from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Annotated

import typer

from . import __version__
from .categories import CategoryIndex, scrape_categories
from .config import Settings
from .console import console, setup_logging
from .scrapers import ProductScraper, ReviewMode, SearchScraper, ShopScraper
from .scrapers.base import BaseScraper
from .scrapers.search import SORT_CHOICES

app = typer.Typer(
    name="shopee",
    help="Thu thập sản phẩm và đánh giá từ Shopee.vn.",
    no_args_is_help=True,
    add_completion=False,
)


@app.callback()
def main(
    ctx: typer.Context,
    config: Annotated[Path | None, typer.Option("--config", help="File cấu hình TOML")] = None,
    output_dir: Annotated[Path | None, typer.Option("--out", help="Thư mục lưu JSON")] = None,
    headless: Annotated[bool | None, typer.Option("--headless/--no-headless")] = None,
    browser_path: Annotated[Path | None, typer.Option("--browser", help="Đường dẫn tới Brave/Chrome")] = None,
    no_sandbox: Annotated[bool | None, typer.Option("--no-sandbox/--sandbox")] = None,
    delay_min: Annotated[float | None, typer.Option(help="Nghỉ tối thiểu giữa các trang (giây)")] = None,
    delay_max: Annotated[float | None, typer.Option(help="Nghỉ tối đa giữa các trang (giây)")] = None,
    verbose: Annotated[bool, typer.Option("-v", "--verbose")] = False,
) -> None:
    setup_logging(verbose)
    ctx.obj = Settings.load(
        config,
        output_dir=output_dir,
        headless=headless,
        browser_path=browser_path,
        no_sandbox=no_sandbox,
        delay_min=delay_min,
        delay_max=delay_max,
    )


def _shared(ctx: typer.Context) -> tuple[Settings, CategoryIndex]:
    settings: Settings = ctx.obj
    return settings, CategoryIndex.load(settings.categories_csv)


def _run(scraper: BaseScraper, review_limit: int | None, mode: ReviewMode) -> None:
    store, report = asyncio.run(scraper.run(review_limit=review_limit, mode=mode))
    sidecar = store.path.with_suffix(".report.json")
    report.save(sidecar)
    console.print(f"\n[green]Xong.[/] {len(store)} sản phẩm trong [bold]{store.path}[/]")
    report.render(console)
    console.print(f"[dim]Chi tiết selector: {sidecar}[/]")


@app.command()
def search(
    ctx: typer.Context,
    keyword: Annotated[str, typer.Argument(help="Từ khoá tìm kiếm")],
    num: Annotated[int, typer.Option("-n", "--num", help="Số sản phẩm cần lấy")] = 10,
    review_limit: Annotated[int | None, typer.Option("-r", "--review-limit")] = None,
    stars: Annotated[ReviewMode, typer.Option(help="recent = mới nhất, all-stars = cân bằng theo sao")] = ReviewMode.recent,
    sort_by: Annotated[str, typer.Option(help=f"Một trong: {', '.join(SORT_CHOICES)}")] = "relevancy",
    category: Annotated[str | None, typer.Option("-c", "--category", help="Mã ngành hàng")] = None,
    index_only: Annotated[bool, typer.Option("--index-only", help="Chỉ lấy trang danh sách, bỏ qua chi tiết")] = False,
) -> None:
    """Crawl theo từ khoá."""
    if sort_by not in SORT_CHOICES:
        raise typer.BadParameter(f"sort-by phải thuộc {SORT_CHOICES}")

    settings, categories = _shared(ctx)
    scraper = SearchScraper(
        keyword=keyword,
        num_products=num,
        sort_by=sort_by,
        category=category,
        index_only=index_only,
        settings=settings,
        categories=categories,
    )
    _run(scraper, review_limit=review_limit, mode=stars)


@app.command()
def shop(
    ctx: typer.Context,
    url: Annotated[str, typer.Argument(help="Link shop, ví dụ https://shopee.vn/tenshop")],
    num: Annotated[int, typer.Option("-n", "--num")] = 10,
    review_limit: Annotated[int | None, typer.Option("-r", "--review-limit")] = None,
    stars: Annotated[ReviewMode, typer.Option()] = ReviewMode.recent,
) -> None:
    """Crawl toàn bộ sản phẩm của một shop."""
    settings, categories = _shared(ctx)
    scraper = ShopScraper(shop_url=url, num_products=num, settings=settings, categories=categories)
    _run(scraper, review_limit=review_limit, mode=stars)


@app.command()
def product(
    ctx: typer.Context,
    url: Annotated[str, typer.Argument(help="Link một sản phẩm")],
    review_limit: Annotated[int | None, typer.Option("-r", "--review-limit")] = None,
    stars: Annotated[ReviewMode, typer.Option()] = ReviewMode.recent,
) -> None:
    """Crawl một sản phẩm."""
    settings, categories = _shared(ctx)
    scraper = ProductScraper(url=url, settings=settings, categories=categories)
    _run(scraper, review_limit=review_limit, mode=stars)


@app.command()
def categories(
    ctx: typer.Context,
    out: Annotated[Path | None, typer.Option("--out-csv", help="Nơi ghi CSV")] = None,
) -> None:
    """Cập nhật bảng mã ngành hàng từ banhang.shopee.vn."""
    settings: Settings = ctx.obj
    target = out or settings.categories_csv
    count = asyncio.run(scrape_categories(settings, target))
    if count:
        console.print(f"[green]Xong.[/] {count} ngành hàng ghi vào [bold]{target}[/]")
        raise typer.Exit(0)
    raise typer.Exit(1)


@app.command()
def version() -> None:
    """In phiên bản."""
    console.print(f"shopee-scraper {__version__}")
