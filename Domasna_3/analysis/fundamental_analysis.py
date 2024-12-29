from playwright.sync_api import sync_playwright

def scraping():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto("https://seinet.com.mk")
        try:
            page.wait_for_selector('#root > nav > div.header-panel-container.w-100 > div > ul > div > button',
                                   state="visible", timeout=60000)
            page.click('#root > nav > div.header-panel-container.w-100 > div > ul > div > button')
            print("Dropdown menu clicked.")
        except Exception as e:
            print(f"Failed to click the dropdown menu: {e}")

            # Wait for the English language option to appear and click it
        try:
            page.wait_for_selector('[data-key="en-GB"]', state="visible", timeout=60000)
            page.click('[data-key="en-GB"]')
            print("Switched to English successfully.")
        except Exception as e:
            print(f"Failed to switch to English: {e}")
        page.click('[data-key="en-GB"]')
        page.wait_for_selector("#formIssuerId")
        options = page.query_selector_all("#formIssuerId option")
        issuers = {option.get_attribute("value"): option.text_content().strip() for option in options if
                   option.get_attribute("value")}
        print(issuers)
        browser.close()
        return issuers

