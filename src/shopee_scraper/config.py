from __future__ import annotations

import os
import tomllib
from pathlib import Path
from typing import Any

from pydantic import BaseModel, field_validator

CONFIG_FILENAME = "shopee.config.toml"
ENV_PREFIX = "SHOPEE_"


class Settings(BaseModel):
    headless: bool = False
    chrome_version: int | None = None  # None = tự dò từ Chrome đã cài
    page_load_timeout: int = 30
    window_size: str = "1920,1080"
    user_data_dir: str | None = None

    delay_min: float = 3.0
    delay_max: float = 7.0
    review_page_delay: float = 1.5

    review_limit: int = 30
    star_limit_per_type: int = 10
    save_every: int = 5
    max_retries: int = 2

    output_dir: Path = Path("out")
    categories_csv: Path = Path("data/shopee_categories.csv")

    @field_validator("output_dir", "categories_csv", mode="before")
    @classmethod
    def _as_path(cls, v: Any) -> Any:
        return Path(v) if isinstance(v, str) else v

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

    def resolve_output(self, filename: str) -> Path:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        return self.output_dir / filename
