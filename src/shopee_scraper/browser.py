from __future__ import annotations

import asyncio
import logging
import random
from collections.abc import Sequence
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING

import nodriver as uc

from .config import Settings
from .console import console
from .extraction import FALLBACK, MISS, PRIMARY, ExtractionReport
from .selectors import CHALLENGE_URL_MARKERS, Selector

if TYPE_CHECKING:
    from nodriver import Element, Tab

log = logging.getLogger(__name__)


@asynccontextmanager
async def browser_session(settings: Settings):
    args = [
        "--disable-dev-shm-usage",
        "--disable-blink-features=AutomationControlled",
        "--window-size=1920,1080",
        f"--lang={settings.lang}",
    ]
    browser = await uc.start(
        browser_executable_path=settings.resolve_browser(),
        headless=settings.headless,
        sandbox=not settings.no_sandbox,
        user_data_dir=settings.user_data_dir,  # None -> nodriver tự tạo profile tạm
        lang=settings.lang,
        browser_args=args,
    )
    try:
        tab = await browser.get("about:blank")
        yield browser, tab
    finally:
        try:
            browser.stop()
        except Exception:
            pass
        await asyncio.sleep(0.3)


async def _query_first(scope, css: str):
    try:
        return await scope.query_selector(css)
    except Exception:
        return None


async def _query_all(scope, css: str) -> list:
    try:
        return await scope.query_selector_all(css) or []
    except Exception:
        return []


async def select_first(scope, selectors: Sequence[Selector]) -> tuple[Element | None, str]:
    for index, css in enumerate(selectors):
        el = await _query_first(scope, css)
        if el:
            return el, (PRIMARY if index == 0 else FALLBACK)
    return None, MISS


async def select_all(scope, selectors: Sequence[Selector]) -> list:
    for css in selectors:
        found = await _query_all(scope, css)
        if found:
            return found
    return []


# tab.find quét cả DOM nên rất chậm trên trang Shopee và không tôn trọng timeout
# của chính nó, nên phải bọc wait_for cứng. Anchor chỉ dùng để cuộn tới khu vực
# lazy-load; không thấy thì thôi, tuyệt đối đừng để nó treo cả lần cào.
async def find_text(tab: Tab, texts: Sequence[str], timeout: float = 3.0):
    for text in texts:
        try:
            el = await asyncio.wait_for(tab.find(text, best_match=True), timeout)
        except Exception:
            el = None
        if el:
            return el
    return None


class Fields:
    """Đọc field kèm ghi nhận selector nào khớp, đổ vào ExtractionReport."""

    def __init__(self, report: ExtractionReport):
        self.report = report

    async def element(self, scope, name: str, selectors: Sequence[Selector]):
        el, tier = await select_first(scope, selectors)
        self.report.record(name, tier)
        return el

    async def text(self, scope, name: str, selectors: Sequence[Selector], default: str = "") -> str:
        el, tier = await select_first(scope, selectors)
        self.report.record(name, tier)
        if el is None:
            return default
        try:
            value = (el.text or "").strip()
        except Exception:
            value = ""
        return value or default

    async def attr(
        self, scope, name: str, selectors: Sequence[Selector], attribute: str, default: str = ""
    ) -> str:
        el, tier = await select_first(scope, selectors)
        self.report.record(name, tier)
        if el is None:
            return default
        try:
            value = el.attrs.get(attribute) or ""
        except Exception:
            value = ""
        return value or default


async def current_url(tab: Tab) -> str:
    try:
        return await tab.evaluate("location.href") or ""
    except Exception:
        return ""


async def is_challenged(tab: Tab) -> bool:
    url = (await current_url(tab)).lower()
    return any(marker in url for marker in CHALLENGE_URL_MARKERS)


async def _ainput() -> str:
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, input)


async def wait_for_human(tab: Tab) -> None:
    while await is_challenged(tab):
        console.print(
            "\n[bold yellow]Cần thao tác tay:[/] giải captcha hoặc đăng nhập trên cửa sổ "
            "Brave, rồi quay lại đây nhấn Enter."
        )
        await _ainput()
        await asyncio.sleep(3)
        if await is_challenged(tab):
            log.warning("Vẫn đang bị chặn, chờ thêm 5s...")
            await asyncio.sleep(5)
        else:
            log.info("Đã qua captcha, tải lại trang")
            try:
                await tab.reload()
            except Exception:
                pass
            await asyncio.sleep(3)


async def goto(
    tab: Tab, url: str, settings: Settings, wait: float | None = None, retries: int | None = None
) -> None:
    wait = settings.page_load_wait if wait is None else wait
    retries = settings.page_retries if retries is None else retries

    last: Exception | None = None
    for _ in range(retries + 1):
        try:
            await tab.get(url)
            last = None
            break
        except Exception as e:  # timeout / mạng chập chờn
            last = e
            await asyncio.sleep(2)
    if last is not None:
        raise last

    await asyncio.sleep(wait)
    await wait_for_human(tab)


async def polite_sleep(settings: Settings) -> None:
    await asyncio.sleep(random.uniform(settings.delay_min, settings.delay_max))


async def scroll_to(element: Element) -> None:
    try:
        await element.scroll_into_view()
    except Exception:
        pass


async def scroll_fraction(tab: Tab, fraction: float) -> None:
    try:
        await tab.evaluate(f"window.scrollTo(0, document.body.scrollHeight * {fraction});")
    except Exception:
        pass


async def page_html(tab: Tab) -> str:
    try:
        return await tab.get_content()
    except Exception:
        return ""


async def count_children(element: Element, selectors: Sequence[Selector]) -> int:
    return len(await select_all(element, selectors))
