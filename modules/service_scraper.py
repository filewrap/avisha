import json, os, time
from selenium.webdriver.common.by import By

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
ALL_SERVICES_FILE = os.path.join(DATA_DIR, "services_all.json")
TELEGRAM_SERVICES_FILE = os.path.join(DATA_DIR, "telegram_services.txt")
TELEGRAM_JSON_FILE = os.path.join(DATA_DIR, "telegram_services.json")

BALANCE = 0.01
TELEGRAM_KEYWORDS = ["telegram", "tg"]
RELEVANT_KEYWORDS = ["member", "bot start", "join"]


def ensure_data_dir():
    os.makedirs(DATA_DIR, exist_ok=True)


def scrape_services(driver):
    driver.get("https://smmpanel.one/services")
    time.sleep(3)
    services = driver.execute_script("""
        var rows = document.querySelectorAll('#service-table tbody tr');
        var services = [];
        var currentCategory = '';
        for (var i = 0; i < rows.length; i++) {
            var row = rows[i];
            var cells = row.querySelectorAll('td');
            if (cells.length === 1) {
                currentCategory = cells[0].textContent.trim();
                continue;
            }
            var sid = row.querySelector('td[data-filter-table-service-id]');
            if (!sid) continue;
            var nameEl = row.querySelector('td[data-td-service-id]');
            var tdTexts = Array.from(cells).map(function(c){ return c.textContent.trim(); });
            services.push({
                id: sid.getAttribute('data-filter-table-service-id'),
                name: nameEl ? nameEl.textContent.trim() : '',
                rate_per_1000: tdTexts[3] || '',
                min_order: tdTexts[4] || '',
                max_order: tdTexts[5] || '',
                avg_time: tdTexts[6] || '',
                category: currentCategory
            });
        }
        return services;
    """)
    return services


def filter_telegram(services):
    filtered = []
    for svc in services:
        name_lower = svc["name"].lower()
        cat_lower = svc.get("category", "").lower()
        is_telegram = any(kw in name_lower or kw in cat_lower for kw in TELEGRAM_KEYWORDS)
        if not is_telegram:
            continue
        is_relevant = any(kw in name_lower for kw in RELEVANT_KEYWORDS)
        if not is_relevant:
            continue
        filtered.append(svc)
    return filtered


def calculate_affordable(services, balance=BALANCE):
    affordable = []
    for svc in services:
        try:
            rate_str = svc["rate_per_1000"].replace("$", "").replace(",", "").replace("\xa0", "").strip()
            rate_per_1000 = float(rate_str)
            min_order = int(svc["min_order"].replace(",", "").replace("\xa0", "").strip())
            max_order = int(svc["max_order"].replace(",", "").replace("\xa0", "").strip())
            if rate_per_1000 <= 0:
                continue
            rate_per_unit = rate_per_1000 / 1000
            max_qty = int(balance / rate_per_unit)
            if max_qty > max_order:
                max_qty = max_order
            if max_qty < min_order:
                continue
            cost = round(max_qty * rate_per_unit, 6)
            affordable.append({
                "id": svc["id"],
                "name": svc["name"],
                "category": svc["category"],
                "rate_per_1000": rate_per_1000,
                "rate_per_unit": rate_per_unit,
                "min_order": min_order,
                "max_order": max_order,
                "max_qty": max_qty,
                "cost": cost,
                "avg_time": svc["avg_time"],
            })
        except Exception:
            pass
    affordable.sort(key=lambda x: x["max_qty"], reverse=True)
    return affordable


def save_all(services, affordable):
    ensure_data_dir()
    with open(ALL_SERVICES_FILE, "w") as f:
        json.dump(services, f, indent=2)
    with open(TELEGRAM_JSON_FILE, "w") as f:
        json.dump(affordable, f, indent=2)
    _write_txt(affordable)


def _write_txt(affordable):
    lines = []
    lines.append(f"{'ID':>5}  {'Service':52s}  {'$/1k':>7}  {'Qty':>5}  {'Cost':>8}  {'Min':>5}  {'Max':>7}  {'Time':>12}")
    lines.append("-" * 120)
    for s in affordable:
        lines.append(
            f"{s['id']:>5}  {s['name'][:52]:52s}  ${s['rate_per_1000']:>5.3f}  {s['max_qty']:>5}  ${s['cost']:.4f}  {s['min_order']:>5}  {s['max_order']:>7}  {s['avg_time']:>12}"
        )
    with open(TELEGRAM_SERVICES_FILE, "w") as f:
        f.write("\n".join(lines) + "\n")


def load_telegram():
    if not os.path.exists(TELEGRAM_JSON_FILE):
        return None
    with open(TELEGRAM_JSON_FILE) as f:
        return json.load(f)


def get_service_by_id(affordable, service_id):
    for s in affordable:
        if str(s["id"]) == str(service_id):
            return s
    return None


def calc_qty(service, target):
    if target < service["min_order"]:
        return None
    cost = target * service["rate_per_unit"]
    if cost > BALANCE:
        max_by_balance = int(BALANCE / service["rate_per_unit"])
        max_by_balance = min(max_by_balance, service["max_order"])
        if max_by_balance < service["min_order"]:
            return None
        return max_by_balance
    return target
