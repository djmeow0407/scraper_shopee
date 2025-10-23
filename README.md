## Shopee Scraper

This project provides a robust Python tool for scraping product and review data from **Shopee.vn**.
It uses **Selenium with undetected-chromedriver** to avoid detection and supports a wide range of CLI options for flexible data collection.

---

### Installation

```bash
pip install -r requirements.txt
```

---

### Basic Usage

```bash
python src/retriv_data.py -k "Raspberry pi" -n 10
```

---

### CLI Options

| Option                  | Description                                         | Default      | Example                    |
| ----------------------- | --------------------------------------------------- | ------------ | -------------------------- |
| `-k`, `--keyword`       | Search keyword                                      | Raspberry pi | `-k "iPhone 15"`           |
| `-n`, `--num`           | Number of products to scrape                        | 10           | `-n 50`                    |
| `-r`, `--review-limit`  | Max reviews per product                             | 30           | `-r 100`                   |
| `--index-only`          | Only scrape product info, skip reviews              | False        | `--index-only`             |
| `--all-star-types`      | Scrape reviews by star type (1-5 stars)             | False        | `--all-star-types`         |
| `--star-limit-per-type` | Max reviews per star type (with `--all-star-types`) | 10           | `--star-limit-per-type 20` |
| `--sort-by`             | Sort by: relevancy, sales, ctime, price             | relevancy    | `--sort-by sales`          |
| `-c`, `--category`      | Shopee category ID (see below)                      | None         | `-c 11035954`              |
| `-t`, `--time-range`    | Filter by time: 1month, 3months, 6months, 1year     | None         | `-t 1month`                |

---

### Example Commands

#### Scrape 20 best-selling headphones

```bash
python src/retriv_data.py -k "headphones" --sort-by sales -n 20
```

#### Scrape 15 newest phones

```bash
python src/retriv_data.py -k "phone" --sort-by ctime -n 15
```

#### Scrape laptops in a specific category

```bash
python src/retriv_data.py -k "laptop" -c 11035954 -n 20
```

#### Scrape reviews by star type

```bash
python src/retriv_data.py -k "mouse" --all-star-types --star-limit-per-type 20 -n 5
```

#### Only scrape product info (no reviews)

```bash
python src/retriv_data.py -k "keyboard" -n 50 --index-only
```

---

### Output Data

The output is a JSON file named `shopee_<keyword>.json` containing a list of products.
Each product includes:

* `link`: Product URL
* `name`: Product name
* `price`: Price
* `rating`: Average rating
* `img`: Image URL
* `location`: Seller location

If `--index-only` is not used, each product also includes:

* `category`: Product category
* `description`: Product description
* `detailed_rating`: Ratings breakdown by star
* `total_rating`: Total number of ratings
* `comments`: List of reviews

Each review contains:

* `author`: Reviewer name
* `rating`: Star rating (1-5)
* `time`: Review time
* `content`: Review text
* `seller_respond`: Seller's response (if any)
* `like_count`: Number of likes

---

### How to Get Category IDs

To find the correct Shopee category ID for the `-c`/`--category` option, visit:
👉 [https://banhang.shopee.vn/edu/category-guide](https://banhang.shopee.vn/edu/category-guide)


Or find it in 'shopee_categories.csv'


Search or browse for your desired category and copy the corresponding ID from the table.

---

### Notes & Recommendations

* **Login Required for Full Results:**
  Shopee restricts the number of visible products for non-logged-in users.
  To scrape more than ~40 products, **you must log in to Shopee in the opened browser window** before continuing.

* **Captcha Handling:**
  If a captcha page appears, **you must solve it immediately** in the browser window.
  The scraper will automatically continue once the captcha is cleared.

* **Delays:**
  The tool includes randomized delays to reduce the risk of being rate-limited or blocked.

* **Periodic Save:**
  Data is saved every 5 products and again upon completion to prevent loss.

* **Resume Support:**
  If scraping is interrupted, re-run the same command — previously saved products will be skipped.

---

### Requirements

* Python 3.7+
* undetected-chromedriver
* selenium
* tqdm

(if you using 3.13 python, please install setuptools (already included in `requirement.txt`))

Install all dependencies with:

```bash
pip install -r requirements.txt
```

---

### ⚠️ Disclaimer

This project is intended **for research, educational, and personal learning purposes only.**
It is **not designed or authorized for commercial or large-scale use.**
The author is **not affiliated with or endorsed by Shopee.**
Use responsibly and respect Shopee’s Terms of Service.

---

**Author:** djmeow
**Date:** October 22, 2025
