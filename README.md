
## Cài đặt

Trước khi chạy, hãy đảm bảo bạn đã cài đặt các thư viện cần thiết:

```bash
pip install -r requirements.txt
```

## Các chức năng chính

Bộ tool bao gồm 3 script chính nằm trong thư mục `src/`:

### 1. Thu thập dữ liệu từ Shop (`src/retriv_shop.py`)
Dùng để lấy danh sách sản phẩm của một Shop cụ thể.

**Cú pháp:**
```bash
python src/retriv_shop.py --url "LINK_SHOP" --num [SỐ_LƯỢNG_SP] --review-limit [SỐ_REVIEW_MỖI_SP]
```

**Ví dụ:**
```bash
# Lấy 10 sản phẩm từ shop, mỗi sản phẩm lấy 20 review
python src/retriv_shop.py --url "https://shopee.vn/banhkeobaominhchgtsp" --num 10 --review-limit 20
```

### 2. Thu thập dữ liệu theo Từ khóa (`src/retriv_data.py`)
Dùng để tìm kiếm và lấy dữ liệu sản phẩm theo từ khóa (keyword).

**Cú pháp:**
```bash
python src/retriv_data.py --keyword "TỪ_KHÓA" --num [SỐ_LƯỢNG_SP] --review-limit [SỐ_REVIEW_MỖI_SP]
```

**Ví dụ:**
```bash
# Tìm kiếm "bánh cốm", lấy 5 sản phẩm đầu tiên
python src/retriv_data.py --keyword "bánh cốm" --num 5 --review-limit 10
```
*Tùy chọn thêm:*
- `--sort-by`: Sắp xếp theo `relevancy` (liên quan), `sales` (bán chạy), `ctime` (mới nhất), `price` (giá).

### 3. Thu thập dữ liệu 1 Sản phẩm (`src/retriv_product.py`)
Dùng để lấy chi tiết của **một link sản phẩm duy nhất**.

**Cú pháp:**
```bash
python src/retriv_product.py --url "LINK_SẢN_PHẨM" --review-limit [SỐ_REVIEW]
```

**Ví dụ:**
```bash
python src/retriv_product.py --url "https://shopee.vn/product/123/456" --review-limit 50
```

## Lưu ý quan trọng

1.  **Captcha**: Tool sử dụng trình duyệt thật để tránh bị chặn. Nếu Shopee yêu cầu nhập Captcha hoặc đăng nhập, màn hình terminal sẽ hiện thông báo. Bạn cần **mở cửa sổ trình duyệt lên, giải captcha thủ công**, sau đó **quay lại terminal và nhấn Enter** để tool tiếp tục chạy.
2.  **File Log**: Kết quả sẽ được lưu vào file `.json` tương ứng với tên shop/từ khóa/sản phẩm.
