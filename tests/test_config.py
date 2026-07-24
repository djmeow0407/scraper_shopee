import pytest
from pydantic import ValidationError

from shopee_scraper.config import Settings


def test_defaults():
    settings = Settings()
    assert settings.review_limit == 30
    assert settings.delay_min < settings.delay_max


def test_toml_overrides_defaults(tmp_path):
    config = tmp_path / "shopee.config.toml"
    config.write_text("[scraper]\nreview_limit = 99\nheadless = true\n", encoding="utf-8")

    settings = Settings.load(config)
    assert settings.review_limit == 99
    assert settings.headless is True


def test_cli_overrides_toml(tmp_path):
    config = tmp_path / "shopee.config.toml"
    config.write_text("[scraper]\nreview_limit = 99\n", encoding="utf-8")

    assert Settings.load(config, review_limit=5).review_limit == 5


def test_none_override_does_not_clobber_toml(tmp_path):
    config = tmp_path / "shopee.config.toml"
    config.write_text("[scraper]\nreview_limit = 99\n", encoding="utf-8")

    assert Settings.load(config, review_limit=None).review_limit == 99


def test_env_overrides_toml(tmp_path, monkeypatch):
    config = tmp_path / "shopee.config.toml"
    config.write_text("[scraper]\nreview_limit = 99\n", encoding="utf-8")
    monkeypatch.setenv("SHOPEE_REVIEW_LIMIT", "7")

    assert Settings.load(config).review_limit == 7


def test_flat_toml_without_table(tmp_path):
    config = tmp_path / "shopee.config.toml"
    config.write_text("review_limit = 42\n", encoding="utf-8")

    assert Settings.load(config).review_limit == 42


def test_delay_order_validated():
    with pytest.raises(ValidationError):
        Settings(delay_min=10, delay_max=1)


def test_resolve_output_creates_dir(tmp_path):
    settings = Settings(output_dir=tmp_path / "out")
    path = settings.resolve_output("a.json")
    assert path.parent.is_dir()
