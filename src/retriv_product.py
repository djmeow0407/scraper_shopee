import argparse
import json
import logging
import re
import os
try:
    from src.base_scraper import BaseShopeeScraper
except ImportError:
    from base_scraper import BaseShopeeScraper

class SingleProductScraper(BaseShopeeScraper):
    def __init__(self, url, review_limit):
        super().__init__()
        self.url = url
        self.review_limit = review_limit

    def run(self):
        driver = self.setup_driver()
        try:
            logging.info(f"Scraping product: {self.url}")
            # We don't have meta info (name/price) beforehand, pass None
            # The base scraper will try to extract them from page
            details = self.scrape_product_details(driver, self.url, product_meta=None, review_limit=self.review_limit)
            
            # Generate filename
            name_slug = re.sub(r'[^a-z0-9_]+', '', details["product"]["name"].lower())[:50]
            pid = details["product"]["id"]
            filename = f"product_{name_slug}_{pid}.json"
            
            with open(filename, "w", encoding="utf-8") as f:
                json.dump([details], f, ensure_ascii=False, indent=2)
                
            logging.info(f"Saved product details to {filename}")
            
        except Exception as e:
            logging.error(f"Fatal error: {e}", exc_info=True)
        finally:
            self.teardown_driver(driver)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Scrape single Shopee product")
    parser.add_argument("--url", required=True, help="Product URL")
    parser.add_argument("--review-limit", type=int, default=10, help="Max reviews to scrape")
    args = parser.parse_args()
    
    scraper = SingleProductScraper(args.url, args.review_limit)
    scraper.run()
