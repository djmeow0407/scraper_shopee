from __future__ import annotations

import logging
import random
import re
import shutil
import subprocess
import time
from collections.abc import Iterator, Sequence
from contextlib import contextmanager

import undetected_chromedriver as uc
from selenium.common.exceptions import WebDriverException
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement

from .config import Settings
from .console import console
from .selectors import CHALLENGE_URL_MARKERS, Selector

log = logging.getLogger(__name__)

CHROME_BINARIES = ["google-chrome", "google-chrome-stable", "chromium", "chromium-browser", "chrome"]


def detect_chrome_version() -> int | None:
    """Major version của Chrome đã cài, None nếu không dò được."""
    for binary in CHROME_BINARIES:
        path = shutil.which(binary)
        if not path:
            continue
        try:
            out = subprocess.run(
                [path, "--version"], capture_output=True, text=True, timeout=10
            ).stdout
        except (subprocess.SubprocessError, OSError):
            continue
        match = re.search(r"(\d+)\.", out)
        if match:
            return int(match.group(1))
    return None


@contextmanager
def chrome_session(settings: Settings) -> Iterator[WebDriver]:
    options = uc.ChromeOptions()
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument(f"--window-size={settings.window_size}")
    if settings.user_data_dir:
        options.add_argument(f"--user-data-dir={settings.user_data_dir}")

    version = settings.chrome_version or detect_chrome_version()
    if version:
        log.debug("Chrome major version: %s", version)
    else:
        log.warning("Không dò được phiên bản Chrome, để undetected-chromedriver tự xử lý")

    driver = uc.Chrome(options=options, version_main=version, headless=settings.headless)
    driver.set_page_load_timeout(settings.page_load_timeout)
    try:
        yield driver
    finally:
        teardown(driver)


def teardown(driver: WebDriver) -> None:
    """uc.Chrome hay ném WinError 6 / OSError trong __del__, dập trước cho gọn."""
    try:
        driver.service.process.kill()
    except Exception:
        pass
    try:
        driver.quit()
    except Exception:
        pass
    driver.quit = lambda: None  # type: ignore[method-assign]


def find_first(
    scope: WebDriver | WebElement, selectors: Sequence[Selector]
) -> WebElement | None:
    for by, value in selectors:
        try:
            return scope.find_element(by, value)
        except WebDriverException:
            continue
    return None


def find_all(scope: WebDriver | WebElement, selectors: Sequence[Selector]) -> list[WebElement]:
    for by, value in selectors:
        try:
            found = scope.find_elements(by, value)
        except WebDriverException:
            continue
        if found:
            return found
    return []


def text_of(scope: WebDriver | WebElement, selectors: Sequence[Selector], default: str = "") -> str:
    el = find_first(scope, selectors)
    if el is None:
        return default
    try:
        return el.text.strip() or default
    except WebDriverException:
        return default


def attr_of(
    scope: WebDriver | WebElement,
    selectors: Sequence[Selector],
    attribute: str,
    default: str = "",
) -> str:
    el = find_first(scope, selectors)
    if el is None:
        return default
    try:
        return el.get_attribute(attribute) or default
    except WebDriverException:
        return default


def is_challenged(driver: WebDriver) -> bool:
    try:
        url = driver.current_url.lower()
    except WebDriverException:
        return False
    return any(marker in url for marker in CHALLENGE_URL_MARKERS)


def wait_for_human(driver: WebDriver) -> None:
    """Chặn cho tới khi captcha/đăng nhập được giải bằng tay."""
    while is_challenged(driver):
        console.print(
            "\n[bold yellow]Cần thao tác tay:[/] mở cửa sổ Chrome, giải captcha "
            "hoặc đăng nhập, rồi quay lại đây nhấn Enter."
        )
        input()
        time.sleep(3)
        if is_challenged(driver):
            log.warning("Vẫn đang bị chặn, chờ thêm 5s...")
            time.sleep(5)
        else:
            log.info("Đã qua captcha, tải lại trang")
            driver.refresh()
            time.sleep(3)


def goto(driver: WebDriver, url: str, wait: float = 3.0) -> None:
    driver.get(url)
    time.sleep(wait)
    wait_for_human(driver)


def polite_sleep(settings: Settings) -> None:
    time.sleep(random.uniform(settings.delay_min, settings.delay_max))


def scroll_to(driver: WebDriver, element: WebElement) -> None:
    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", element)


def scroll_fraction(driver: WebDriver, fraction: float) -> None:
    driver.execute_script(f"window.scrollTo(0, document.body.scrollHeight * {fraction});")
