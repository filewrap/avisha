import random,string
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def random_username():
    return ''.join(random.choices(string.ascii_lowercase + string.digits,k=9))
def random_email():
    return ''.join(random.choices(string.ascii_lowercase + string.digits,k=9))+"@gmail.com"
def random_password():
    return ''.join(random.choices(string.ascii_letters + string.digits,k=10))

def do_signup(driver,url):
    driver.get(url)
    wait=WebDriverWait(driver,20)
    password=random_password()
    wait.until(EC.presence_of_element_located((By.ID,"username"))).send_keys(random_username())
    driver.find_element(By.ID,"email").send_keys(random_email())
    driver.find_element(By.ID,"password").send_keys(password)
    driver.find_element(By.ID,"confirm").send_keys(password)
    toggle=wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR,"label[for='test1']")))
    driver.execute_script("arguments[0].click();",toggle)
    signup_btn=wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR,"button.fill-btn.fill-icon")))
    driver.execute_script("arguments[0].click();",signup_btn)
