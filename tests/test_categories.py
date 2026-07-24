from pathlib import Path

from shopee_scraper.categories import CategoryIndex

REAL_CSV = Path(__file__).resolve().parents[1] / "data" / "shopee_categories.csv"

HEADER = "nganh_cap_1,nganh_cap_2,nganh_cap_3,nganh_cap_4,nganh_cap_5,ma_nganh,mo_ta_vi_du\n"


def write_csv(tmp_path: Path, body: str) -> Path:
    path = tmp_path / "cats.csv"
    path.write_text(HEADER + body, encoding="utf-8")
    return path


def test_lookup_by_code(tmp_path):
    path = write_csv(tmp_path, "Thời Trang Nữ,Áo,Áo thun,-,-,100350,áo phông\n")
    index = CategoryIndex.load(path)

    info = index.get("100350")
    assert info is not None
    assert info.example == "áo phông"


def test_placeholder_levels_dropped(tmp_path):
    path = write_csv(tmp_path, "Thời Trang Nữ,Áo,Áo thun,-,-,100350,\n")
    info = CategoryIndex.load(path).get("100350")

    assert info.path == ["Thời Trang Nữ", "Áo", "Áo thun"]


def test_unknown_code_returns_none(tmp_path):
    path = write_csv(tmp_path, "A,-,-,-,-,111,\n")
    index = CategoryIndex.load(path)

    assert index.get("999") is None
    assert index.get(None) is None


def test_rows_without_code_skipped(tmp_path):
    path = write_csv(tmp_path, "A,-,-,-,-,,\nB,-,-,-,-,222,\n")
    assert len(CategoryIndex.load(path)) == 1


def test_missing_file_is_empty(tmp_path):
    assert len(CategoryIndex.load(tmp_path / "khong-ton-tai.csv")) == 0


def test_bundled_csv_loads():
    index = CategoryIndex.load(REAL_CSV)
    assert len(index) > 1000
