from selenium import webdriver
from modules.signup import do_signup
from modules.service_search import search_service
from modules.place_order import place_order

def run_site1():
    print("[1] Starting automation")
    link = input("Enter link: ")
    quantity = input("Enter quantity: ")
    driver = webdriver.Chrome()
    try:
        do_signup(driver, "https://smmpanel.one/signup")
        search_service(driver, "85")
        place_order(driver, link, quantity)
        input("Press Enter to close...")
    finally:
        driver.quit()
