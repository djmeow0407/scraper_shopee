import sys
import time
import json
import logging
import re
import os
import traceback
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from tqdm import tqdm

class BaseShopeeScraper:
    def __init__(self):
        self._setup_logging()

    def _setup_logging(self):
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s [%(levelname)s] %(message)s",
            handlers=[logging.StreamHandler(sys.stdout)]
        )

    def _wait_for_captcha(self, driver):
        blacklist = ["captcha", "/buyer/login", "/user/login", "/account/login", "/verify", "security"]
        while any(x in driver.current_url.lower() for x in blacklist):
            logging.info("Captcha detected. Please solve and press Enter in terminal...")
            print("!!! ACTION REQUIRED: Focus browser, solve captcha, then press Enter here !!!")
            input()
            time.sleep(3)
            if not any(x in driver.current_url.lower() for x in blacklist):
                logging.info("Captcha cleared. Resuming...")
                driver.refresh()
                time.sleep(3)
            else:
                logging.warning("Captcha still detected. Waiting 5s...")
                time.sleep(5)

    def _parse_price(self, price_text):
        raw = price_text.strip()
        cleaned = re.sub(r'[^\d]', '', raw)
        try: val = int(cleaned)
        except: val = 0
        return {"value": val, "currency": "VND", "raw": raw}

    def _parse_weight(self, weight_str):
        match = re.search(r'(\d+)\s*([a-zA-Z]+)', weight_str)
        if match: return {"value": int(match.group(1)), "unit": match.group(2)}
        return {"value": 0, "unit": ""}

    def _parse_description(self, raw_text):
        data = {
            "summary": "", "manufacturer": "", "hashtags": [],
            "raw_text": raw_text, "category_list": [], "specs": {}
        }
        if not raw_text: return data
        
        lines = [l.strip() for l in raw_text.split('\n') if l.strip()]
        specs_buffer, desc_buffer = [], []
        mode = "desc"
        
        for line in lines:
            if "CHI TIẾT SẢN PHẨM" in line.upper(): mode = "specs"; continue
            elif "MÔ TẢ SẢN PHẨM" in line.upper(): mode = "desc"; continue
            if mode == "specs": specs_buffer.append(line)
            else: desc_buffer.append(line)

        # Parse Specs
        common_keys = ["Danh Mục", "Thương hiệu", "Trọng lượng", "Xuất xứ", "Hạn sử dụng", "Gửi từ", "Kho", "Loại thực phẩm", "Thể tích", "Kích cỡ"]
        current_key = None
        for item in specs_buffer:
            if item in common_keys:
                current_key = item
                data["specs"][current_key] = ""
            elif current_key:
                val = data["specs"][current_key]
                val = f"{val} > {item}" if val else item
                data["specs"][current_key] = val
        
        # Category
        if "Danh Mục" in data["specs"]:
            data["category_list"] = data["specs"]["Danh Mục"].split(" > ")

        # Desc analysis
        full_desc = "\n".join(desc_buffer)
        data["hashtags"] = re.findall(r'#\w+', full_desc)
        
        manuf_match = re.search(r'(công ty|cty)\s+.*?(bảo minh|.*?)\n', full_desc, re.IGNORECASE)
        if manuf_match: data["manufacturer"] = manuf_match.group(0).strip()
            
        summary = full_desc.split('\n')[0]
        if len(summary) < 20 and len(desc_buffer) > 1:
            summary = desc_buffer[0] + ". " + desc_buffer[1]
        data["summary"] = summary[:200] + "..." if len(summary) > 200 else summary
        
        return data

    def _get_reviews(self, driver, max_reviews):
        data = []
        driver.implicitly_wait(2)
        try:
            try:
                anchor = driver.find_element(By.XPATH, "//div[contains(text(), 'ĐÁNH GIÁ SẢN PHẨM')]")
                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", anchor)
                time.sleep(2)
            except:
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight * 0.9);")
                time.sleep(2)
                
            container = None
            for _ in range(5):
                try: 
                    c = driver.find_element(By.CLASS_NAME, "shopee-product-comment-list")
                    if c.is_displayed(): container = c; break
                except: pass
                if "chưa có đánh giá" in driver.page_source: return []
                if not container:
                    try:
                        c = driver.find_element(By.CSS_SELECTOR, "div.product-ratings")
                        if c.is_displayed(): container = c; break
                    except: pass
                time.sleep(1)
            
            if not container: return []
        except: return []

        logging.info(f"Collecting up to {max_reviews} reviews...")
        with tqdm(total=max_reviews, desc="Reviews", leave=True) as pbar:
            while len(data) < max_reviews:
                try:
                    current_class = container.get_attribute("class")
                    if "comment-list" not in current_class and "ratings__list" not in current_class:
                        try: container = container.find_element(By.CLASS_NAME, "shopee-product-comment-list")
                        except: pass
                    
                    items = container.find_elements(By.XPATH, "./div")
                    valid_items = [i for i in items if i.size['height'] > 20 and i.text.strip()]
                    if not valid_items: valid_items = container.find_elements(By.CSS_SELECTOR, ".shopee-product-rating")
                except: break
                
                for item in valid_items:
                    if len(data) >= max_reviews: break
                    try:
                        full_text = item.text
                        lines = [l.strip() for l in full_text.split('\n') if l.strip()]
                        
                        review = {
                            "username": "", "rating": 5, "review_time": "",
                            "attributes": {}, "content": "",
                            "seller_response": {"content": "", "responded": False},
                            "helpful_votes": 0
                        }
                        
                        try: review["username"] = item.find_element(By.CSS_SELECTOR, "a[href*='/shop/']").text.strip()
                        except: pass
                        if not review["username"] and lines: review["username"] = lines[0]

                        try: review["rating"] = len(item.find_elements(By.CSS_SELECTOR, "svg.icon-rating-solid"))
                        except: pass
                        
                        match = re.search(r'\d{4}-\d{2}-\d{2}\s\d{2}:\d{2}', full_text)
                        if match: review["review_time"] = match.group(0).replace(' ', 'T') + ":00"

                        marker = "phản hồi của Người Bán"
                        if re.search(marker, full_text, re.IGNORECASE):
                            review["seller_response"]["responded"] = True
                            parts = re.split(marker, full_text, flags=re.IGNORECASE)
                            if len(parts) > 1:
                                resp = parts[1].strip()
                                resp = re.sub(r'\n?\d+$', '', resp)
                                for trash in ["hữu ích?", "báo cáo", "like_count"]:
                                    resp = resp.split(trash)[0]
                                review["seller_response"]["content"] = resp.strip()

                        if full_text.strip().endswith("1") and lines[-1].isdigit():
                             review["helpful_votes"] = int(lines[-1])
                        
                        temp = full_text
                        if review["username"]: temp = temp.replace(review["username"], "")
                        if review.get("review_time"): temp = temp.replace(match.group(0), "")
                        if review["seller_response"]["content"]: temp = temp.replace(review["seller_response"]["content"], "")
                        temp = re.sub(marker, "", temp, flags=re.IGNORECASE)
                        
                        content_lines = []
                        attr_keys = ["Hương vị:", "Bao bì/Mẫu mã:", "Chất lượng sản phẩm:", "Tính năng nổi bật:", "Đúng với mô tả:", "Variation:", "Phân loại hàng:"]
                        for line in temp.split('\n'):
                            line = line.strip()
                            if not line: continue
                            is_attr = False
                            for k in attr_keys:
                                if line.startswith(k):
                                    val = line.replace(k, "").strip()
                                    clean_k = k.replace(":", "").replace(" ", "_").lower()
                                    review["attributes"][clean_k] = val
                                    is_attr = True
                                    break
                            if is_attr: continue
                            if re.match(r'^\d+$', line): continue
                            content_lines.append(line)
                        review["content"] = "\n".join(content_lines).strip()
                        
                        data.append(review)
                        pbar.update(1)
                    except: continue

                if len(data) < max_reviews:
                    try:
                        btn = driver.find_element(By.CSS_SELECTOR, "button.shopee-icon-button--right")
                        if btn.is_enabled(): btn.click(); time.sleep(2)
                        else: break
                    except: break
        
        logging.info(f"Collected {len(data)} reviews.")
        return data

    def scrape_product_details(self, driver, url, product_meta=None, review_limit=10, shop_header="Unknown"):
        driver.get(url)
        time.sleep(3)
        self._wait_for_captcha(driver)
        
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight * 0.3);")
        time.sleep(1)
        try:
            desc_anchor = driver.find_element(By.XPATH, "//div[contains(text(), 'MÔ TẢ SẢN PHẨM')]")
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", desc_anchor)
        except:
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight * 0.6);")
        time.sleep(2)
        
        # Meta aggregation
        meta = product_meta or {}
        name = meta.get("name", "Unknown")
        price = meta.get("price", "0")
        image = meta.get("img", "")
        
        if name == "Unknown":
            try: name = driver.find_element(By.CSS_SELECTOR, "._44qnta span").text
            except: 
                 try: name = driver.find_element(By.XPATH, "//div[contains(@class, 'product-brief-name')]").text
                 except: pass

        if price == "0":
             try: price = driver.find_element(By.CSS_SELECTOR, ".pqTWkA").text
             except: pass

        # Description
        desc_text = ""
        try:
            container = driver.find_element(By.XPATH, "//div[div[contains(text(), 'MÔ TẢ SẢN PHẨM')]]")
            desc_text = container.text
        except:
            try: desc_text = driver.find_element(By.XPATH, '//div[contains(@class, "product-detail")]').text
            except: pass
            
        parsed_desc = self._parse_description(desc_text)
        
        # ID
        pid = "0_0"
        match = re.search(r'i\.(\d+)\.(\d+)', url)
        if match: pid = f"{match.group(1)}_{match.group(2)}"
        
        specs = parsed_desc["specs"]
        
        obj = {
            "product": {
                "id": pid,
                "url": url,
                "name": name,
                "price": self._parse_price(price),
                "image": image,
                "stock_status": specs.get("Kho", "Unknown"),
                "category": parsed_desc.get("category_list", []),
                "brand": specs.get("Thương hiệu", "No Brand"),
                "weight": self._parse_weight(specs.get("Trọng lượng", "")),
                "origin": specs.get("Xuất xứ", "Unknown"),
                "shelf_life_months": int(re.search(r'\d+', specs.get("Hạn sử dụng", "0")).group(0)) if re.search(r'\d+', specs.get("Hạn sử dụng", "")) else 0,
                "ship_from": specs.get("Gửi từ", "Unknown")
            },
            "description": {
                "summary": parsed_desc["summary"],
                "manufacturer": parsed_desc["manufacturer"],
                "hashtags": parsed_desc["hashtags"],
                "raw_text": parsed_desc["raw_text"]
            },
            "reviews": self._get_reviews(driver, review_limit),
            "shop": {
                "name": shop_header,
                "url": "",
                "platform": "Shopee"
            },
            "meta": {
                "scraped_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
                "source": "Shopee",
                "language": "vi"
            }
        }
        return obj

    def setup_driver(self):
        options = uc.ChromeOptions()
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--start-maximized")

        logging.getLogger('undetected_chromedriver').setLevel(logging.CRITICAL)

        driver = uc.Chrome(
            options=options,
            version_main=144  # 🔥 QUAN TRỌNG: khớp Chrome 144 của bạn
        )

        driver.set_page_load_timeout(30)
        return driver
    def teardown_driver(self, driver):
        """Robust driver cleanup to prevent WinError 6"""
        try:
            driver.service.process.kill()
        except: pass
        try:
            driver.quit()
        except: pass
        
        # Monkey patch quit to silence __del__ error
        driver.quit = lambda: None
