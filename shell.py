from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import WebDriverException, TimeoutException, NoSuchElementException
from concurrent.futures import ThreadPoolExecutor
import time


def check_file_management_interface(url, driver_path):
    """
    Check if the URL has a file upload and management interface.
    """
    service = Service(driver_path)
    options = webdriver.ChromeOptions()
    # options.add_argument("--headless")  # Uncomment to run in headless mode
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    driver = webdriver.Chrome(service=service, options=options)

    try:
        # Step 1: Navigate to the given URL
        driver.get(url)

        # Step 2: Wait for the page to load completely
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))  # Ensure page has loaded
        )

        # Step 3: Look for file upload and file structure
        has_file_upload = False
        has_file_structure = False

        try:
            # Check for a file upload input
            WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='file']"))
            )
            has_file_upload = True
        except TimeoutException:
            pass

        try:
            # Check for a table or file listing structure
            file_table = driver.find_element(By.TAG_NAME, "table")
            if file_table:
                has_file_structure = True
        except NoSuchElementException:
            pass

        # Step 4: Determine if the site is working
        if has_file_upload and has_file_structure:
            return f"Working: {url}"
        else:
            return f"Not working: {url} - No file management interface found"

    except (TimeoutException, WebDriverException) as e:
        return f"Not working: {url} - {str(e)}"

    finally:
        driver.quit()


def process_single_site(site, driver_path, success_file, failure_file):
    """
    Helper function to process a single site.
    """
    url = site.strip()
    print(f"Processing site: {url}")
    result = check_file_management_interface(url, driver_path)
    print(f"Result for {url}: {result}\n")

    # Save results to the appropriate file
    if "Working" in result:
        with open(success_file, 'a') as success_log:
            success_log.write(f"{url}\n")
    else:
        with open(failure_file, 'a') as failure_log:
            failure_log.write(f"{url}\n")


def process_sites_from_file(file_path, driver_path, success_file, failure_file, max_workers=15):
    """
    Process multiple sites concurrently.
    """
    try:
        with open(file_path, 'r') as file:
            lines = file.readlines()
            tasks = []

            # Parse each line
            for line in lines:
                if not line.strip():
                    continue
                tasks.append(line.strip())

            # Process sites concurrently
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                for site in tasks:
                    executor.submit(
                        process_single_site,
                        site,
                        driver_path,
                        success_file,
                        failure_file,
                    )
    except FileNotFoundError:
        print(f"File not found: {file_path}")


# Example usage
file_path = "/Users/nafseerck/OTT/pythonscript/shell-urls.txt"  # Path to your text file
driver_path = "/Users/nafseerck/OTT/pythonscript/chromedriver"  # Path to your ChromeDriver
success_file = "/Users/nafseerck/OTT/pythonscript/success_urls.txt"
failure_file = "/Users/nafseerck/OTT/pythonscript/not_working_urls.txt"

start_time = time.time()
process_sites_from_file(file_path, driver_path, success_file, failure_file, max_workers=15)
end_time = time.time()

print(f"Finished processing sites in {end_time - start_time:.2f} seconds.")
