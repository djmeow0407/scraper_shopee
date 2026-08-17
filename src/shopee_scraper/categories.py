from __future__ import annotations

import asyncio
import csv
import logging
import random
from pathlib import Path

from . import selectors as sel
from .browser import browser_session, goto, select_all, select_first
from .config import Settings
from .console import console
from .models import CategoryInfo

log = logging.getLogger(__name__)

CATEGORY_GUIDE_URL = "https://banhang.shopee.vn/edu/category-guide/"
CSV_FIELDS = ["nganh_cap_1", "nganh_cap_2", "nganh_cap_3", "nganh_cap_4", "nganh_cap_5",
              "ma_nganh", "mo_ta_vi_du"]


class CategoryIndex:
    """Tra cứu ngành hàng theo mã, đọc từ shopee_categories.csv."""

    def __init__(self, rows: dict[str, CategoryInfo]):
        self._rows = rows

    def __len__(self) -> int:
        return len(self._rows)

    def get(self, code: str | None) -> CategoryInfo | None:
        return self._rows.get(code) if code else None

    @classmethod
    def load(cls, path: Path) -> CategoryIndex:
        if not path.is_file():
            log.warning("Không thấy %s, bỏ qua phần gắn ngành hàng", path)
            return cls({})

        rows: dict[str, CategoryInfo] = {}
        with path.open(encoding="utf-8", newline="") as f:
            for row in csv.DictReader(f):
                code = (row.get("ma_nganh") or "").strip()
                if not code:
                    continue
                # Shopee điền "-" cho các cấp không dùng tới.
                path_parts = [(row.get(f"nganh_cap_{i}") or "").strip() for i in range(1, 6)]
                rows[code] = CategoryInfo(
                    code=code,
                    path=[p for p in path_parts if p and p != "-"],
                    example=(row.get("mo_ta_vi_du") or "").strip(),
                )
        log.info("Nạp %d ngành hàng từ %s", len(rows), path)
        return cls(rows)


async def _scrape_page(tab) -> list[dict[str, str]]:
    out = []
    for row in await select_all(tab, sel.CATEGORY_ROW):
        cols = await select_all(row, ["td"])
        if len(cols) < len(CSV_FIELDS):
            continue
        out.append({field: (cols[i].text or "").strip() for i, field in enumerate(CSV_FIELDS)})
    return out


async def scrape_categories(settings: Settings, out_path: Path) -> int:
    """Cào toàn bộ bảng ngành hàng của Shopee ra CSV. Trả về số dòng."""
    rows: list[dict[str, str]] = []

    async with browser_session(settings) as (_browser, tab):
        await goto(tab, CATEGORY_GUIDE_URL, settings)

        page = 1
        while True:
            rows.extend(await _scrape_page(tab))
            console.print(f"  trang {page}: tổng {len(rows)} dòng")

            button, _ = await select_first(tab, sel.CATEGORY_NEXT_PAGE)
            if button is None:
                break
            classes = (button.attrs.get("class") if button.attrs else "") or ""
            if "disabled" in classes or "disabled" in (button.attrs or {}):
                break

            await button.scroll_into_view()
            await asyncio.sleep(0.5)
            await button.click()
            await asyncio.sleep(random.uniform(1.5, 3.0))
            page += 1

    if not rows:
        log.error("Không lấy được dòng nào, giữ nguyên file cũ")
        return 0

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    return len(rows)
