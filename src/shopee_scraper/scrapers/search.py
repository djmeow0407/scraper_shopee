from __future__ import annotations

import logging
import re
from urllib.parse import quote

from .. import selectors as sel
from ..browser import browser_session, goto, polite_sleep, select_all, select_first
from ..models import ProductInfo, ProductListing, ProductRecord
from ..parsers import parse_price
from ..report import RunReport
from ..storage import JsonStore
from .base import PRODUCT_ID, BaseScraper, ReviewMode

log = logging.getLogger(__name__)

PRODUCTS_PER_PAGE = 60
SORT_CHOICES = ["relevancy", "sales", "ctime", "price"]


class SearchScraper(BaseScraper):
    def __init__(self, keyword: str, num_products: int, sort_by: str = "relevancy",
                 category: str | None = None, index_only: bool = False, **kwargs):
        super().__init__(**kwargs)
        self.keyword = keyword
        self.num_products = num_products
        self.sort_by = sort_by
        self.category = category
        self.index_only = index_only

    @property
    def output_file(self) -> str:
        slug = re.sub(r"[^a-z0-9]+", "_", self.keyword.lower()).strip("_")
        return f"search_{slug or 'unknown'}.json"

    def search_url(self, page: int = 0) -> str:
        params = [f"keyword={quote(self.keyword.strip())}", "noCorrection=true", f"page={page}",
                  f"sortBy={self.sort_by}"]
        # facet phải có ở mọi trang, bản cũ chỉ gắn cho trang đầu rồi tự đánh mất.
        if self.category:
            params.insert(0, f"facet={self.category}")
        return "https://shopee.vn/search?" + "&".join(params)

    async def collect_listings(self, tab) -> list[ProductListing]:
        listings: list[ProductListing] = []
        pages = -(-self.num_products // PRODUCTS_PER_PAGE)

        for page in range(pages):
            url = self.search_url(page)
            log.info("Trang %d/%d: %s", page + 1, pages, url)
            await goto(tab, url, self.settings)

            container, _ = await select_first(tab, sel.SEARCH_RESULT_LIST)
            items = await select_all(container or tab, sel.SEARCH_RESULT_ITEM)
            if not items:
                log.warning("Trang %d không có sản phẩm nào, bỏ qua", page + 1)
                continue

            for item in items:
                if len(listings) >= self.num_products:
                    return listings
                listing = await self._read_listing(item)
                if listing is not None:
                    listings.append(listing)

            log.info("Trang %d xong, tổng %d sản phẩm", page + 1, len(listings))
            await polite_sleep(self.settings)

        return listings

    async def _read_listing(self, item) -> ProductListing | None:
        url = await self.fields.attr(item, "listing_link", sel.LISTING_LINK, "href")
        if not url:
            return None
        return ProductListing(
            url=url,
            name=await self.fields.text(item, "listing_name", sel.LISTING_NAME, "Unknown"),
            price=await self.fields.text(item, "listing_price", sel.LISTING_PRICE, "0"),
            image=await self.fields.attr(item, "listing_image", sel.LISTING_IMAGE, "src"),
            rating=await self.fields.text(item, "listing_rating", sel.LISTING_RATING),
            location=await self.fields.text(item, "listing_location", sel.LISTING_LOCATION),
        )

    async def run(
        self, review_limit: int | None = None, mode: ReviewMode = ReviewMode.recent
    ) -> tuple[JsonStore, RunReport]:
        store = JsonStore(self.settings.resolve_output(self.output_file))
        run_report = RunReport(self.report)

        async with browser_session(self.settings) as (_browser, tab):
            listings = await self.collect_listings(tab)
            todo = [item for item in listings if not store.has(item.url)]
            log.info("Tìm được %d sản phẩm, %d cái chưa crawl", len(listings), len(todo))

            for index, listing in enumerate(todo, 1):
                try:
                    if self.index_only:
                        record = self._listing_only(listing)
                    else:
                        record = await self.scrape_product(
                            tab, listing.url, listing=listing, review_limit=review_limit,
                            mode=mode, category_code=self.category,
                        )
                    store.add(record)
                    run_report.observe(record)
                except Exception as e:
                    log.error("Lỗi ở %s: %s", listing.url, e)
                if index % self.settings.save_every == 0:
                    store.save()

        store.save()
        return store, run_report

    def _listing_only(self, listing: ProductListing) -> ProductRecord:
        match = PRODUCT_ID.search(listing.url)
        return ProductRecord(
            product=ProductInfo(
                id=f"{match.group(1)}_{match.group(2)}" if match else "0_0",
                url=listing.url,
                name=listing.name,
                price=parse_price(listing.price),
                image=listing.image,
                rating=listing.rating,
                location=listing.location,
                category_info=self.categories.get(self.category),
            )
        )
