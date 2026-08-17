# shopee-scraper

Thu thập sản phẩm và đánh giá từ Shopee.vn, xuất ra JSON có schema ổn định để đưa
thẳng vào pipeline phân tích cảm xúc theo khía cạnh (ABSA).

## Cài đặt

Cần Python 3.11–3.13 và một trình duyệt Chromium (mặc định dò `brave-origin`,
rồi Brave/Chrome/Chromium). nodriver điều khiển trình duyệt qua CDP, không cần
webdriver binary.

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -e .
```

Kiểm tra:

```bash
shopee version
```

## Dùng

Ba chế độ crawl, cùng một schema đầu ra:

```bash
# Theo từ khoá
shopee search "bánh cốm" -n 50 -r 20

# Toàn bộ một shop
shopee shop https://shopee.vn/banhkeobaominhchgtsp -n 30

# Một sản phẩm
shopee product "https://shopee.vn/...-i.201416673.20429274639" -r 100
```

Kết quả ghi vào `out/` (`search_<từ_khoá>.json`, `shop_<tên>.json`,
`product_<tên>_<id>.json`). Chạy lại cùng lệnh thì các link đã crawl được bỏ qua,
nên bị captcha giữa chừng cũng không mất công.

### Lấy đánh giá cân bằng theo sao

Mặc định tool lấy đánh giá mới nhất, mà Shopee thì đa số là 5 sao. Muốn có đủ
review tiêu cực để trị class imbalance:

```bash
shopee search "bánh cốm" -n 20 --stars all-stars
```

Chế độ này bấm lần lượt từng bộ lọc 1→5 sao, mỗi mức lấy `star_limit_per_type`
review (mặc định 10), và ghi mức sao đang lọc vào trường `star_bucket`.

### Lọc theo ngành hàng

```bash
shopee categories                          # cập nhật data/shopee_categories.csv
shopee search "kẹo" -c 100017 -n 30        # facet theo mã ngành
```

Mã ngành được gắn vào `product.category_info` của mỗi bản ghi.

## Cấu hình

Tham số CLI cho lần chạy, `shopee.config.toml` cho mặc định lâu dài:

```toml
[scraper]
review_limit = 50
star_limit_per_type = 15
delay_min = 4.0
delay_max = 9.0
headless = false
output_dir = "out"
```

Thứ tự ưu tiên: mặc định < `shopee.config.toml` < biến môi trường `SHOPEE_*` <
tham số CLI. Xem toàn bộ tuỳ chọn trong `src/shopee_scraper/config.py`.

## Schema đầu ra

Mỗi file là một mảng bản ghi. Xem `examples/output.sample.json` cho bản đầy đủ.

```jsonc
{
  "product": {
    "id": "201416673_20429274639",
    "url": "https://shopee.vn/...",
    "name": "Kẹo vừng cao cấp Bảo Minh 250gr",
    "price": { "value": 58000, "currency": "VND", "raw": "58.000 ₫" },
    "category": ["Shopee", "Bách Hóa Online", "Đồ ăn vặt", "Kẹo"],
    "category_info": { "code": "100017", "path": [...], "example": "..." },
    "brand": "Bảo Minh",
    "weight": { "value": 250, "unit": "g" },
    "origin": "Việt Nam",
    "shelf_life_months": 6,
    "ship_from": "Hà Nội",
    "rating": "4.9",
    "location": "Hà Nội"
  },
  "description": { "summary": "...", "manufacturer": "...", "hashtags": [], "specs": {} },
  "rating_breakdown": {
    "total": 1523,
    "by_star": { "1": 12, "2": 8, "3": 45, "4": 210, "5": 1248 },
    "with_comment": 890,
    "with_media": 156
  },
  "reviews": [
    {
      "username": "dung_gin",
      "rating": 5,
      "review_time": "2025-02-08T09:51:00",
      "variation": "250gr",
      "attributes": { "flavor": "ngon", "quality": "tốt" },
      "content": "Giao hàng nhanh, bánh rất ngon",
      "seller_response": { "responded": true, "content": "Shop cảm ơn ạ" },
      "helpful_votes": 3,
      "star_bucket": null
    }
  ],
  "shop": { "name": "...", "url": "...", "platform": "Shopee" },
  "meta": { "scraped_at": "...", "scraper_version": "0.3.0", "warnings": [] }
}
```

`meta.warnings` liệt kê bất thường của bản ghi (`name-missing`,
`price-zero-suspicious`, `price-missing`, `reviews-empty-despite-ratings`,
`category-missing`). Cuối mỗi lần chạy còn có bảng sức khỏe selector và file
`*.report.json` cạnh output; nếu một field bị gắn `selector-dead`/`selector-degraded`
thì Shopee đã đổi DOM — sửa `src/shopee_scraper/selectors.py`.

## Captcha & đăng nhập

Tool mở trình duyệt thật, không headless mặc định. Khi Shopee bắt captcha hoặc
đăng nhập, terminal dừng và nhắc: giải thủ công trên cửa sổ trình duyệt rồi quay
lại nhấn Enter. Bị chặn liên tục thì tăng `delay_min`/`delay_max`.

Trỏ `user_data_dir` vào một profile cố định để đăng nhập QR **một lần**; các lần
sau cookie còn nên bỏ qua được màn traffic/login:

```toml
[scraper]
user_data_dir = "~/.local/share/shopee-scraper/brave-profile"
```

## Cấu trúc

```
src/shopee_scraper/
├── cli.py            # lệnh typer: search / shop / product / categories
├── config.py         # Settings, ghép TOML + env + CLI
├── models.py         # schema pydantic của đầu ra
├── selectors.py      # toàn bộ selector Shopee, mỗi cái là danh sách ứng viên
├── browser.py        # phiên nodriver: điều hướng, tìm phần tử, xử lý captcha
├── extraction.py     # theo dõi selector nào khớp primary/fallback/miss
├── quality.py        # kiểm tra chéo bản ghi, sinh meta.warnings
├── report.py         # gộp số liệu một lần chạy + ghi *.report.json
├── storage.py        # ghi JSON nguyên tử + resume
├── categories.py     # tra cứu và cào bảng ngành hàng
├── parsers/          # bóc text -> model, không đụng trình duyệt
└── scrapers/         # base + ba chế độ crawl
```

Toàn bộ logic bóc tách nằm trong `parsers/`, không import nodriver, nên test được
bằng fixture text:

```bash
pip install -e ".[dev]"
pytest
ruff check src tests
```

## So với bản trước (v0.1)

Gộp bản `retriv_data.py` đơn khối trên GitHub với bản refactor `base_scraper.py`
ở máy, giữ ưu điểm của cả hai:

| Tính năng | v0.1 GitHub | v0.1 local | v0.2 |
|---|---|---|---|
| Crawl theo shop / theo 1 sản phẩm | ✗ | ✓ | ✓ |
| Schema lồng, parse giá/khối lượng/spec | ✗ | ✓ | ✓ |
| Lọc đánh giá theo từng mức sao | ✓ | ✗ (flag chết) | ✓ |
| `rating_breakdown` theo sao | ✓ | ✗ | ✓ |
| Tra ngành hàng từ CSV | ✓ | ✗ | ✓ |
| `rating` / `location` ở trang danh sách | ✓ | ✗ | ✓ |
| Nghỉ ngẫu nhiên giữa các trang | ✓ | ✗ (cố định 2s) | ✓ |
| Cờ chống phát hiện | ✓ | ✗ | ✓ |

Đã sửa:

- `--category` giờ giữ `facet` ở mọi trang; bản cũ dựng lại URL không có facet từ
  trang thứ hai nên bộ lọc mất tác dụng.
- Đánh giá bóc theo cấu trúc text thay vì bám chuỗi style inline dài.
- Ghi file nguyên tử (tmp + rename), không còn nguy cơ mất dữ liệu khi Ctrl-C
  giữa lúc ghi.
- Tên/giá sản phẩm có dự phòng qua thẻ `og:` khi class bị hash đổi.

## v0.3

- Đổi từ undetected-chromedriver/Selenium sang **nodriver** (async, điều khiển
  trực tiếp qua CDP), trình duyệt tự dò không cần webdriver binary.
- Thêm tầng quan sát: `extraction.py` theo dõi selector khớp primary/fallback/miss,
  `quality.py` kiểm tra chéo bản ghi, cuối mỗi lần chạy in bảng cảnh báo và ghi
  `*.report.json` — DOM đổi thì thấy ngay thay vì lặng lẽ trả rỗng.

Thay đổi cần biết khi chuyển sang v0.2:

- `python src/retriv_data.py -k "x"` → `shopee search "x"`
- `python src/retriv_shop.py --url U` → `shopee shop U`
- `python src/retriv_product.py --url U` → `shopee product U`
- `--all-star-types` → `--stars all-stars`
- Bỏ `--time-range`: cờ này chưa bao giờ lọc theo thời gian thật, nó chỉ đổi
  `sortBy` thành `ctime`. Cần hành vi đó thì dùng `--sort-by ctime`.
- File ra nằm trong `out/` thay vì thư mục hiện tại, và đổi tiền tố thành
  `search_`. File cũ vẫn đọc được (schema phẳng cũ vẫn resume được).

## Giấy phép

MIT.
