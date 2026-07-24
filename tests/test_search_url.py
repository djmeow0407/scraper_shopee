from shopee_scraper.config import Settings
from shopee_scraper.scrapers import SearchScraper


def scraper(**kwargs) -> SearchScraper:
    kwargs.setdefault("keyword", "bánh cốm")
    kwargs.setdefault("num_products", 10)
    return SearchScraper(settings=Settings(), **kwargs)


def test_keyword_is_url_encoded():
    url = scraper().search_url()
    assert "keyword=b%C3%A1nh%20c%E1%BB%91m" in url


def test_facet_present_on_every_page():
    """Bản cũ chỉ gắn facet cho trang đầu rồi dựng lại URL không có facet."""
    s = scraper(category="100017")
    assert all("facet=100017" in s.search_url(page) for page in range(3))


def test_no_facet_when_category_missing():
    assert "facet=" not in scraper().search_url()


def test_page_and_sort_applied():
    url = scraper(sort_by="sales").search_url(page=2)
    assert "page=2" in url
    assert "sortBy=sales" in url


def test_output_filename_slugified():
    assert scraper().output_file == "search_b_nh_c_m.json"
