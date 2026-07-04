import random,string,time
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
    username=random_username()
    email=random_email()
    wait.until(EC.presence_of_element_located((By.ID,"username"))).send_keys(username)
    driver.find_element(By.ID,"email").send_keys(email)
    driver.find_element(By.ID,"password").send_keys(password)
    driver.find_element(By.ID,"confirm").send_keys(password)
    toggle=wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR,"label[for='test1']")))
    driver.execute_script("arguments[0].click();",toggle)
    # Bypass ALTCHA captcha: remove widget and submit form natively
    driver.execute_script("""
        var form = document.querySelector('form[action=""]');
        if (form) {
            var w = document.querySelector('altcha-widget');
            if (w) w.remove();
            var inp = document.createElement('input');
            inp.type = 'hidden';
            inp.name = 'altcha';
            inp.value = '';
            form.appendChild(inp);
            form.submit();
        }
    """)
    time.sleep(5)
    return {"username": username, "email": email, "password": password}
