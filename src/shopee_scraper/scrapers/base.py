from __future__ import annotations

import asyncio
import logging
import re
from enum import StrEnum

from .. import quality
from .. import selectors as sel
from ..browser import (
    Fields,
    find_text,
    goto,
    page_html,
    scroll_fraction,
    scroll_to,
    select_all,
    select_first,
)
from ..categories import CategoryIndex
from ..config import Settings
from ..extraction import ExtractionReport
from ..models import (
    Description,
    ProductInfo,
    ProductListing,
    ProductRecord,
    RatingBreakdown,
    Review,
    ScrapeMeta,
    ShopInfo,
)
from ..parsers import parse_price, parse_rating_filter, parse_review_block, parse_weight
from ..parsers.description import category_path, parse_description, shelf_life_months

log = logging.getLogger(__name__)

PRODUCT_ID = re.compile(r"i\.(\d+)\.(\d+)")


class ReviewMode(StrEnum):
    recent = "recent"
    all_stars = "all-stars"


class BaseScraper:
    def __init__(self, settings: Settings, categories: CategoryIndex | None = None):
        self.settings = settings
        self.categories = categories or CategoryIndex({})
        self.report = ExtractionReport()
        self.fields = Fields(self.report)

    async def _rating_filters(self, tab) -> list[tuple[str, int]]:
        out = []
        for element in await select_all(tab, sel.RATING_FILTER):
            try:
                parsed = parse_rating_filter(element.text)
            except Exception:
                continue
            if parsed:
                out.append(parsed)
        return out

    async def rating_breakdown(self, tab) -> RatingBreakdown:
        breakdown = RatingBreakdown()
        for key, count in await self._rating_filters(tab):
            if key.isdigit():
                breakdown.by_star[int(key)] = count
                breakdown.total += count
            elif key == "commented":
                breakdown.with_comment = count
            elif key == "media":
                breakdown.with_media = count
        return breakdown

    async def _review_container(self, tab):
        anchor = await find_text(tab, sel.REVIEW_ANCHOR_TEXT)
        if anchor is not None:
            await scroll_to(anchor)
        else:
            await scroll_fraction(tab, 0.9)
        await asyncio.sleep(2)

        for _ in range(5):
            container, _ = await select_first(tab, sel.REVIEW_LIST)
            if container is not None:
                return container
            if sel.NO_REVIEW_TEXT in (await page_html(tab)).lower():
                return None
            await asyncio.sleep(1)
        return None

    async def _parse_item(self, item, star_bucket: int | None) -> Review | None:
        try:
            text = item.text or ""
        except Exception:
            return None
        stars = len(await select_all(item, sel.REVIEW_SOLID_STAR))
        author = await self.fields.text(item, "review_author", sel.REVIEW_AUTHOR)
        return parse_review_block(
            text, rating=stars or (star_bucket or 0), username=author, star_bucket=star_bucket
        )

    async def collect_reviews(self, tab, limit: int, star_bucket: int | None = None) -> list[Review]:
        if limit <= 0:
            return []
        container = await self._review_container(tab)
        if container is None:
            return []

        reviews: list[Review] = []
        while len(reviews) < limit:
            items = [i for i in await select_all(container, sel.REVIEW_ITEM) if _has_text(i)]
            if not items:
                break

            before = len(reviews)
            for item in items:
                if len(reviews) >= limit:
                    break
                review = await self._parse_item(item, star_bucket)
                if review is not None:
                    reviews.append(review)

            # Không thêm được gì ở trang này thì bấm tiếp cũng vô ích.
            if len(reviews) >= limit or len(reviews) == before:
                break

            button, _ = await select_first(tab, sel.REVIEW_NEXT_PAGE)
            if button is None:
                break
            try:
                await button.click()
            except Exception:
                break
            await asyncio.sleep(self.settings.review_page_delay)

            refreshed, _ = await select_first(tab, sel.REVIEW_LIST)
            if refreshed is not None:
                container = refreshed

        label = f" {star_bucket} sao" if star_bucket else ""
        log.info("Thu thập %d đánh giá%s", len(reviews), label)
        return reviews

    async def collect_reviews_by_star(self, tab, per_bucket: int) -> list[Review]:
        """Bấm lần lượt từng bộ lọc sao để lấy mẫu cân bằng thay vì toàn 5 sao."""
        buckets = {
            int(key): count
            for key, count in await self._rating_filters(tab)
            if key.isdigit() and count > 0
        }
        if not buckets:
            log.warning("Không thấy bộ lọc sao, quay về lấy đánh giá mới nhất")
            return await self.collect_reviews(tab, per_bucket)

        reviews: list[Review] = []
        for star in sorted(buckets):
            if not await self._click_star_filter(tab, star):
                continue
            reviews.extend(
                await self.collect_reviews(tab, min(buckets[star], per_bucket), star_bucket=star)
            )
        return reviews

    async def _click_star_filter(self, tab, star: int) -> bool:
        # Tìm lại element mỗi vòng: bấm lọc xong là Shopee dựng lại DOM.
        for element in await select_all(tab, sel.RATING_FILTER):
            try:
                parsed = parse_rating_filter(element.text)
                if not parsed or parsed[0] != str(star):
                    continue
                await scroll_to(element)
                await element.click()
            except Exception as e:
                log.warning("Không bấm được bộ lọc %d sao: %s", star, e)
                return False
            await asyncio.sleep(self.settings.review_page_delay)
            return True
        return False

    async def scrape_product(
        self,
        tab,
        url: str,
        listing: ProductListing | None = None,
        shop: ShopInfo | None = None,
        review_limit: int | None = None,
        mode: ReviewMode = ReviewMode.recent,
        category_code: str | None = None,
    ) -> ProductRecord:
        await goto(tab, url, self.settings)

        await scroll_fraction(tab, 0.3)
        await asyncio.sleep(1)
        anchor = await find_text(tab, sel.DESCRIPTION_ANCHOR_TEXT)
        if anchor is not None:
            await scroll_to(anchor)
        else:
            await scroll_fraction(tab, 0.6)
        await asyncio.sleep(2)

        container = await self.fields.element(tab, "description", sel.DESCRIPTION_CONTAINER)
        description = parse_description((container.text if container else "") or "")

        name = listing.name if listing else ""
        if not name or name == "Unknown":
            name = await self.fields.text(tab, "product_name", sel.PRODUCT_NAME) or await self._meta(
                tab, "og:title"
            )

        price_text = listing.price if listing else ""
        if not price_text or price_text == "0":
            price_text = await self.fields.text(tab, "product_price", sel.PRODUCT_PRICE)

        image = listing.image if listing else ""
        if not image:
            image = await self.fields.attr(
                tab, "product_image", sel.PRODUCT_IMAGE, "src"
            ) or await self._meta(tab, "og:image")

        breakdown = await self.rating_breakdown(tab)

        if mode is ReviewMode.all_stars:
            reviews = await self.collect_reviews_by_star(tab, self.settings.star_limit_per_type)
        else:
            limit = self.settings.review_limit if review_limit is None else review_limit
            reviews = await self.collect_reviews(tab, min(limit, breakdown.total or limit))

        record = ProductRecord(
            product=self._build_product(
                url, name or "Unknown", price_text, image, description, listing, category_code
            ),
            description=description,
            rating_breakdown=breakdown,
            reviews=reviews,
            shop=shop or ShopInfo(),
            meta=ScrapeMeta(),
        )
        record.meta.warnings = quality.validate(record)
        return record

    def _build_product(
        self,
        url: str,
        name: str,
        price_text: str,
        image: str,
        description: Description,
        listing: ProductListing | None,
        category_code: str | None,
    ) -> ProductInfo:
        specs = description.specs
        match = PRODUCT_ID.search(url)
        return ProductInfo(
            id=f"{match.group(1)}_{match.group(2)}" if match else "0_0",
            url=url,
            name=name,
            price=parse_price(price_text),
            image=image,
            stock_status=specs.get("Kho", "Unknown"),
            category=category_path(specs),
            category_info=self.categories.get(category_code),
            brand=specs.get("Thương hiệu", "No Brand"),
            weight=parse_weight(specs.get("Trọng lượng", "")),
            origin=specs.get("Xuất xứ", "Unknown"),
            shelf_life_months=shelf_life_months(specs),
            ship_from=specs.get("Gửi từ", "Unknown"),
            rating=listing.rating if listing else "",
            location=listing.location if listing else "",
        )

    @staticmethod
    async def _meta(tab, prop: str) -> str:
        js = f"document.querySelector('meta[property=\"{prop}\"]')?.content || ''"
        try:
            return (await tab.evaluate(js)) or ""
        except Exception:
            return ""


def _has_text(element) -> bool:
    try:
        return bool((element.text or "").strip())
    except Exception:
        return False
