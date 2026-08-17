from shopee_scraper.extraction import FALLBACK, MISS, PRIMARY, ExtractionReport


def test_records_split_across_tiers():
    report = ExtractionReport()
    report.record("price", PRIMARY)
    report.record("price", FALLBACK)
    report.record("price", MISS)

    stat = report.fields["price"]
    assert (stat.total, stat.primary, stat.fallback, stat.miss) == (3, 1, 1, 1)
    assert stat.hit == 2


def test_no_flag_below_min_samples():
    report = ExtractionReport()
    report.record("name", MISS)
    report.record("name", MISS)
    assert report.flags() == []


def test_dead_selector_flagged():
    report = ExtractionReport()
    for _ in range(3):
        report.record("name", MISS)
    flags = report.flags()
    assert len(flags) == 1
    assert flags[0].startswith("selector-dead: name")


def test_degraded_selector_flagged():
    report = ExtractionReport()
    for _ in range(4):
        report.record("price", FALLBACK)
    flags = report.flags()
    assert len(flags) == 1
    assert flags[0].startswith("selector-degraded: price")


def test_healthy_primary_no_flag():
    report = ExtractionReport()
    for _ in range(5):
        report.record("price", PRIMARY)
    assert report.flags() == []


def test_to_dict_shape():
    report = ExtractionReport()
    report.record("name", PRIMARY)
    assert report.to_dict() == {"name": {"total": 1, "primary": 1, "fallback": 0, "miss": 0}}
