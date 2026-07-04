import signal, sys, time, os
from modules.local_proxy import start_local_proxy
from modules.signup import do_signup
from modules.service_search import search_service
from modules.place_order import place_order
from modules.service_scraper import (
    scrape_services, filter_telegram, calculate_affordable, save_all,
    load_telegram, get_service_by_id, calc_qty, BALANCE,
    TELEGRAM_SERVICES_FILE,
)
from modules.session_manager import (
    save_cookies, try_cookie_login, mark_account_used,
    pick_proxy, save_account_info, is_logged_in,
)
from sites.site1 import create_driver
from proxies import PROXIES

running = True


def sigint(sig, frame):
    global running
    print("\n[!] Ctrl+C — stopping after current order...")
    running = False


signal.signal(signal.SIGINT, sigint)


def log(msg):
    ts = time.strftime("%H:%M:%S")
    print(f"[{ts}] {msg}")


def refresh_services():
    log("Refreshing services from smmpanel.one...")
    proxy = pick_proxy(PROXIES, None)
    driver = create_driver(proxy=proxy)
    try:
        creds = do_signup(driver, "https://smmpanel.one/signup")
        save_cookies(driver, creds["username"])
        save_account_info(creds, proxy)
        mark_account_used(creds["username"])
        log(f"Scraping as {creds['username']}...")
        all_services = scrape_services(driver)
        tg = filter_telegram(all_services)
        affordable = calculate_affordable(tg)
        save_all(all_services, affordable)
        log(f"Done: {len(all_services)} total, {len(tg)} telegram, {len(affordable)} affordable")
        return affordable
    finally:
        driver.quit()


def pick_best_service(affordable, target_qty):
    for svc in affordable:
        q = calc_qty(svc, target_qty)
        if q is not None and q >= target_qty:
            return svc, q
    best = None
    best_q = 0
    for svc in affordable:
        q = calc_qty(svc, target_qty)
        if q is not None and q > best_q:
            best = svc
            best_q = q
    if best is not None:
        return best, best_q
    return None, None


def do_order(link, target_qty, affordable, last_proxy):
    proxy = pick_proxy(PROXIES, last_proxy)
    log(f"Proxy: {proxy}")

    driver = create_driver(proxy=proxy)
    try:
        user = try_cookie_login(driver, PROXIES, proxy)
        if not user:
            log("Fresh signup...")
            creds = do_signup(driver, "https://smmpanel.one/signup")
            user = creds["username"]
            save_cookies(driver, user)
            save_account_info(creds, proxy)
            mark_account_used(user)
            log(f"Account: {user}")

        if not is_logged_in(driver):
            log("Login failed, retrying fresh signup...")
            driver.quit()
            proxy = pick_proxy(PROXIES, proxy)
            driver = create_driver(proxy=proxy)
            creds = do_signup(driver, "https://smmpanel.one/signup")
            user = creds["username"]
            save_cookies(driver, user)
            save_account_info(creds, proxy)
            mark_account_used(user)
            log(f"Account: {user}")

        svc, qty = pick_best_service(affordable, target_qty)
        if not svc:
            log("No affordable service found")
            return proxy, False

        cost = round(qty * svc["rate_per_unit"], 4)
        log(f"Service #{svc['id']} | {svc['name'][:50]}")
        log(f"  Qty: {qty} | Cost: ${cost} | Rate: ${svc['rate_per_1000']}/1k")

        search_service(driver, svc["id"])
        place_order(driver, link, str(qty))
        time.sleep(2)

        error = driver.execute_script("""
            var a = document.querySelectorAll('.alert-danger, .alert-warning, .swal2-popup');
            var t = [];
            a.forEach(function(e) { t.push(e.textContent.trim()); });
            return t.join(' | ');
        """)
        if error:
            log(f"Server: {error[:200]}")
            return proxy, False
        else:
            log("Order placed!")
            save_cookies(driver, user)
            return proxy, True

    except Exception as e:
        log(f"Error: {e}")
        return proxy, False
    finally:
        try:
            driver.quit()
        except Exception:
            pass


def main():
    print("=" * 60)
    print("  Avisha - Telegram Order Automation")
    print("  Ctrl+C to stop")
    print("=" * 60)

    affordable = load_telegram()
    if not affordable:
        affordable = refresh_services()
    else:
        log(f"Loaded {len(affordable)} telegram services from cache")

    print()
    print(f"  Telegram services (affordable within ${BALANCE}):")
    print(f"  {'ID':>5}  {'Service':42s}  {'$/1k':>7}  {'Qty':>5}  {'Cost':>8}")
    print("  " + "-" * 75)
    for s in affordable[:30]:
        print(f"  {s['id']:>5}  {s['name'][:42]:42s}  ${s['rate_per_1000']:>5.3f}  {s['max_qty']:>5}  ${s['cost']:.4f}")
    if len(affordable) > 30:
        print(f"  ... and {len(affordable) - 30} more (see {TELEGRAM_SERVICES_FILE})")

    print()
    link = input("Channel/Group link: ").strip()
    if not link:
        print("No link provided, exiting.")
        return

    qty_str = input("Target member quantity: ").strip()
    try:
        target_qty = int(qty_str)
    except ValueError:
        print("Invalid quantity.")
        return

    log(f"Link: {link}")
    log(f"Target: {target_qty} members")

    last_proxy = None
    order_count = 0

    while running:
        log(f"--- Order #{order_count + 1} ---")
        last_proxy, ok = do_order(link, target_qty, affordable, last_proxy)
        if ok:
            order_count += 1
        log(f"Total orders placed: {order_count}")

        if not running:
            break

        print()
        choice = input("[enter] next order  |  [a] autopilot (10 more)  |  [r] refresh prices  |  [q] quit: ").strip().lower()
        if choice == "q":
            break
        elif choice == "r":
            affordable = refresh_services()
            print()
            print(f"  Refreshed: {len(affordable)} affordable telegram services")
            print(f"  {'ID':>5}  {'Service':42s}  {'$/1k':>7}  {'Qty':>5}  {'Cost':>8}")
            print("  " + "-" * 75)
            for s in affordable[:20]:
                print(f"  {s['id']:>5}  {s['name'][:42]:42s}  ${s['rate_per_1000']:>5.3f}  {s['max_qty']:>5}  ${s['cost']:.4f}")
        elif choice == "a":
            autopilot_count = 10
            log(f"Autopilot: {autopilot_count} orders...")
            for i in range(autopilot_count):
                if not running:
                    break
                log(f"Autopilot order {i+1}/{autopilot_count}")
                last_proxy, ok = do_order(link, target_qty, affordable, last_proxy)
                if ok:
                    order_count += 1
                log(f"Total: {order_count}")
            log("Autopilot finished")

    log(f"Done. {order_count} orders placed.")


if __name__ == "__main__":
    main()
