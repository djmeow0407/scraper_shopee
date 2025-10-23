import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from tqdm import tqdm
import csv, time, random

options = uc.ChromeOptions()
options.add_argument("--disable-blink-features=AutomationControlled")
driver = uc.Chrome(options=options)

url = "https://banhang.shopee.vn/edu/category-guide/"
driver.get(url)

wait = WebDriverWait(driver, 20)

def scrape_current_page():
    rows = driver.find_elements(By.CSS_SELECTOR, "tr.shopee-table__row")
    data_list = []
    for row in rows:
        cols = row.find_elements(By.TAG_NAME, "td")
        if len(cols) < 7:
            continue
        def safe_text(col_idx):
            try:
                return cols[col_idx].text.strip()
            except:
                return ""
        record = {
            "nganh_cap_1": safe_text(0),
            "nganh_cap_2": safe_text(1),
            "nganh_cap_3": safe_text(2),
            "nganh_cap_4": safe_text(3),
            "nganh_cap_5": safe_text(4),
            "ma_nganh": safe_text(5),
            "mo_ta_vi_du": safe_text(6),
        }
        data_list.append(record)
    return data_list

wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "tr.shopee-table__row")))

all_data = []
page = 1
pbar = tqdm(desc="Collecting data", unit="page")

while True:
    pbar.set_description(f"Pages {page}")
    page_data = scrape_current_page()
    all_data.extend(page_data)
    pbar.update(1)

    if page % 5 == 0:
        with open("shopee_categories_temp.csv", "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=all_data[0].keys())
            writer.writeheader()
            writer.writerows(all_data)
        print(f"Saves {len(all_data)} rows.")
    try:
        next_btn = driver.find_element(By.CSS_SELECTOR, "button.shopee-pager__button-next")
        class_attr = next_btn.get_attribute("class")
        if not next_btn.is_enabled() or (class_attr and "disabled" in class_attr):
            print("End of pages. No more data to collect.")
            break

        driver.execute_script("arguments[0].scrollIntoView(true);", next_btn)
        time.sleep(0.5)
        next_btn.click()

        time.sleep(random.uniform(1.5, 3.0))
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "tr.shopee-table__row")))
        page += 1

    except Exception as e:
        print(f"No other pages or error: {e}")
        break

driver.quit()
pbar.close()

with open("shopee_categories.csv", "w", encoding="utf-8", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=all_data[0].keys())
    writer.writeheader()
    writer.writerows(all_data)

print(f"Complete! Saved {len(all_data)} rows.")
