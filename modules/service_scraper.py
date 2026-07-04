import json, os, time
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
ALL_SERVICES_FILE = os.path.join(DATA_DIR, "services_all.json")
AFFORDABLE_FILE = os.path.join(DATA_DIR, "services_affordable.json")

BALANCE = 0.01

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
                category: currentCategory,
                cat_id: row.getAttribute('data-filter-table-category-id') || ''
            });
        }
        return services;
    """)
    return services

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
            max_affordable = int(balance / rate_per_unit)
            if max_affordable > max_order:
                max_affordable = max_order
            if max_affordable >= min_order:
                affordable.append({
                    "id": svc["id"],
                    "name": svc["name"],
                    "category": svc["category"],
                    "rate_per_1000": rate_per_1000,
                    "rate_per_unit": round(rate_per_unit, 6),
                    "min_order": min_order,
                    "max_order": max_order,
                    "max_affordable_qty": max_affordable,
                    "max_cost": round(max_affordable * rate_per_unit, 6),
                    "avg_time": svc["avg_time"]
                })
        except:
            pass
    affordable.sort(key=lambda x: x["max_affordable_qty"], reverse=True)
    return affordable

def save_services_data(services, affordable):
    ensure_data_dir()
    with open(ALL_SERVICES_FILE, "w") as f:
        json.dump(services, f, indent=2)
    with open(AFFORDABLE_FILE, "w") as f:
        json.dump(affordable, f, indent=2)

def load_affordable_services():
    if not os.path.exists(AFFORDABLE_FILE):
        return None
    with open(AFFORDABLE_FILE) as f:
        return json.load(f)

def print_affordable_table(affordable):
    print(f"\n{'#':>6} | {'Service':50s} | {'$/1k':>8} | {'Qty':>7} | {'Cost':>8} | Category")
    print("-" * 110)
    for i, s in enumerate(affordable):
        name = s["name"][:50]
        print(f"{s['id']:>6} | {name:50s} | ${s['rate_per_1000']:>6.3f} | {s['max_affordable_qty']:>7} | ${s['max_cost']:.4f} | {s['category']}")

def get_service_by_id(affordable, service_id):
    for s in affordable:
        if str(s["id"]) == str(service_id):
            return s
    return None

def calc_quantity_for_service(service, target_members):
    if target_members < service["min_order"]:
        return None
    cost = target_members * service["rate_per_unit"]
    if cost > BALANCE:
        max_by_balance = int(BALANCE / service["rate_per_unit"])
        max_by_balance = min(max_by_balance, service["max_order"])
        if max_by_balance < service["min_order"]:
            return None
        return max_by_balance
    return target_members
