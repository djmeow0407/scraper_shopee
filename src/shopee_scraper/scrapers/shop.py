from __future__ import annotations

import logging
import re

from .. import selectors as sel
from ..browser import (
    browser_session,
    goto,
    polite_sleep,
    scroll_fraction,
    select_all,
)
from ..models import ProductListing, ShopInfo
from ..report import RunReport
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

    async def shop_header(self, tab) -> ShopInfo:
        name = await self.fields.text(tab, "shop_header", sel.SHOP_HEADER)
        return ShopInfo(name=name.split("\n")[0] if name else "Unknown", url=self.shop_url)

    async def _page_listings(self, tab, page: int) -> list[ProductListing]:
        await goto(tab, f"{self.shop_url}?page={page}&sortBy=pop", self.settings, wait=2)
        for fraction in (0.4, 0.7, 1.0):
            await scroll_fraction(tab, fraction)
            await polite_sleep(self.settings)

        anchors = await select_all(tab, sel.SHOP_PRODUCT_LINK)
        listings = []
        for anchor in anchors:
            url = anchor.attrs.get("href") if anchor.attrs else ""
            if not url or "-i." not in url:
                continue
            listings.append(
                ProductListing(
                    url=url,
                    name=await self.fields.text(anchor, "listing_name", sel.LISTING_NAME, "Unknown"),
                    price=await self.fields.text(anchor, "listing_price", sel.LISTING_PRICE, "0"),
                )
            )
        return listings

    async def run(
        self, review_limit: int | None = None, mode: ReviewMode = ReviewMode.recent
    ) -> tuple[JsonStore, RunReport]:
        store = JsonStore(self.settings.resolve_output(self.output_file))
        run_report = RunReport(self.report)

        async with browser_session(self.settings) as (_browser, tab):
            await goto(tab, self.shop_url, self.settings)
            shop = await self.shop_header(tab)
            log.info("Shop: %s", shop.name)

            page = 0
            empty_pages = 0
            scraped = 0
            while scraped < self.num_products and empty_pages < MAX_EMPTY_PAGES:
                listings = await self._page_listings(tab, page)
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
                        record = await self.scrape_product(
                            tab, listing.url, listing=listing, shop=shop,
                            review_limit=review_limit, mode=mode,
                        )
                    except Exception as e:
                        log.error("Lỗi ở %s: %s", listing.url, e)
                        continue
                    store.add(record)
                    run_report.observe(record)
                    scraped += 1
                    if scraped % self.settings.save_every == 0:
                        store.save()
                page += 1

        store.save()
        return store, run_report
