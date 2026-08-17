from __future__ import annotations

import logging
import re

from ..browser import browser_session
from ..models import ProductRecord
from ..report import RunReport
from ..storage import JsonStore
from .base import BaseScraper, ReviewMode

log = logging.getLogger(__name__)


class ProductScraper(BaseScraper):
    def __init__(self, url: str, **kwargs):
        super().__init__(**kwargs)
        self.url = url

    def output_file(self, record: ProductRecord) -> str:
        slug = re.sub(r"[^a-z0-9]+", "_", record.product.name.lower()).strip("_")[:50]
        return f"product_{slug or 'unknown'}_{record.product.id}.json"

    async def run(
        self, review_limit: int | None = None, mode: ReviewMode = ReviewMode.recent
    ) -> tuple[JsonStore, RunReport]:
        run_report = RunReport(self.report)
        async with browser_session(self.settings) as (_browser, tab):
            record = await self.scrape_product(tab, self.url, review_limit=review_limit, mode=mode)

        store = JsonStore(self.settings.resolve_output(self.output_file(record)))
        store.add(record)
        run_report.observe(record)
        store.save()
        return store, run_report
