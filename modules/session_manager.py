import json, os, time, random
from selenium.webdriver.common.by import By

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
COOKIES_DIR = os.path.join(DATA_DIR, "cookies")
USED_ACCOUNTS_FILE = os.path.join(DATA_DIR, "used_accounts.json")

def ensure_dirs():
    os.makedirs(COOKIES_DIR, exist_ok=True)

def save_cookies(driver, account_name):
    ensure_dirs()
    path = os.path.join(COOKIES_DIR, f"{account_name}.json")
    cookies = driver.get_cookies()
    with open(path, "w") as f:
        json.dump(cookies, f, indent=2)

def load_cookies(driver, account_name):
    ensure_dirs()
    path = os.path.join(COOKIES_DIR, f"{account_name}.json")
    if not os.path.exists(path):
        return False
    with open(path) as f:
        cookies = json.load(f)
    driver.get("https://smmpanel.one")
    time.sleep(1)
    for cookie in cookies:
        try:
            driver.add_cookie(cookie)
        except:
            pass
    driver.refresh()
    time.sleep(3)
    return True

def is_logged_in(driver):
    url = driver.current_url
    return "signup" not in url and "signin" not in url

def mark_account_used(username):
    used = load_used_accounts()
    used.append({"username": username, "time": time.time()})
    ensure_dirs()
    with open(USED_ACCOUNTS_FILE, "w") as f:
        json.dump(used, f, indent=2)

def load_used_accounts():
    if not os.path.exists(USED_ACCOUNTS_FILE):
        return []
    with open(USED_ACCOUNTS_FILE) as f:
        return json.load(f)

def get_used_usernames():
    used = load_used_accounts()
    return {a["username"] for a in used}

def pick_proxy(proxies, last_proxy=None):
    available = [p for p in proxies if p != last_proxy]
    if not available:
        available = proxies
    return random.choice(available)

def save_account_info(creds, proxy):
    from modules.accounts import save_account
    save_account(creds["username"], creds["email"], creds["password"], proxy)

def try_cookie_login(driver, proxies, last_proxy=None):
    ensure_dirs()
    used_usernames = get_used_usernames()
    cookie_files = [f for f in os.listdir(COOKIES_DIR) if f.endswith(".json")]

    for cf in cookie_files:
        account_name = cf.replace(".json", "")
        if account_name in used_usernames:
            continue
        if load_cookies(driver, account_name):
            if is_logged_in(driver):
                print(f"[cookie] Logged in as {account_name}")
                return account_name
    return None
