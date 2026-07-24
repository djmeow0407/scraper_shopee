from __future__ import annotations

import logging
import re

from selenium.common.exceptions import WebDriverException
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver

from .. import selectors as sel
from ..driver import chrome_session, find_all, goto, polite_sleep, scroll_fraction, text_of
from ..models import ProductListing, ShopInfo
from ..storage import JsonStore
from .base import BaseScraper, ReviewMode

log = logging.getLogger(__name__)

MAX_EMPTY_PAGES = 2


class ShopScraper(BaseScraper):
    def __init__(self, shop_url: str, num_products: int, **kwargs):
        super().__init__(**kwargs)
        self.shop_url = shop_url.split("?")[0].rstrip("/")
        self.num_products = num_products

    @property
    def shop_slug(self) -> str:
        tail = re.sub(r"https?://(www\.)?shopee\.vn/", "", self.shop_url).split("/")[0]
        return re.sub(r"[^a-z0-9]+", "_", tail.lower()).strip("_") or "shop"

    @property
    def output_file(self) -> str:
        return f"shop_{self.shop_slug}.json"

    def shop_header(self, driver: WebDriver) -> ShopInfo:
        name = text_of(driver, sel.SHOP_HEADER)
        return ShopInfo(name=name.split("\n")[0] if name else "Unknown", url=self.shop_url)

    def _page_listings(self, driver: WebDriver, page: int) -> list[ProductListing]:
        goto(driver, f"{self.shop_url}?page={page}&sortBy=pop", wait=2)
        for fraction in (0.4, 0.7, 1.0):
            scroll_fraction(driver, fraction)
            polite_sleep(self.settings)

        anchors = find_all(driver, sel.SHOP_PRODUCT_LINK)
        if not anchors:
            anchors = [
                a
                for a in driver.find_elements(By.TAG_NAME, "a")
                if "-i." in (a.get_attribute("href") or "")
            ]

        listings = []
        for anchor in anchors:
            try:
                url = anchor.get_attribute("href")
            except WebDriverException:
                continue
            if not url:
                continue
            listings.append(
                ProductListing(
                    url=url,
                    name=text_of(anchor, sel.LISTING_NAME, "Unknown"),
                    price=text_of(anchor, sel.LISTING_PRICE, "0"),
                )
            )
        return listings

    def run(self, review_limit: int | None = None, mode: ReviewMode = ReviewMode.recent) -> JsonStore:
        store = JsonStore(self.settings.resolve_output(self.output_file))

        with chrome_session(self.settings) as driver:
            goto(driver, self.shop_url)
            shop = self.shop_header(driver)
            log.info("Shop: %s", shop.name)

            page = 0
            empty_pages = 0
            scraped = 0

            while scraped < self.num_products and empty_pages < MAX_EMPTY_PAGES:
                listings = self._page_listings(driver, page)
                todo = [item for item in listings if not store.has(item.url)]
                log.info("Trang %d: %d sản phẩm, %d cái mới", page, len(listings), len(todo))

                if not listings:
                    empty_pages += 1
                    page += 1
                    continue
                empty_pages = 0

                for listing in todo:
                    if scraped >= self.num_products:
                        break
                    try:
                        record = self.scrape_product(
                            driver, listing.url, listing=listing, shop=shop,
                            review_limit=review_limit, mode=mode,
                        )
                    except WebDriverException as e:
                        log.error("Lỗi ở %s: %s", listing.url, e)
                        continue
                    store.add(record)
                    scraped += 1
                    if scraped % self.settings.save_every == 0:
                        store.save()

                page += 1

        store.save()
        return store
