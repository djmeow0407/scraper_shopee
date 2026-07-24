from __future__ import annotations

import json
import logging
import os
from pathlib import Path

from .models import ProductRecord

log = logging.getLogger(__name__)


class JsonStore:
    """File JSON dạng list các ProductRecord, ghi nguyên tử và cho phép chạy tiếp."""

    def __init__(self, path: Path):
        self.path = path
        self.records: list[dict] = []
        self.known_urls: set[str] = set()
        self._load()

    def _load(self) -> None:
        if not self.path.is_file():
            return
        try:
            with self.path.open(encoding="utf-8") as f:
                loaded = json.load(f)
        except (OSError, json.JSONDecodeError) as e:
            log.warning("Không đọc được %s (%s), coi như bắt đầu mới", self.path, e)
            return

        if isinstance(loaded, dict):  # file cũ chỉ chứa một sản phẩm
            loaded = [loaded]

        self.records = loaded
        self.known_urls = {url for url in map(_record_url, loaded) if url}
        log.info("Đã có %d sản phẩm trong %s, sẽ bỏ qua các link này", len(loaded), self.path)

    def __len__(self) -> int:
        return len(self.records)

    def has(self, url: str) -> bool:
        return url in self.known_urls

    def add(self, record: ProductRecord) -> None:
        self.records.append(record.to_json_dict())
        if record.url:
            self.known_urls.add(record.url)

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(self.path.suffix + ".tmp")
        with tmp.open("w", encoding="utf-8") as f:
            json.dump(self.records, f, ensure_ascii=False, indent=2)
        os.replace(tmp, self.path)
        log.info("Đã lưu %d sản phẩm vào %s", len(self.records), self.path)


def _record_url(record: object) -> str:
    """Lấy url từ schema mới, ngã về schema phẳng của bản cũ."""
    if not isinstance(record, dict):
        return ""
    product = record.get("product")
    if isinstance(product, dict) and product.get("url"):
        return str(product["url"])
    return str(record.get("link") or record.get("url") or "")
