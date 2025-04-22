import json
import os
import sys
from playwright.sync_api import sync_playwright, TimeoutError, Error
import time

# Configurable constants
LOGIN_URL = "https://hiring.idenhq.com/"
PRODUCTS_URL = "https://hiring.idenhq.com/challenge"
SESSION_FILE = "auth/session.json"
OUTPUT_FILE = "product_data.json"
USERNAME = "aditya.darak257@gmail.com"
PASSWORD = "snZK2u4b"

# Define a fixed timeout for waiting and retrying elements.
MAX_WAIT_TIME = 90000  # Max wait time in milliseconds (30 seconds)
RETRY_LIMIT = 3  # Number of retries before failure

def save_session(context):
    os.makedirs("auth", exist_ok=True)
    context.storage_state(path=SESSION_FILE)

def load_session(playwright):
    if os.path.exists(SESSION_FILE):
        browser = playwright.chromium.launch(headless=True)
        return browser.new_context(storage_state=SESSION_FILE)
    return None

def wait_for_element(page, selector, timeout=MAX_WAIT_TIME, retries=RETRY_LIMIT):
    """
    Waits for an element to appear up to a maximum wait time, with a limited retry mechanism.
    If the element does not appear, it will retry up to `retries` times with fixed delays.
    """
    attempt = 0
    while attempt < retries:
        try:
            page.wait_for_selector(selector, timeout=timeout)
            print(f"[INFO] Element {selector} found!")
            return True
        except TimeoutError:
            attempt += 1
            print(f"[WARNING] Retrying {selector} (attempt {attempt}/{retries})...")
            time.sleep(2)  # Delay between retries to avoid rapid retries
    print(f"[ERROR] Element {selector} not found after {retries} retries.")
    return False

def login_and_save_session(playwright):
    print("[INFO] Logging in and creating a new session...")
    browser = playwright.chromium.launch(headless=True)
    context = browser.new_context()
    page = context.new_page()
    try:
        page.goto(LOGIN_URL)
        if not wait_for_element(page, "input[name='Email']", timeout=MAX_WAIT_TIME):
            sys.exit(1)
        
        page.fill("input[name='Email']", USERNAME)
        page.fill("input[name='Password']", PASSWORD)
        page.click("button[type='submit']")
        page.wait_for_load_state("networkidle")
        save_session(context)
        print("[SUCCESS] Login and session saved.")
        return context
    except TimeoutError:
        print("[ERROR] Login page elements not found.")
        context.close()
        sys.exit(1)

def navigate_to_product_table(page):
    try:
        print("[INFO] Navigating to product table...")
        page.goto(PRODUCTS_URL)
        if not wait_for_element(page, "text=Inventory", timeout=MAX_WAIT_TIME):
            sys.exit(1)
        
        page.click("text=Inventory")
        if not wait_for_element(page, "text=Products", timeout=MAX_WAIT_TIME):
            sys.exit(1)

        page.click("text=Products")
        if not wait_for_element(page, "table#product-table", timeout=MAX_WAIT_TIME):
            sys.exit(1)
        print("[SUCCESS] Product table located.")
    except TimeoutError:
        print("[ERROR] Failed to reach the product table.")
        sys.exit(1)

def extract_table_data(page):
    print("[INFO] Extracting product data...")
    all_data = []
    try:
        while True:
            if not wait_for_element(page, "table#product-table tbody tr", timeout=MAX_WAIT_TIME):
                break

            rows = page.query_selector_all("table#product-table tbody tr")
            for row in rows:
                cells = row.query_selector_all("td")
                if len(cells) >= 4:
                    product = {
                        "ID": cells[0].inner_text().strip(),
                        "Product": cells[1].inner_text().strip(),
                        "Price": cells[2].inner_text().strip(),
                        "Stock": cells[3].inner_text().strip(),
                        "Color": cells[4].inner_text().strip(),
                        "Mass(kg)": cells[5].inner_text().strip(),
                        "Warranty": cells[6].inner_text().strip()
                    }
                    all_data.append(product)

            next_button = page.query_selector("button.next:not([disabled])")
            if next_button:
                next_button.click()
                page.wait_for_timeout(1000)
            else:
                break
    except Error as e:
        print(f"[ERROR] During data extraction: {e}")
    return all_data

def export_to_json(data):
    with open(OUTPUT_FILE, "w") as f:
        json.dump(data, f, indent=4)
    print(f"[SUCCESS] Data exported to {OUTPUT_FILE}")

def main():
    with sync_playwright() as playwright:
        try:
            context = load_session(playwright)
            if not context:
                context = login_and_save_session(playwright)

            page = context.new_page()
            navigate_to_product_table(page)
            data = extract_table_data(page)
            export_to_json(data)
        except Exception as e:
            print(f"[FATAL ERROR] {e}")
        finally:
            context.close()

if __name__ == "__main__":
    main()
