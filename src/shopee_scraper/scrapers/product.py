from __future__ import annotations

import logging
import re

from ..driver import chrome_session
from ..models import ProductRecord
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

    def run(self, review_limit: int | None = None, mode: ReviewMode = ReviewMode.recent) -> JsonStore:
        with chrome_session(self.settings) as driver:
            record = self.scrape_product(driver, self.url, review_limit=review_limit, mode=mode)

        if record.meta.warnings:
            log.warning("Bản ghi thiếu dữ liệu: %s", ", ".join(record.meta.warnings))

        store = JsonStore(self.settings.resolve_output(self.output_file(record)))
        store.add(record)
        store.save()
        return store
