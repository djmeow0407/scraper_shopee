import sys
import time
import json
import logging
import argparse
import re
import os
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By

try:
    from src.base_scraper import BaseShopeeScraper
except ImportError:
    from base_scraper import BaseShopeeScraper

class ShopScraper(BaseShopeeScraper):
    def __init__(self, shop_url, num_products, review_limit=10):
        super().__init__()
        self.shop_url = shop_url
        self.num_products = num_products
        self.review_limit = review_limit
        
        shop_name = re.sub(r'https?://(www\.)?shopee\.vn/', '', self.shop_url).split('?')[0].split('/')[0]
        self.output_file = f"shop_{re.sub(r'[^a-z0-9_]+', '', shop_name)}.json"
        
        self.scraped_links = set()
        self._load_existing_data()

    def _load_existing_data(self):
        self.existing_products = []
        if os.path.exists(self.output_file):
            try:
                with open(self.output_file, 'r', encoding='utf-8') as f:
                    self.existing_products = json.load(f)
                self.scraped_links = {
                    prod.get('product', {}).get('url', '') 
                    for prod in self.existing_products 
                    if prod.get('product', {}).get('url')
                }
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

    def run(self):
        driver = self.setup_driver()
        
        try:
            logging.info(f"Navigating to {self.shop_url}")
            driver.get(self.shop_url)
            time.sleep(3)
            self._wait_for_captcha(driver)
            
            shop_header = ""
            try: shop_header = driver.find_element(By.CLASS_NAME, "shopee-shop-header").text
            except: pass
            
            products = self.existing_products.copy()
            page = 0
            
            while True:
                base = self.shop_url.split('?')[0]
                driver.get(f"{base}?page={page}&sortBy=pop")
                time.sleep(2)
                for _ in range(3):
                    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                    time.sleep(1)
                
                links = []
                links = driver.find_elements(By.XPATH, '//a[@data-sqe="link"]')
                if not links: links = driver.find_elements(By.CSS_SELECTOR, ".shop-search-result-view__item a")
                if not links:
                    elems = driver.find_elements(By.CSS_SELECTOR, "a")
                    links = [e for e in elems if e.get_attribute("href") and "-i." in e.get_attribute("href") and "shopid" not in e.get_attribute("href")]
                
                if not links or len(products) >= self.num_products:
                    logging.info(f"Page {page}: No products found or limit reached.")
                    break
                
                logging.info(f"Page {page}: Found {len(links)} products.")
                
                listing_items = []
                for l in links:
                    url = l.get_attribute("href")
                    if not url: continue
                    name, price = "Unknown", "0"
                    try:
                        name = l.find_element(By.XPATH, './/div[contains(@class, "line-clamp-2")]').text
                        price = l.find_element(By.XPATH, './/div[contains(@class, "truncate")]').text
                    except: pass
                    listing_items.append({"url": url, "name": name, "price": price})

                for item in listing_items:
                    if len(products) >= self.num_products: break
                    if any(p.get("product", {}).get("url") == item["url"] for p in products):
                        continue
                        
                    logging.info(f"Processing: {item['name']}")
                    obj = self.scrape_product_details(driver, item["url"], product_meta=item, review_limit=self.review_limit, shop_header=shop_header.split('\n')[0] if shop_header else "Unknown")
                    
                    products.append(obj)
                    self._periodic_save(products)
                page += 1
            self._periodic_save(products)
        except Exception as e:
            logging.error(f"Fatal: {e}", exc_info=True)
        finally:
            self.teardown_driver(driver)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", required=True)
    parser.add_argument("--num", type=int, default=10)
    parser.add_argument("--review-limit", type=int, default=10)
    args = parser.parse_args()
    
    scraper = ShopScraper(args.url, args.num, args.review_limit)
    scraper.run()
