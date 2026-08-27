from playwright.sync_api import sync_playwright
import urllib.parse

query = 'closer'
with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    page.goto(f'https://open.spotify.com/search/{urllib.parse.quote(query)}/tracks', timeout=15000)
    page.wait_for_selector('a[href^="/track/"]', timeout=10000)
    href = page.locator('a[href^="/track/"]').first.get_attribute('href')
    print('FOUND:', href)
    browser.close()
