from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time

# Path to your ChromeDriver
chrome_driver_path = "D:\Python Programs\Seo Automation\chromedriver.exe"

# Set up Selenium options
options = Options()
# options.add_argument("--headless")  # Uncomment to run in headless mode
options.add_argument("--disable-gpu")

# Initialize WebDriver
service = Service(chrome_driver_path)
driver = webdriver.Chrome(service=service, options=options)

try:
    success = False  # Variable to track success
    attempt = 0  # Counter for retries

    while not success:
        attempt += 1
        print(f"Attempt #{attempt}")

        # Open the registration page
        driver.get("https://iamsaigex.drv.pro/cadastrar")

        # Fill in the form fields
        try:
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.ID, "usu_nome"))
            )
            driver.find_element(By.ID, "usu_nome").send_keys("Nafseer CK")
            driver.find_element(By.ID, "usu_email").send_keys(f"nafseer.ceekey@gmail.com")  # Change email for each attempt
            driver.find_element(By.ID, "usu_telefone").send_keys("+91568156107")
            driver.find_element(By.ID, "usu_senha").send_keys("Nafseer@123")

            # Click the agree checkbox
            agree_checkbox = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.CLASS_NAME, "form-check-input"))
            )
            agree_checkbox.click()

            # Locate and click the submit button
            submit_button = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.NAME, "btn"))
            )
            submit_button.click()

            # Wait for the page to process
            time.sleep(5)

            # Check if the page URL has changed
            current_url = driver.current_url
            print("Current URL:", current_url)

            if current_url != "https://iamsaigex.drv.pro/cadastrar":  # Success condition: URL has changed
                print("Registration succeeded!")
                success = True
            else:
                print("Registration failed. Retrying...")

        except Exception as e:
            print(f"An error occurred on attempt #{attempt}: {e}")

except Exception as e:
    print(f"Critical error occurred: {e}")

finally:
    if success:
        print("Process completed successfully.")
    else:
        print("Failed to register after multiple attempts.")
    # Quit the browser only after success or termination
    driver.quit()
