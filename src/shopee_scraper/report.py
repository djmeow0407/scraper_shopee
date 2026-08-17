from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from rich.console import Console
from rich.table import Table

from .extraction import ExtractionReport
from .models import ProductRecord


class RunReport:
    """Gộp số liệu một lần chạy: sức khỏe selector + cảnh báo từng bản ghi."""

    def __init__(self, extraction: ExtractionReport):
        self.extraction = extraction
        self.records = 0
        self.reviews = 0
        self.with_reviews = 0
        self.warnings: Counter[str] = Counter()

    def observe(self, record: ProductRecord) -> None:
        self.records += 1
        self.reviews += len(record.reviews)
        if record.reviews:
            self.with_reviews += 1
        self.warnings.update(record.meta.warnings)

    def to_dict(self) -> dict:
        return {
            "records": self.records,
            "reviews": self.reviews,
            "with_reviews": self.with_reviews,
            "warnings": dict(self.warnings),
            "selector_flags": self.extraction.flags(),
            "selector_stats": self.extraction.to_dict(),
        }

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")

    def render(self, console: Console) -> None:
        console.print(
            f"\n[bold]Tổng kết[/]  {self.records} sản phẩm, {self.reviews} đánh giá, "
            f"{self.with_reviews} sản phẩm có đánh giá"
        )

        flags = self.extraction.flags()
        if flags:
            console.print("\n[bold red]Selector nghi hỏng — kiểm tra selectors.py:[/]")
            for flag in flags:
                console.print(f"  [red]•[/] {flag}")

        if self.warnings:
            table = Table(title="Cảnh báo theo bản ghi", title_style="yellow", show_edge=False)
            table.add_column("Loại")
            table.add_column("Số bản ghi", justify="right")
            for name, count in self.warnings.most_common():
                table.add_row(name, str(count))
            console.print(table)

        if not flags and not self.warnings:
            console.print("[green]Không có cảnh báo nào.[/]")
