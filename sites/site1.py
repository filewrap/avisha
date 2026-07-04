import random
from urllib.parse import urlparse
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from modules.signup import do_signup
from modules.service_search import search_service
from modules.place_order import place_order
from modules.accounts import save_account
from modules.local_proxy import start_local_proxy
from proxies import PROXIES

def parse_proxy(proxy_url):
    p = urlparse(proxy_url)
    return p.hostname, p.port, p.username, p.password

def create_driver(headless=True, proxy=None):
    opts = Options()
    if headless:
        opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--window-size=1920,1080")
    opts._proxy_server = None
    if proxy:
        host, port, user, pw = parse_proxy(proxy)
        srv, local_port = start_local_proxy(host, port, user, pw)
        opts.add_argument(f"--proxy-server=socks5://127.0.0.1:{local_port}")
        opts._proxy_server = srv
    opts.binary_location = "/usr/bin/chromium-browser"
    return webdriver.Chrome(options=opts)

def run_site1(link=None, quantity=None, service_id="85", proxy=None):
    if link is None:
        link = input("Enter link: ")
    if quantity is None:
        quantity = input("Enter quantity: ")

    if not proxy:
        proxy = random.choice(PROXIES)
    print(f"[*] Using proxy: {proxy}")

    driver = create_driver(proxy=proxy)
    try:
        print("[1] Signing up...")
        creds = do_signup(driver, "https://smmpanel.one/signup")
        save_account(creds["username"], creds["email"], creds["password"], proxy)
        print(f"[+] Account saved: {creds['username']} / {creds['email']}")

        print(f"[2] Searching service {service_id}...")
        search_service(driver, service_id)

        print(f"[3] Placing order: {link} x{quantity}...")
        place_order(driver, link, quantity)
        print("[+] Order placed")

        input("Press Enter to close...")
    finally:
        driver.quit()
        if hasattr(driver.options, "_proxy_server") and driver.options._proxy_server:
            driver.options._proxy_server.close()
