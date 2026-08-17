from __future__ import annotations

import os
import tomllib
from pathlib import Path
from typing import Any

from pydantic import BaseModel, field_validator

CONFIG_FILENAME = "shopee.config.toml"
ENV_PREFIX = "SHOPEE_"

# Ứng viên đường dẫn trình duyệt Chromium, dò theo thứ tự khi browser_path bỏ trống.
BROWSER_CANDIDATES = [
    "/usr/bin/brave-origin",
    "/usr/bin/brave-browser",
    "/usr/bin/brave",
    "/usr/bin/google-chrome",
    "/usr/bin/google-chrome-stable",
    "/usr/bin/chromium",
    "/usr/bin/chromium-browser",
]


class Settings(BaseModel):
    browser_path: str | None = None  # None = tự dò trong BROWSER_CANDIDATES
    headless: bool = False
    no_sandbox: bool = True
    lang: str = "vi-VN"
    user_data_dir: str | None = None  # trỏ vào profile đã đăng nhập để đỡ captcha
    page_load_wait: float = 4.0
    page_retries: int = 1

    delay_min: float = 3.0
    delay_max: float = 7.0
    review_page_delay: float = 1.5

    review_limit: int = 30
    star_limit_per_type: int = 10
    save_every: int = 5

    output_dir: Path = Path("out")
    categories_csv: Path = Path("data/shopee_categories.csv")

    @field_validator("output_dir", "categories_csv", mode="before")
    @classmethod
    def _as_path(cls, v: Any) -> Any:
        return Path(v) if isinstance(v, str) else v

    @field_validator("browser_path", "user_data_dir", mode="before")
    @classmethod
    def _as_str(cls, v: Any) -> Any:
        return str(v) if isinstance(v, Path) else v

    @field_validator("delay_max")
    @classmethod
    def _delay_order(cls, v: float, info: Any) -> float:
        lo = info.data.get("delay_min", 0.0)
        if v < lo:
            raise ValueError(f"delay_max ({v}) phải >= delay_min ({lo})")
        return v

    @classmethod
    def load(cls, config_path: Path | None = None, **overrides: Any) -> Settings:
        """Ghép mặc định < shopee.config.toml < env SHOPEE_* < tham số CLI."""
        data: dict[str, Any] = {}

        path = config_path or Path(CONFIG_FILENAME)
        if path.is_file():
            with path.open("rb") as f:
                loaded = tomllib.load(f)
            data.update(loaded.get("scraper", loaded))

        for field in cls.model_fields:
            raw = os.environ.get(f"{ENV_PREFIX}{field.upper()}")
            if raw is not None:
                data[field] = raw

        # None nghĩa là CLI không truyền, đừng ghi đè lên file config.
        data.update({k: v for k, v in overrides.items() if v is not None})
        return cls(**data)

    def resolve_browser(self) -> str:
        if self.browser_path:
            return self.browser_path
        for candidate in BROWSER_CANDIDATES:
            if Path(candidate).exists():
                return candidate
        raise FileNotFoundError(
            "Không tìm thấy trình duyệt Chromium. Đặt browser_path trong cấu hình "
            "hoặc dùng --browser."
        )

    def resolve_output(self, filename: str) -> Path:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        return self.output_dir / filename
