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

# Define a fixed timeout for waiting and retrying elements
MAX_WAIT_TIME = 30000  # Max wait time in milliseconds (30 seconds)
RETRY_LIMIT = 3  # Number of retries before failure

def save_session(context):
    os.makedirs("auth", exist_ok=True)
    context.storage_state(path=SESSION_FILE)

def load_session(playwright):
    if os.path.exists(SESSION_FILE):
        browser = playwright.chromium.launch(headless=False)
        return browser.new_context(storage_state=SESSION_FILE)
    return None

def wait_for_element(page, selector, timeout=MAX_WAIT_TIME, retries=RETRY_LIMIT):
    """
    Waits for an element to appear up to a maximum wait time, with a limited retry mechanism.
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
            time.sleep(2)
    print(f"[ERROR] Element {selector} not found after {retries} retries.")
    return False

def login_and_save_session(playwright):
    print("[INFO] Logging in and creating a new session...")
    browser = playwright.chromium.launch(headless=False)
    context = browser.new_context()
    page = context.new_page()
    try:
        page.goto(LOGIN_URL)
        page.wait_for_load_state("domcontentloaded")
        page.wait_for_load_state("networkidle")
        
        # Wait for email and password fields to be visible
        if wait_for_element(page, "input[type='email']") and wait_for_element(page, "input[type='password']"):
            # Fill login form
            page.fill("input[type='email']", USERNAME)
            page.fill("input[type='password']", PASSWORD)
            
            # Find and click submit button
            submit_selector = "button[type='submit']"
            if wait_for_element(page, submit_selector):
                page.click(submit_selector)
                
                # Wait for navigation after login
                print("[INFO] Waiting for navigation after login...")
                page.wait_for_timeout(5000)
                page.wait_for_load_state("networkidle")
                
                # Save session
                save_session(context)
                print("[SUCCESS] Login and session saved.")
                return context
            else:
                print("[ERROR] Submit button not found")
        else:
            print("[ERROR] Login form fields not found")
            
        context.close()
        sys.exit(1)
    except Exception as e:
        print(f"[ERROR] Exception during login: {e}")
        context.close()
        sys.exit(1)

def extract_table_data(page):
    print("[INFO] Attempting to extract product data...")
    all_data = []
    try:
        # Wait for the product table to load
        if not wait_for_element(page, "table", timeout=10000):
            print("[ERROR] Product table not found on the page")
            return all_data
        
        # Get table headers
        headers = page.query_selector_all("table th")
        header_texts = [header.inner_text().strip() for header in headers]
        print(f"[INFO] Table headers: {header_texts}")
        
        # Process table rows
        rows = page.query_selector_all("table tbody tr")
        print(f"[INFO] Found {len(rows)} rows in the table")
        
        for row in rows:
            cells = row.query_selector_all("td")
            if len(cells) >= 2:
                # Create a product dictionary based on headers
                product = {}
                for i, cell in enumerate(cells):
                    if i < len(header_texts):
                        header = header_texts[i]
                        product[header] = cell.inner_text().strip()
                
                all_data.append(product)
                
        print(f"[INFO] Extracted {len(all_data)} product records")
        if all_data:
            print("[INFO] Sample record:")
            print(json.dumps(all_data[0], indent=2))
            
    except Error as e:
        print(f"[ERROR] During data extraction: {e}")
    
    return all_data

def export_to_json(data):
    if not data:
        print("[WARNING] No data to export")
        return
        
    with open(OUTPUT_FILE, "w") as f:
        json.dump(data, f, indent=4)
    print(f"[SUCCESS] Data exported to {OUTPUT_FILE}")

def main():
    with sync_playwright() as playwright:
        context = None
        try:
            # Try to load existing session or login
            context = load_session(playwright)
            if not context:
                context = login_and_save_session(playwright)

            page = context.new_page()
            
            # Navigate directly to products URL
            print(f"[INFO] Navigating to {PRODUCTS_URL}")
            page.goto(PRODUCTS_URL)
            page.wait_for_load_state("domcontentloaded")
            page.wait_for_load_state("networkidle")
            
            # Extract data from the table
            data = extract_table_data(page)
            
            if data:
                export_to_json(data)
            else:
                print("[ERROR] No product data was extracted")
                
        except Exception as e:
            print(f"[FATAL ERROR] {e}")
            import traceback
            traceback.print_exc()
        finally:
            if context:
                context.close()

if __name__ == "__main__":
    main()