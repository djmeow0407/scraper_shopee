from __future__ import annotations

import logging
import re
from urllib.parse import quote

from selenium.common.exceptions import WebDriverException
from selenium.webdriver.remote.webdriver import WebDriver

from .. import selectors as sel
from ..driver import attr_of, chrome_session, find_all, find_first, goto, polite_sleep, text_of
from ..models import ProductInfo, ProductListing, ProductRecord
from ..parsers import parse_price
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

    def collect_listings(self, driver: WebDriver) -> list[ProductListing]:
        listings: list[ProductListing] = []
        pages = -(-self.num_products // PRODUCTS_PER_PAGE)

        for page in range(pages):
            url = self.search_url(page)
            log.info("Trang %d/%d: %s", page + 1, pages, url)
            goto(driver, url, wait=4)

            container = find_first(driver, sel.SEARCH_RESULT_LIST)
            items = find_all(container, sel.SEARCH_RESULT_ITEM) if container is not None else []
            if not items:
                items = find_all(driver, sel.SEARCH_RESULT_ITEM)
            if not items:
                log.warning("Trang %d không có sản phẩm nào, bỏ qua", page + 1)
                continue

            for item in items:
                if len(listings) >= self.num_products:
                    return listings
                listing = self._read_listing(item)
                if listing is not None:
                    listings.append(listing)

            log.info("Trang %d xong, tổng %d sản phẩm", page + 1, len(listings))
            polite_sleep(self.settings)

        return listings

    def _read_listing(self, item) -> ProductListing | None:
        try:
            url = attr_of(item, sel.LISTING_LINK, "href")
        except WebDriverException:
            return None
        if not url:
            return None

        return ProductListing(
            url=url,
            name=text_of(item, sel.LISTING_NAME, "Unknown"),
            price=text_of(item, sel.LISTING_PRICE, "0"),
            image=attr_of(item, sel.LISTING_IMAGE, "src"),
            rating=text_of(item, sel.LISTING_RATING),
            location=text_of(item, sel.LISTING_LOCATION),
        )

    def run(self, review_limit: int | None = None, mode: ReviewMode = ReviewMode.recent) -> JsonStore:
        store = JsonStore(self.settings.resolve_output(self.output_file))

        with chrome_session(self.settings) as driver:
            listings = self.collect_listings(driver)
            todo = [item for item in listings if not store.has(item.url)]
            log.info("Tìm được %d sản phẩm, %d cái chưa crawl", len(listings), len(todo))

            for index, listing in enumerate(todo, 1):
                try:
                    if self.index_only:
                        record = self._listing_only(listing)
                    else:
                        record = self.scrape_product(
                            driver, listing.url, listing=listing,
                            review_limit=review_limit, mode=mode,
                            category_code=self.category,
                        )
                    store.add(record)
                except WebDriverException as e:
                    log.error("Lỗi ở %s: %s", listing.url, e)
                if index % self.settings.save_every == 0:
                    store.save()

        store.save()
        return store

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
