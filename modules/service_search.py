from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time

def search_service(driver,service_id="85"):
    wait=WebDriverWait(driver,20)
    search_input=wait.until(EC.presence_of_element_located((By.ID,"input_service")))
    search_input.clear()
    search_input.send_keys(service_id)
    search_btn=wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR,"button.search")))
    driver.execute_script("arguments[0].click();",search_btn)
    time.sleep(4)
