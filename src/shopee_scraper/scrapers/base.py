from __future__ import annotations

import logging
import re
import time
from enum import StrEnum

from selenium.common.exceptions import WebDriverException
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement

from .. import selectors as sel
from ..categories import CategoryIndex
from ..config import Settings
from ..console import progress
from ..driver import attr_of, find_all, find_first, goto, scroll_fraction, scroll_to, text_of
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

    def rating_breakdown(self, driver: WebDriver) -> RatingBreakdown:
        breakdown = RatingBreakdown()
        for key, count in self._rating_filters(driver):
            if key.isdigit():
                breakdown.by_star[int(key)] = count
                breakdown.total += count
            elif key == "commented":
                breakdown.with_comment = count
            elif key == "media":
                breakdown.with_media = count
        return breakdown

    def _rating_filters(self, driver: WebDriver) -> list[tuple[str, int]]:
        out = []
        for element in find_all(driver, sel.RATING_FILTER):
            try:
                parsed = parse_rating_filter(element.text)
            except WebDriverException:
                continue
            if parsed:
                out.append(parsed)
        return out

    def _review_container(self, driver: WebDriver) -> WebElement | None:
        anchor = find_first(driver, sel.REVIEW_ANCHOR)
        if anchor is not None:
            scroll_to(driver, anchor)
        else:
            scroll_fraction(driver, 0.9)
        time.sleep(2)

        for _ in range(5):
            container = find_first(driver, sel.REVIEW_LIST)
            if container is not None:
                try:
                    if container.is_displayed():
                        return container
                except WebDriverException:
                    pass
            if "chưa có đánh giá" in driver.page_source.lower():
                return None
            time.sleep(1)
        return None

    def _review_items(self, container: WebElement) -> list[WebElement]:
        kept = []
        for item in find_all(container, sel.REVIEW_ITEM):
            try:
                if item.size["height"] > 20 and item.text.strip():
                    kept.append(item)
            except WebDriverException:
                continue
        return kept

    def _parse_item(self, item: WebElement, star_bucket: int | None) -> Review | None:
        try:
            text = item.text
            stars = len(find_all(item, sel.REVIEW_SOLID_STAR))
        except WebDriverException:
            return None

        return parse_review_block(
            text,
            rating=stars or (star_bucket or 0),
            username=text_of(item, sel.REVIEW_AUTHOR),
            star_bucket=star_bucket,
        )

    def collect_reviews(
        self,
        driver: WebDriver,
        limit: int,
        star_bucket: int | None = None,
    ) -> list[Review]:
        if limit <= 0:
            return []

        container = self._review_container(driver)
        if container is None:
            return []

        reviews: list[Review] = []
        label = f"Đánh giá {star_bucket} sao" if star_bucket else "Đánh giá"

        with progress() as bar:
            task = bar.add_task(label, total=limit)
            while len(reviews) < limit:
                items = self._review_items(container)
                if not items:
                    break

                before = len(reviews)
                for item in items:
                    if len(reviews) >= limit:
                        break
                    review = self._parse_item(item, star_bucket)
                    if review is not None:
                        reviews.append(review)
                        bar.update(task, completed=len(reviews))

                # Không thêm được gì ở trang này thì bấm tiếp cũng vô ích.
                if len(reviews) >= limit or len(reviews) == before:
                    break

                button = find_first(driver, sel.REVIEW_NEXT_PAGE)
                if button is None:
                    break
                try:
                    if not button.is_enabled():
                        break
                    button.click()
                except WebDriverException:
                    break
                time.sleep(self.settings.review_page_delay)

                refreshed = find_first(driver, sel.REVIEW_LIST)
                if refreshed is not None:
                    container = refreshed

        return reviews

    def collect_reviews_by_star(self, driver: WebDriver, per_bucket: int) -> list[Review]:
        """Bấm lần lượt từng bộ lọc sao để lấy mẫu cân bằng thay vì toàn 5 sao."""
        buckets = {
            int(key): count
            for key, count in self._rating_filters(driver)
            if key.isdigit() and count > 0
        }
        if not buckets:
            log.warning("Không thấy bộ lọc sao, quay về lấy đánh giá mới nhất")
            return self.collect_reviews(driver, per_bucket)

        reviews: list[Review] = []
        for star in sorted(buckets):
            if not self._click_star_filter(driver, star):
                continue
            reviews.extend(
                self.collect_reviews(driver, min(buckets[star], per_bucket), star_bucket=star)
            )
        return reviews

    def _click_star_filter(self, driver: WebDriver, star: int) -> bool:
        # Tìm lại element mỗi vòng: bấm lọc xong là Shopee dựng lại DOM.
        for element in find_all(driver, sel.RATING_FILTER):
            try:
                parsed = parse_rating_filter(element.text)
                if not parsed or parsed[0] != str(star):
                    continue
                scroll_to(driver, element)
                element.click()
            except WebDriverException as e:
                log.warning("Không bấm được bộ lọc %d sao: %s", star, e)
                return False
            time.sleep(self.settings.review_page_delay)
            return True
        return False

    def scrape_product(
        self,
        driver: WebDriver,
        url: str,
        listing: ProductListing | None = None,
        shop: ShopInfo | None = None,
        review_limit: int | None = None,
        mode: ReviewMode = ReviewMode.recent,
        category_code: str | None = None,
    ) -> ProductRecord:
        goto(driver, url)
        warnings: list[str] = []

        scroll_fraction(driver, 0.3)
        time.sleep(1)
        anchor = find_first(driver, sel.DESCRIPTION_ANCHOR)
        if anchor is not None:
            scroll_to(driver, anchor)
        else:
            scroll_fraction(driver, 0.6)
        time.sleep(2)

        container = find_first(driver, sel.DESCRIPTION_CONTAINER)
        description = parse_description(container.text if container is not None else "")
        if not description.raw_text:
            warnings.append("description-empty")

        name = listing.name if listing else ""
        if not name or name == "Unknown":
            name = text_of(driver, sel.PRODUCT_NAME) or self._meta(driver, "og:title")
        if not name:
            warnings.append("name-not-found")
            name = "Unknown"

        price_text = listing.price if listing else ""
        if not price_text or price_text == "0":
            price_text = text_of(driver, sel.PRODUCT_PRICE)
        if not price_text:
            warnings.append("price-not-found")

        image = listing.image if listing else ""
        if not image:
            image = attr_of(driver, sel.PRODUCT_IMAGE, "src") or self._meta(driver, "og:image")

        breakdown = self.rating_breakdown(driver)

        if mode is ReviewMode.all_stars:
            reviews = self.collect_reviews_by_star(driver, self.settings.star_limit_per_type)
        else:
            limit = self.settings.review_limit if review_limit is None else review_limit
            reviews = self.collect_reviews(driver, min(limit, breakdown.total or limit))

        if not reviews:
            warnings.append("no-reviews")

        return ProductRecord(
            product=self._build_product(
                url, name, price_text, image, description, listing, category_code
            ),
            description=description,
            rating_breakdown=breakdown,
            reviews=reviews,
            shop=shop or ShopInfo(),
            meta=ScrapeMeta(warnings=warnings),
        )

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
    def _meta(driver: WebDriver, prop: str) -> str:
        try:
            el = driver.find_element(By.CSS_SELECTOR, f'meta[property="{prop}"]')
            return (el.get_attribute("content") or "").strip()
        except WebDriverException:
            return ""
