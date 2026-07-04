import signal, sys, time, json, os
from modules.local_proxy import start_local_proxy
from modules.signup import do_signup
from modules.service_search import search_service
from modules.place_order import place_order
from modules.service_scraper import (
    scrape_services, calculate_affordable, save_services_data,
    load_affordable_services, print_affordable_table,
    get_service_by_id, calc_quantity_for_service, BALANCE
)
from modules.session_manager import (
    save_cookies, try_cookie_login, mark_account_used,
    pick_proxy, save_account_info, is_logged_in, ensure_dirs
)
from sites.site1 import create_driver
from proxies import PROXIES

running = True

def handle_sigint(sig, frame):
    global running
    print("\n[*] Stopping after current order...")
    running = False

signal.signal(signal.SIGINT, handle_sigint)

def get_user_input():
    link = input("\nEnter link (or 'q' to quit): ").strip()
    if link.lower() == 'q':
        return None, None
    quantity = input("Enter target member quantity: ").strip()
    try:
        quantity = int(quantity)
    except ValueError:
        print("[!] Invalid quantity")
        return None, None
    return link, quantity

def run_single_cycle(link, target_qty, last_proxy, affordable_services):
    proxy = pick_proxy(PROXIES, last_proxy)
    print(f"\n[*] Proxy: {proxy}")

    driver = create_driver(proxy=proxy)
    logged_in_user = None

    try:
        # Step 1: Try cookie login first
        print("[1] Trying cookie login...")
        logged_in_user = try_cookie_login(driver, PROXIES, proxy)

        if not logged_in_user:
            # Step 2: Fresh signup
            print("[1] Fresh signup...")
            creds = do_signup(driver, "https://smmpanel.one/signup")
            logged_in_user = creds["username"]
            save_cookies(driver, logged_in_user)
            save_account_info(creds, proxy)
            mark_account_used(logged_in_user)
            print(f"[+] Account: {logged_in_user}")

        if not is_logged_in(driver):
            print("[!] Login failed, retrying with fresh signup...")
            driver.quit()
            proxy = pick_proxy(PROXIES, proxy)
            driver = create_driver(proxy=proxy)
            creds = do_signup(driver, "https://smmpanel.one/signup")
            logged_in_user = creds["username"]
            save_cookies(driver, logged_in_user)
            save_account_info(creds, proxy)
            mark_account_used(logged_in_user)
            print(f"[+] Account: {logged_in_user}")

        # Step 3: Find best service for this quantity
        best = None
        for svc in affordable_services:
            qty = calc_quantity_for_service(svc, target_qty)
            if qty is not None:
                if qty >= target_qty:
                    best = svc
                    break
                if best is None or qty > calc_quantity_for_service(best, target_qty):
                    best = svc

        if not best:
            print("[!] No affordable service found for this quantity")
            return proxy

        actual_qty = calc_quantity_for_service(best, target_qty)
        cost = round(actual_qty * best["rate_per_unit"], 4)
        print(f"[2] Service #{best['id']}: {best['name'][:50]}")
        print(f"    Qty: {actual_qty} | Cost: ${cost} | Rate: ${best['rate_per_1000']}/1k")

        # Step 4: Search service
        search_service(driver, best["id"])

        # Step 5: Place order
        place_order(driver, link, str(actual_qty))
        time.sleep(2)

        # Check for error messages
        error = driver.execute_script("""
            var alerts = document.querySelectorAll('.alert-danger, .alert-warning, .swal2-popup');
            var texts = [];
            alerts.forEach(function(a) { texts.push(a.textContent.trim()); });
            return texts.join(' | ');
        """)
        if error:
            print(f"[!] Server response: {error[:200]}")
        else:
            print(f"[+] Order placed successfully")

        # Save cookies for reuse
        save_cookies(driver, logged_in_user)
        return proxy

    except Exception as e:
        print(f"[!] Error: {e}")
        return proxy
    finally:
        try:
            driver.quit()
        except:
            pass

def main():
    print("=" * 60)
    print("  Avisha - SMM Panel Order Automation")
    print("  Ctrl+C to stop")
    print("=" * 60)

    # Step 0: Load or scrape services
    affordable = load_affordable_services()
    if not affordable:
        print("\n[*] No cached services. Scraping from smmpanel.one...")
        proxy = pick_proxy(PROXIES, None)
        driver = create_driver(proxy=proxy)
        try:
            creds = do_signup(driver, "https://smmpanel.one/signup")
            save_cookies(driver, creds["username"])
            save_account_info(creds, proxy)
            mark_account_used(creds["username"])
            services = scrape_services(driver)
            affordable = calculate_affordable(services)
            save_services_data(services, affordable)
            print(f"[+] Scraped {len(services)} services, {len(affordable)} affordable")
        finally:
            driver.quit()
    else:
        print(f"[+] Loaded {len(affordable)} affordable services from cache")

    print_affordable_table(affordable)

    # Main loop
    last_proxy = None
    order_count = 0

    while running:
        link, target_qty = get_user_input()
        if link is None:
            break

        last_proxy = run_single_cycle(link, target_qty, last_proxy, affordable)
        order_count += 1
        print(f"\n--- Completed order #{order_count} ---")

    print(f"\n[*] Done. {order_count} orders placed.")

if __name__ == "__main__":
    main()
