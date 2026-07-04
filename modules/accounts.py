import json, os

ACCOUNTS_FILE = os.path.join(os.path.dirname(__file__), "accounts.json")

def save_account(username, email, password, proxy=None):
    accounts = load_accounts()
    accounts.append({
        "username": username,
        "email": email,
        "password": password,
        "proxy": proxy,
    })
    with open(ACCOUNTS_FILE, "w") as f:
        json.dump(accounts, f, indent=2)

def load_accounts():
    if not os.path.exists(ACCOUNTS_FILE):
        return []
    with open(ACCOUNTS_FILE) as f:
        return json.load(f)
