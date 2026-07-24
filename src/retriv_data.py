import sys
import time
import json
import logging
import argparse
import re
import os
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException # Added import
from tqdm import tqdm

try:
    from src.base_scraper import BaseShopeeScraper
except ImportError:
    from base_scraper import BaseShopeeScraper

class ProductScraper(BaseShopeeScraper):
    def __init__(self, keyword, num_products, index_only, review_limit, sort_by="relevancy", category=None, time_range=None):
        super().__init__()
        self.keyword = keyword
        self.num_products = num_products
        self.index_only = index_only
        self.review_limit = review_limit
        self.sort_by = sort_by
        self.category = category
        self.time_range = time_range
        
        self.output_file = f"shopee_{re.sub(r'[^a-z0-9_]+', '', self.keyword.lower())}.json"
        
        self.scraped_links = set()
        self._load_existing_data()

    def _load_existing_data(self):
        self.existing_products = []
        if os.path.exists(self.output_file):
            try:
                with open(self.output_file, 'r', encoding='utf-8') as f:
                    self.existing_products = json.load(f)
                # Handle old schema (flat) vs new schema (nested) fallback
                self.scraped_links = set()
                for prod in self.existing_products:
                    # New schema
                    if 'product' in prod and 'url' in prod['product']:
                         self.scraped_links.add(prod['product']['url'])
                    # Old schema
                    elif 'link' in prod:
                         self.scraped_links.add(prod['link'])
                         
                logging.info(f"Loaded {len(self.existing_products)} existing products")
            except Exception as e:
                logging.warning(f"Could not load existing data: {e}")
                self.existing_products = []

    def _periodic_save(self, products):
        try:
            with open(self.output_file, 'w', encoding='utf-8') as f:
                json.dump(products, f, ensure_ascii=False, indent=2)
            logging.info(f"Periodic save: {len(products)} products saved")
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

    def _get_products(self, driver):
        products_xpath = '//*[@id="main"]/div/div[2]/div/div/div/div/div/div[2]/section/ul'
        products = []
        products_per_page = 60
        total_pages = -(-self.num_products // products_per_page)

        for page in range(total_pages):
            search_url = f"https://shopee.vn/search?keyword={re.sub(r'\s+', '%20', self.keyword.strip())}&page={page}&sortBy={self.sort_by}"
            logging.info(f"Loading page {page+1}/{total_pages}: {search_url}")

            driver.get(search_url)
            time.sleep(4)
            self._wait_for_captcha(driver)
            driver.implicitly_wait(3)

            try:
                container = driver.find_element(By.XPATH, products_xpath)
                items = container.find_elements(By.XPATH, './/li')
            except NoSuchElementException:
                # Fallback selector for main container
                try: 
                    items = driver.find_elements(By.CSS_SELECTOR, ".shopee-search-item-result__item")
                except:
                    logging.warning(f"Product container not found on page {page+1}. Skipping.")
                    continue
            
            if not items:
                 try: items = driver.find_elements(By.CSS_SELECTOR, "div[data-sqe='item']")
                 except: pass

            for idx, li in enumerate(items):
                if len(products) >= self.num_products:
                    return products

                try:
                    # Try finding link anchor
                    link_elem = li.find_element(By.TAG_NAME, 'a')
                    link = link_elem.get_attribute("href")
                except:
                    link = ""

                if link and link in self.scraped_links:
                    continue

                try:
                    name = li.find_element(By.XPATH, './/div[contains(@class, "line-clamp-2")]').text.strip()
                except: name = "Unknown"
                
                try:
                    price = li.find_element(By.XPATH, './/div[contains(@class, "truncate")]').text
                except: price = "0"
                
                try:
                    img = li.find_element(By.TAG_NAME, 'img').get_attribute("src")
                except: img = ""

                products.append({
                    "url": link,
                    "link": link,
                    "name": name,
                    "price": price,
                    "img": img,
                })

            logging.info(f"Page {page+1} scraped, total products candidate: {len(products)}")
            time.sleep(2)
        return products

    def run(self):
        driver = self.setup_driver()
        
        try:
            url = self._build_search_url()
            logging.info(f"Search URL: {url}")
            driver.get(url)
            time.sleep(5)
            self._wait_for_captcha(driver)
            
            new_products_meta = self._get_products(driver)
            logging.info(f"Found {len(new_products_meta)} products to process")
            
            final_products = self.existing_products.copy()
            
            for idx, meta in enumerate(tqdm(new_products_meta, desc="Processing products"), 1):
                try:
                    if meta["url"] in self.scraped_links: continue
                    
                    if not self.index_only:
                        details = self.scrape_product_details(driver, meta["url"], product_meta=meta, review_limit=self.review_limit)
                        final_products.append(details)
                        self.scraped_links.add(meta["url"])
                    else:
                        details = {
                            "product": {
                                "id": "0_0",
                                "url": meta["url"],
                                "name": meta["name"],
                                "price": self._parse_price(meta["price"]),
                                "image": meta["img"],
                                "stock_status": "Unknown",
                                "category": [],
                                "brand": "Unknown",
                                "weight": {"value": 0, "unit": ""},
                                "origin": "Unknown",
                                "shelf_life_months": 0,
                                "ship_from": "Unknown"
                            },
                            "description": {"raw_text": ""},
                            "reviews": [],
                            "shop": {"name": "Unknown", "url": "", "platform": "Shopee"},
                            "meta": {
                                "scraped_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
                                "source": "Shopee",
                                "language": "vi"
                            }
                        }
                        final_products.append(details)
                        self.scraped_links.add(meta["url"])
                        
                    if idx % 5 == 0:
                        self._periodic_save(final_products)
                        
                except Exception as e:
                    logging.error(f"Error processing {meta.get('url')}: {e}")
                    self._periodic_save(final_products)
                    
            self._periodic_save(final_products)
            logging.info(f"Completed! Total {len(final_products)} products saved")
            
        except Exception as e:
             logging.error(f"Fatal: {e}", exc_info=True)
        finally:
            self.teardown_driver(driver)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Shopee Search Scraper")
    parser.add_argument("-k", "--keyword", required=True, help="Search keyword")
    parser.add_argument("-n", "--num", type=int, default=10, help="Number of products to scrape")
    parser.add_argument("-r", "--review-limit", type=int, default=30, help="Max reviews per product")
    parser.add_argument("--index-only", action="store_true", default=False, help="Only scrape product info, skip reviews")
    parser.add_argument("--all-star-types", action="store_true", default=False, help="(Deprecated) Scrape reviews by star type")
    parser.add_argument("--star-limit-per-type", type=int, default=10, help="(Deprecated)")
    parser.add_argument("--sort-by", type=str, default="relevancy", choices=["relevancy", "sales", "ctime", "price"])
    parser.add_argument("-c", "--category", type=str, default=None)
    parser.add_argument("-t", "--time-range", type=str, default=None)
    
    args = parser.parse_args()
    scraper = ProductScraper(
        args.keyword,
        args.num,
        args.index_only,
        args.review_limit,
        sort_by=args.sort_by,
        category=args.category,
        time_range=args.time_range
    )
    scraper.run()