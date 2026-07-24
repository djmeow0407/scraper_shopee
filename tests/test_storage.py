import json

from shopee_scraper.models import ProductInfo, ProductRecord
from shopee_scraper.storage import JsonStore


def record(url: str) -> ProductRecord:
    return ProductRecord(product=ProductInfo(url=url, name="Sản phẩm"))


def test_new_store_is_empty(tmp_path):
    store = JsonStore(tmp_path / "out.json")
    assert len(store) == 0
    assert not store.has("bất kỳ")


def test_add_and_save_roundtrip(tmp_path):
    path = tmp_path / "out.json"
    store = JsonStore(path)
    store.add(record("https://shopee.vn/a-i.1.2"))
    store.save()

    loaded = json.loads(path.read_text(encoding="utf-8"))
    assert len(loaded) == 1
    assert loaded[0]["product"]["url"] == "https://shopee.vn/a-i.1.2"


def test_resume_skips_known_urls(tmp_path):
    path = tmp_path / "out.json"
    first = JsonStore(path)
    first.add(record("https://shopee.vn/a-i.1.2"))
    first.save()

    second = JsonStore(path)
    assert len(second) == 1
    assert second.has("https://shopee.vn/a-i.1.2")


def test_reads_legacy_flat_schema(tmp_path):
    path = tmp_path / "out.json"
    path.write_text(
        json.dumps([{"link": "https://shopee.vn/a-i.1.2", "name": "cũ"}]),
        encoding="utf-8",
    )

    store = JsonStore(path)
    assert store.has("https://shopee.vn/a-i.1.2")


def test_corrupt_file_starts_fresh(tmp_path):
    path = tmp_path / "out.json"
    path.write_text("{ hỏng", encoding="utf-8")

    store = JsonStore(path)
    assert len(store) == 0


def test_save_is_atomic(tmp_path):
    path = tmp_path / "out.json"
    store = JsonStore(path)
    store.add(record("https://shopee.vn/a-i.1.2"))
    store.save()

    assert not path.with_suffix(".json.tmp").exists()
