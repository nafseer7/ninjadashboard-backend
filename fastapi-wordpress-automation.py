from fastapi import FastAPI, File, UploadFile, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException, WebDriverException
from concurrent.futures import ThreadPoolExecutor
import os
import re
from datetime import datetime
from fastapi.middleware.cors import CORSMiddleware
import requests
from pydantic import BaseModel,HttpUrl
from fastapi.logger import logger
import tempfile
import threading




class LoginRequest(BaseModel):
    site_url: HttpUrl  # Ensures a valid URL is provided
    username: str
    password: str

driver = None


app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Replace "*" with your frontend domain in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Directory setup
UPLOAD_DIR = "uploads"
CLEANED_DIR = "cleaned"
OUTPUT_DIR = "outputs"
CHROMEDRIVER_PATH = "chromedriver.exe"

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(CLEANED_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)


def clean_file(input_file_path, output_file_path):
    """Cleans the uploaded file."""
    with open(input_file_path, 'r') as file:
        lines = file.readlines()

    cleaned_lines = []
    for line in lines:
        line = line.strip()  # Remove leading/trailing whitespaces
        line = line.replace(';', ',')  # Replace semicolons with commas
        line = re.sub(r'\"', '', line)  # Remove double quotes
        if line:  # If line is not empty
            cleaned_lines.append(line)

    with open(output_file_path, 'w') as file:
        for line in cleaned_lines:
            file.write(line + '\n')


def format_url(url):
    """Ensure the URL has a valid format with http:// or https://."""
    if not url.startswith("http://") and not url.startswith("https://"):
        url = "http://" + url
    return url


def is_valid_url(url):
    """Validate the URL using regex."""
    regex = re.compile(r'^(http://|https://)?([a-zA-Z0-9.-]+\.[a-zA-Z]{2,})(/.*)?$')
    return re.match(regex, url) is not None


@app.post("/upload/")
async def upload_and_clean_file(file: UploadFile = File(...)):
    """Upload and clean a .txt file."""
    if not file.filename.endswith(".txt"):
        raise HTTPException(status_code=400, detail="Only .txt files are allowed.")

    # Include timestamp in the cleaned filename
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    cleaned_file_name = f"cleaned_{timestamp}_{file.filename}"
    cleaned_file_path = os.path.join(CLEANED_DIR, cleaned_file_name)

    # Save the uploaded file
    input_file_path = os.path.join(UPLOAD_DIR, file.filename)
    with open(input_file_path, "wb") as f:
        f.write(await file.read())

    # Clean the file
    clean_file(input_file_path, cleaned_file_path)

    return {
        "message": "File uploaded and cleaned successfully.",
        "timestamp": timestamp,
        "cleaned_file_name": cleaned_file_name,
    }


@app.get("/list-cleaned/")
def list_cleaned_files():
    """List all available cleaned files."""
    cleaned_files = [
        {"filename": file, "timestamp": file.split("_")[1]}  # Extract timestamp
        for file in os.listdir(CLEANED_DIR) if file.startswith("cleaned_")
    ]
    if not cleaned_files:
        return {"message": "No cleaned files available."}
    return cleaned_files

@app.get("/list-success-cleaned/")
def list_success_cleaned_files():
    """List all available success cleaned files in the outputs directory."""
    success_files = [
        {"filename": file}
        for file in os.listdir(OUTPUT_DIR) if file.startswith("success_cleaned")
    ]
    if not success_files:
        return {"message": "No success cleaned files available."}
    return success_files

@app.get("/view-content/")
def view_file_content(file_name: str):
    """View the content of a cleaned file in a structured JSON format."""
    file_path = os.path.join(OUTPUT_DIR, file_name)

    # Check if the file exists
    if not os.path.exists(file_path):
        return JSONResponse(
            status_code=404,
            content={"error": "File not found.", "file_name": file_name}
        )

    structured_content = []

    try:
        # Read and parse the file
        with open(file_path, 'r') as file:
            lines = file.readlines()
            for line in lines:
                try:
                    site, username, password = line.strip().split(',')
                    structured_content.append({
                        "website": site.strip(),
                        "username": username.strip(),
                        "password": password.strip()
                    })
                except ValueError:
                    structured_content.append({
                        "error": f"Invalid line format: {line.strip()}"
                    })

        return JSONResponse(content=structured_content, status_code=200)

    except Exception as e:
        # Handle unexpected errors
        return JSONResponse(
            status_code=500,
            content={"error": "An unexpected error occurred.", "details": str(e)}
        )

@app.post("/process-cleaned/")
def process_cleaned_file(file_name: str):
    """Process the cleaned file for WordPress login checking."""
    cleaned_file_path = os.path.join(CLEANED_DIR, file_name)
    if not os.path.exists(cleaned_file_path):
        raise HTTPException(status_code=404, detail="Cleaned file not found.")

    success_file = os.path.join(OUTPUT_DIR, f"success_{file_name}")
    failure_file = os.path.join(OUTPUT_DIR, f"failure_{file_name}")

    success_entries = []
    failure_entries = []

    def process_line(line):
        """Process a single line."""
        try:
            site, username, password = line.strip().split(',')
            result = check_wordpress_with_selenium(site, username, password)
            if "Login successful" in result:
                success_entries.append(line.strip())
            else:
                failure_entries.append(line.strip())
        except ValueError:
            failure_entries.append(line.strip())

    # Read cleaned file and process concurrently
    with open(cleaned_file_path, 'r') as file:
        lines = file.readlines()

    with ThreadPoolExecutor() as executor:
        executor.map(process_line, lines)

    # Write results to files
    with open(success_file, 'w') as file:
        for entry in success_entries:
            file.write(entry + '\n')

    with open(failure_file, 'w') as file:
        for entry in failure_entries:
            file.write(entry + '\n')

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return {
        "message": "Processing completed.",
        "timestamp": timestamp,
        "success_file": success_file,
        "failure_file": failure_file,
    }


@app.get("/download/{file_name}")
async def download_file(file_name: str):
    """Download a file."""
    file_path = os.path.join(OUTPUT_DIR, file_name)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found.")
    return FileResponse(file_path)

@app.post("/proxy/moz-metrics/")
async def moz_metrics_proxy(request: Request):
    moz_api_url = "https://api.moz.com/jsonrpc"
    moz_token = "bW96c2NhcGUtb0xTSllzbTlYMDpaN2NGeERNaDhodFllc0JLSEFsTzc0TWtHczRrTFhXWQ=="

    try:
        payload = await request.json()
        response = requests.post(
            moz_api_url,
            headers={
                "x-moz-token": moz_token,
                "Content-Type": "application/json",
            },
            json=payload,
        )
        return JSONResponse(content=response.json(), status_code=response.status_code)
    except Exception as e:
        return JSONResponse(
            content={"error": str(e)}, status_code=500
        )

def get_persistent_driver():
    """Create or retrieve a persistent WebDriver instance."""
    global driver
    if driver is None:
        options = webdriver.ChromeOptions()
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        driver = webdriver.Chrome(service=Service(CHROMEDRIVER_PATH), options=options)
    return driver

def login_to_wordpress_in_tab(site_url: str, username: str, password: str):
    """Handles WordPress login in a new tab of the persistent browser session."""
    persistent_driver = get_persistent_driver()

    try:
        # Open a new tab
        persistent_driver.execute_script("window.open('');")
        new_tab_index = len(persistent_driver.window_handles) - 1
        persistent_driver.switch_to.window(persistent_driver.window_handles[new_tab_index])

        login_url = f"{site_url.rstrip('/')}/wp-login.php"
        persistent_driver.get(login_url)

        # Wait for login elements
        username_input = WebDriverWait(persistent_driver, 20).until(
            EC.presence_of_element_located((By.ID, "user_login"))
        )
        password_input = persistent_driver.find_element(By.ID, "user_pass")
        submit_button = persistent_driver.find_element(By.ID, "wp-submit")

        # Input credentials and log in
        username_input.send_keys(username)
        password_input.send_keys(password)
        submit_button.click()

        # Wait for wp-admin navigation
        WebDriverWait(persistent_driver, 20).until(lambda d: "wp-admin" in d.current_url)

        print(f"Login successful in tab {new_tab_index}. Admin URL: {persistent_driver.current_url}")

    except TimeoutException as e:
        print(f"Timeout occurred in tab {new_tab_index}: {str(e)}")
    except Exception as e:
        print(f"Error in tab {new_tab_index}: {str(e)}")

# @app.post("/login-wordpress/")
# async def login_wordpress(request: LoginRequest):
#     """
#     API endpoint to initiate WordPress login in a new tab of the persistent browser session.
#     """
#     site_url = str(request.site_url)  # Convert HttpUrl to string
#     username = request.username
#     password = request.password

#     print(f"Starting login process for: {site_url}")

#     # Run the login in a new thread
#     threading.Thread(target=login_to_wordpress_in_tab, args=(site_url, username, password)).start()

#     return {"message": f"Login process started for {site_url}. A new tab has been opened."}


@app.post("/login-wordpress/")
async def login_wordpress(request: LoginRequest):
    """
    API endpoint to log in to WordPress using HTTP requests.
    """
    site_url = request.site_url.rstrip("/")  # Ensure no trailing slash
    username = request.username
    password = request.password

    try:
        login_url = f"{site_url}/wp-login.php"

        # Simulate the login using requests
        with requests.Session() as session:
            payload = {
                "log": username,
                "pwd": password,
                "wp-submit": "Log In",
                "redirect_to": f"{site_url}/wp-admin/",
            }
            headers = {
                "Content-Type": "application/x-www-form-urlencoded",
            }

            # Send the login POST request
            response = session.post(login_url, data=payload, headers=headers)

            # Check if login was successful by looking for redirect to wp-admin
            if response.url.endswith("/wp-admin/"):
                cookies = session.cookies.get_dict()
                return {
                    "message": "Login successful",
                    "admin_url": f"{site_url}/wp-admin/",
                    "cookies": cookies,
                }

            # Check for login error message
            if "login_error" in response.text:
                return {
                    "message": "Login failed. Please check your credentials.",
                    "error": "Invalid username or password.",
                }

        return {"message": "Unexpected response. Login might have failed."}

    except Exception as e:
        return {"message": f"An error occurred: {str(e)}"}


def check_wordpress_with_selenium(url, username, password):
    """Check WordPress login using Selenium."""
    url = format_url(url)
    if not is_valid_url(url):
        return f"Invalid URL: {url}"

    options = webdriver.ChromeOptions()
    options.add_argument("--headless")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    driver = webdriver.Chrome(service=Service(CHROMEDRIVER_PATH), options=options)

    try:
        login_url = f"{url.rstrip('/')}/wp-login.php"
        driver.get(login_url)
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

        WebDriverWait(driver, 10).until(lambda d: d.current_url != login_url)
        if "wp-admin" in driver.current_url:
            return f"Login successful: {url}"

        try:
            error_element = driver.find_element(By.ID, "login_error")
            return f"Login failed for {url}: {error_element.text}"
        except NoSuchElementException:
            return f"No explicit error found for {url}. Login might have failed."

    except Exception as e:
        return f"An error occurred for {url}: {e}"
    finally:
        driver.quit()


