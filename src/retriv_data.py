import sys
import time
import json
import logging
import argparse
import re
import os
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException
from tqdm import tqdm

class ProductScraper:
    def __init__(self, keyword, num_products, index_only, review_limit, all_star_types=False, star_limit_per_type=10, sort_by="relevancy", category=None, time_range=None):
        self.keyword = keyword
        self.num_products = num_products
        self.index_only = index_only
        self.review_limit = review_limit
        self.all_star_types = all_star_types
        self.star_limit_per_type = star_limit_per_type
        self.sort_by = sort_by
        self.category = category
        self.time_range = time_range
        self.output_file = f"shopee_{re.sub(r'[^a-z0-9_]+', '', self.keyword.lower())}.json"
        self.scraped_links = set()
        self._setup_logging()
        self._load_existing_data()

    def _setup_logging(self):
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s [%(levelname)s] %(message)s",
            handlers=[logging.StreamHandler(sys.stdout)]
        )

    def _load_existing_data(self):
        self.existing_products = []
        if os.path.exists(self.output_file):
            try:
                with open(self.output_file, 'r', encoding='utf-8') as f:
                    self.existing_products = json.load(f)
                self.scraped_links = {prod.get('link', '') for prod in self.existing_products if prod.get('link')}
                logging.info(f"Loaded {len(self.existing_products)} existing products from {self.output_file}")
                logging.info(f"Resume mode: Will skip {len(self.scraped_links)} already scraped products")
            except Exception as e:
                logging.warning(f"Could not load existing data: {e}")
                self.existing_products = []

    def _periodic_save(self, products):
        try:
            with open(self.output_file, 'w', encoding='utf-8') as f:
                json.dump(products, f, ensure_ascii=False, indent=2)
            logging.info(f"Periodic save: {len(products)} products saved to {self.output_file}")
        except Exception as e:
            logging.warning(f"Periodic save failed: {e}")

    def _build_search_url(self):
        base_url = "https://shopee.vn/search?"
        params = []
        if self.category:
            params.append(f"facet={self.category}")
        kw_encoded = re.sub(r'\s+', '%20', self.keyword.strip())
        params.append(f"keyword={kw_encoded}")
        params.append("noCorrection=true")
        params.append("page=0")
        if self.time_range and self.sort_by != "ctime":
            params.append("sortBy=ctime")
        else:
            params.append(f"sortBy={self.sort_by}")
        return base_url + "&".join(params)
    def _wait_for_captcha(self, driver):
        blacklist = ["captcha", "/buyer/login", "/user/login", "/account/login", "/verify", "security"]
        while any(x in driver.current_url.lower() for x in blacklist):
            logging.info("Captcha or login detected. Please solve it and press Enter.")
            input()
            time.sleep(5)

    def _get_products(self, driver):
        products_xpath = '//*[@id="main"]/div/div[2]/div/div/div/div/div/div[2]/section/ul'
        try:
            container = driver.find_element(By.XPATH, products_xpath)
            items = container.find_elements(By.XPATH, './/li')
        except NoSuchElementException:
            logging.warning("Product container not found.")
            return []
        products = []
        for idx, li in enumerate(items):
            if idx >= self.num_products:
                break
            try:
                link = li.find_element(By.XPATH, './/a[@class="contents"]').get_attribute("href")
            except:
                link = ""
            
            if link and link in self.scraped_links:
                logging.info(f"Skipping already scraped product: {link}")
                continue
            
            try:
                name_elem = li.find_element(By.XPATH, './/div[contains(@class, "line-clamp-2")]')
                name = driver.execute_script("return arguments[0].textContent;", name_elem).strip()
            except:
                name = ""
            try:
                price = li.find_element(By.XPATH, './/div[@class="truncate flex items-baseline"]').text
            except:
                price = ""
            try:
                rating = li.find_element(By.XPATH, './/div[@class="text-shopee-black87 text-xs/sp14 flex-none"]').text
            except:
                rating = ""
            try:
                location = li.find_element(By.XPATH, './/div[@class="flex-shrink min-w-0 truncate text-shopee-black54 font-extralight text-sp10"]').text
            except:
                location = ""
            try:
                img = li.find_element(By.XPATH, './/img[@class="inset-y-0 w-full h-full pointer-events-none object-contain absolute"]').get_attribute("src")
            except:
                img = ""
            products.append({
                "link": link,
                "name": name,
                "price": price,
                "rating": rating,
                "img": img,
                "location": location
            })
        return products

    def _parse_star_count(self, text):
        text = text.lower().strip()
        if 'k' in text:
            text = text.replace('k', '')
            try:
                if ',' in text:
                    num = float(text.replace(',', '.'))
                else:
                    num = float(text)
                return int(num * 1000)
            except:
                return 0
        try:
            return int(text)
        except:
            return 0

    def _get_product_details(self, driver, product):
        driver.get(product["link"])
        driver.implicitly_wait(3)
        try:
            cat_xpath = '//*[@id="sll2-normal-pdp-main"]/div/div[1]/div/div[2]/div[2]/div/div[1]/div[1]/section[1]/div'
            product["category"] = driver.find_element(By.XPATH, cat_xpath).text
        except:
            product["category"] = ""
        try:
            desc_xpath = '//*[@id="sll2-normal-pdp-main"]/div/div[1]/div/div[2]/div[2]/div/div[1]/div[1]/section[2]/div/div'
            product["description"] = driver.find_element(By.XPATH, desc_xpath).text
        except:
            product["description"] = ""
        product["detailed_rating"] = {}
        total_ratings = 0
        try:
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            overview_xpath = '//*[@id="sll2-normal-pdp-main"]/div/div/div/div[2]/div[3]/div/div[1]/div[2]/div/div/div[2]/div[2]'
            overview_elem = driver.find_element(By.XPATH, overview_xpath)
            filters = overview_elem.find_elements(By.XPATH, './/div[contains(@class,"product-rating-overview__filter")]')
            for f in filters:
                text = f.text.strip()
                match = re.match(r'(\d+|\D+)\s?(Sao)?\s?\((\d+)\)', text)
                if match:
                    star = match.group(1).strip().lower()
                    val = int(match.group(3))
                    if star.isdigit():
                        key = f"{star}_star"
                    else:
                        key = "all" if "tất cả" in star else re.sub(r'\s+', '_', star)
                    if key == "có_bình_luận":
                        key = "commented"
                    elif key == "có_hình_ảnh_/_video":
                        key = "media"
                    product["detailed_rating"][key] = val
                    if star.isdigit():
                        total_ratings += val
        except:
            pass
        product["total_rating"] = total_ratings
        if self.all_star_types:
            all_reviews = []
            try:
                star_filters = driver.find_elements(By.CLASS_NAME, 'product-rating-overview__filter')
                for filter_div in star_filters:
                    try:
                        filter_text = filter_div.text.strip()
                        if '(' not in filter_text:
                            continue
                    except:
                        continue
                    match = re.match(r'(\d+)\s?[S|s]ao?\s?\(([^)]*)\)', filter_text)
                    if match:
                        star_count = self._parse_star_count(match.group(2))
                        if star_count > 0:
                            filter_div.click()
                            time.sleep(1)
                            all_reviews += self._get_reviews(driver, min(star_count, self.star_limit_per_type))
                product["comments"] = all_reviews
            except Exception as e:
                logging.warning(f"Unable to collect star-based reviews: {e}")
        else:
            all_reviews = self._get_reviews(driver, min(product["total_rating"], self.review_limit))
            product["comments"] = all_reviews

    def _get_reviews(self, driver, max_reviews):
        reviews = []
        try:
            start_time = time.time()
            rating_container = None
            while time.time() - start_time < 5:
                try:
                    rating_container = driver.find_element(By.CLASS_NAME, 'product-ratings__list')
                    break
                except:
                    time.sleep(0.1)
            if not rating_container:
                return reviews
        except:
            return reviews
        with tqdm(total=max_reviews, desc="Collecting reviews") as pbar:
            while len(reviews) < max_reviews:
                rating_items = rating_container.find_elements(By.XPATH, './/div[contains(@class,"shopee-product-rating__main")]')
                for item in rating_items:
                    if len(reviews) >= max_reviews:
                        break
                    review = {}
                    try:
                        review["author"] = item.find_element(By.CLASS_NAME,'shopee-product-rating__author-name').text.strip()
                    except:
                        review["author"] = ""
                    try:
                        star_elems = item.find_element(By.XPATH, './/div[@class="shopee-product-rating__rating"]').find_elements(By.XPATH, '*')
                        solid_stars = [s for s in star_elems if 'shopee-svg-icon icon-rating-solid--active icon-rating-solid' in (s.get_attribute('class') or '')]
                        review["rating"] = len(solid_stars)
                    except:
                        review["rating"] = 0
                    try:
                        review["time"] = item.find_element(By.XPATH, './/div[@class="shopee-product-rating__time"]').text.strip()
                    except:
                        review["time"] = ""
                    try:
                        review["content"] = item.find_element(By.XPATH, './/div[@style="position: relative; box-sizing: border-box; margin: 15px 0px; font-size: 14px; line-height: 20px; color: rgba(0, 0, 0, 0.87); word-break: break-word; white-space: pre-wrap;"]').text.strip()
                    except:
                        review["content"] = ""
                    try:
                        review["seller_respond"] = item.find_element(By.XPATH, './/div[@class="TQTPT9"]//div[@class="qiTixQ"]').text.strip()
                    except:
                        review["seller_respond"] = ""
                    try:
                        like_text = item.find_element(By.XPATH, './/div[@class="shopee-product-rating__like-count"]').text.strip()
                        review["like_count"] = int(like_text) if like_text.isdigit() else 0
                    except:
                        review["like_count"] = 0
                    reviews.append(review)
                    pbar.update(1)
                next_buttons = [ (By.CLASS_NAME, 'shopee-svg-icon icon-arrow-right') ]
                for by, value in next_buttons:
                    try:
                        next_button = driver.find_element(by, value)
                        next_button.click()
                        time.sleep(1)
                        break
                    except:
                        continue
        return reviews

    def run(self):
        options = uc.ChromeOptions()
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("--start-maximized")
        if sys.platform.startswith('linux'):
            options.add_argument("--disable-gpu")
        driver = uc.Chrome(options=options, enable_cdp_events=False, headless=False)
        driver.maximize_window()
        url = self._build_search_url()
        logging.info(f"Search URL: {url}")
        driver.get(url)
        time.sleep(5)
        self._wait_for_captcha(driver)
        driver.implicitly_wait(5)
        
        new_products = self._get_products(driver)
        logging.info(f"Found {len(new_products)} new products to scrape")
        
        all_products = self.existing_products.copy()
        
        for idx, prod in enumerate(tqdm(new_products, desc="Processing products"), 1):
            try:
                if not self.index_only:
                    self._get_product_details(driver, prod)
                all_products.append(prod)
                
                if prod.get('link'):
                    self.scraped_links.add(prod['link'])
                
                if idx % 5 == 0:
                    self._periodic_save(all_products)
                    
            except Exception as e:
                logging.error(f"Error processing product {prod.get('name', 'Unknown')}: {e}")
                self._periodic_save(all_products)
        
        driver.quit()

        self._periodic_save(all_products)
        logging.info(f"Completed! Total {len(all_products)} products saved to {self.output_file}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Shopee Scraper - Crawl product and review data from Shopee.vn")
    parser.add_argument("-k", "--keyword", default='Raspberry pi', help="Search keyword")
    parser.add_argument("-n", "--num", type=int, default=10, help="Number of products to scrape")
    parser.add_argument("-r", "--review-limit", type=int, default=30, help="Max reviews per product")
    parser.add_argument("--index-only", action="store_true", default=False, help="Only scrape product info, skip reviews")
    parser.add_argument("--all-star-types", action="store_true", default=False, help="Scrape reviews by star type")
    parser.add_argument("--star-limit-per-type", type=int, default=10, help="Max reviews per star type")
    parser.add_argument(
        "--sort-by",
        type=str,
        default="relevancy",
        choices=["relevancy", "sales", "ctime", "price"],
        help="Sort by: relevancy, sales, ctime, price"
    )
    parser.add_argument(
        "-c", "--category",
        type=str,
        default=None,
        help="Shopee category ID"
    )
    parser.add_argument(
        "-t", "--time-range",
        type=str,
        default=None,
        choices=["1month", "3months", "6months", "1year"],
        help="Filter by time: 1month, 3months, 6months, 1year"
    )
    args = parser.parse_args()
    scraper = ProductScraper(
        args.keyword,
        args.num,
        args.index_only,
        args.review_limit,
        all_star_types=args.all_star_types,
        star_limit_per_type=args.star_limit_per_type,
        sort_by=args.sort_by,
        category=args.category,
        time_range=args.time_range
    )
    scraper.run()