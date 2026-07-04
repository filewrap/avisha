from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time

def place_order(driver,link,quantity):
    wait=WebDriverWait(driver,20)
    time.sleep(4)
    wait.until(EC.presence_of_element_located((By.ID,"field-orderform-fields-link"))).send_keys(link)
    qty=wait.until(EC.presence_of_element_located((By.ID,"field-orderform-fields-quantity")))
    qty.clear()
    qty.send_keys(str(quantity))
    submit_btn=wait.until(EC.element_to_be_clickable((By.XPATH,"//button[@type='submit']")))
    driver.execute_script("arguments[0].click();",submit_btn)
