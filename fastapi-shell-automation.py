from fastapi import FastAPI, File, UploadFile, HTTPException, Request
from fastapi.responses import JSONResponse
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import WebDriverException, TimeoutException, NoSuchElementException
from concurrent.futures import ThreadPoolExecutor
import os
import tempfile
import datetime
from fastapi.middleware.cors import CORSMiddleware
import requests



app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Replace "*" with your frontend domain in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Path to ChromeDriver
CHROMEDRIVER_PATH = "chromedriver.exe"

# Directories for output files
OUTPUT_DIR = "output_files_shells"
SUCCESS_DIR = os.path.join(OUTPUT_DIR, "success")
ERROR_DIR = os.path.join(OUTPUT_DIR, "error")

os.makedirs(SUCCESS_DIR, exist_ok=True)
os.makedirs(ERROR_DIR, exist_ok=True)


@app.get("/list-success-files/")
async def list_success_files():
    """
    Endpoint to list all files in the success folder.
    """
    try:
        files = os.listdir(SUCCESS_DIR)
        success_files = [file for file in files if file.startswith("success_")]
        return JSONResponse(content={"success_files": success_files})
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")


@app.post("/upload/")
async def upload_file(file: UploadFile = File(...)):
    """
    Endpoint to upload a file containing URLs and save success/error results with timestamps.
    """
    if not file.filename.endswith(".txt"):
        raise HTTPException(status_code=400, detail="Only .txt files are allowed.")

    # Save the uploaded file to a temporary file
    try:
        temp_file = tempfile.NamedTemporaryFile(delete=False)
        temp_file.write(await file.read())
        temp_file.close()

        # Read URLs from the file
        with open(temp_file.name, "r") as f:
            urls = [line.strip() for line in f.readlines() if line.strip()]

        # Process URLs
        results = process_sites(urls, CHROMEDRIVER_PATH)

        # Cleanup temporary file
        os.unlink(temp_file.name)

        # Save results with timestamps
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        success_file = os.path.join(SUCCESS_DIR, f"success_{timestamp}.txt")
        error_file = os.path.join(ERROR_DIR, f"error_{timestamp}.txt")

        with open(success_file, "w") as sf:
            sf.writelines([f"{url}\n" for url in results["working"]])

        with open(error_file, "w") as ef:
            ef.writelines([f"{url}\n" for url in results["not_working"]])

        return JSONResponse(content={
            "success_file": success_file,
            "error_file": error_file,
        })

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")


@app.get("/view-file/")
async def view_file(file_name: str):
    """
    Endpoint to view the content of a success or error file as JSON.
    """
    file_path = os.path.join(SUCCESS_DIR, file_name) if "success" in file_name else os.path.join(ERROR_DIR, file_name)

    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found.")

    try:
        with open(file_path, "r") as f:
            urls = [line.strip() for line in f.readlines()]
        return JSONResponse(content={"urls": urls})

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")


def create_driver(driver_path: str):
    """
    Create a Selenium WebDriver instance with optimized settings.
    """
    service = Service(driver_path)
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")  # Use headless mode for better performance
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.page_load_strategy = "eager"  # Optimize page load strategy
    return webdriver.Chrome(service=service, options=options)


def check_file_management_interface(url: str, driver: webdriver.Chrome) -> str:
    """
    Check if the URL has a file upload and management interface, including 404 error detection.
    """
    try:
        # Navigate to the given URL
        driver.get(url)

        # Wait for the page to load partially
        WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )

        # Check for 404 error by looking for common indicators (title or body content)
        try:
            page_title = driver.title.lower()
            if "404" in page_title or "not found" in page_title:
                return f"Not working: {url} - 404 Not Found"
        except Exception:
            pass

        try:
            page_body = driver.find_element(By.TAG_NAME, "body").text.lower()
            if "404" in page_body or "not found" in page_body:
                return f"Not working: {url} - 404 Not Found"
        except NoSuchElementException:
            pass

        # Look for file upload and file structure
        has_file_upload = False
        has_file_structure = False

        try:
            WebDriverWait(driver, 3).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='file']"))
            )
            has_file_upload = True
        except TimeoutException:
            pass

        try:
            file_table = driver.find_element(By.TAG_NAME, "table")
            if file_table:
                has_file_structure = True
        except NoSuchElementException:
            pass

        # Determine if the site is working
        if has_file_upload and has_file_structure:
            return f"Working: {url}"
        else:
            return f"Not working: {url} - No file management interface found"

    except (TimeoutException, WebDriverException) as e:
        return f"Not working: {url} - {str(e)}"


def process_sites(sites: list, driver_path: str) -> dict:
    """
    Process multiple sites concurrently and return results.
    """
    results = {"working": [], "not_working": []}

    def process_single_site(site):
        driver = create_driver(driver_path)  # Create a new driver instance for each thread
        try:
            result = check_file_management_interface(site, driver)
            if "Working" in result:
                results["working"].append(site)
            else:
                results["not_working"].append(site)
        finally:
            driver.quit()

    # Use ThreadPoolExecutor for concurrent processing
    with ThreadPoolExecutor(max_workers=20) as executor:
        executor.map(process_single_site, sites)

    return results

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



@app.post("/remove-duplicate-domains/")
async def remove_duplicate_domains(file: UploadFile = File(...)):
    """
    API to remove duplicate domains from a file containing URLs.
    """
    if not file.filename.endswith(".txt"):
        raise HTTPException(status_code=400, detail="Only .txt files are allowed.")

    try:
        # Save the uploaded file to a temporary file
        temp_file = tempfile.NamedTemporaryFile(delete=False)
        temp_file.write(await file.read())
        temp_file.close()

        unique_domains = {}
        cleaned_urls = []

        with open(temp_file.name, "r") as f:
            for line in f:
                url = line.strip()
                if url:
                    domain = extract_domain(url)
                    if domain not in unique_domains:
                        unique_domains[domain] = url

        # Retain only one URL per domain
        cleaned_urls = list(unique_domains.values())

        # Save the cleaned file
        output_file = os.path.join(OUTPUT_DIR, f"cleaned_{file.filename}")
        with open(output_file, "w") as f:
            for url in cleaned_urls:
                f.write(f"{url}\n")

        # Cleanup temporary file
        os.unlink(temp_file.name)

        return JSONResponse(content={
            "message": "Duplicate domains removed successfully.",
            "cleaned_file": output_file,
        })

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")


def extract_domain(url: str) -> str:
    """
    Extract the domain from a given URL.
    """
    try:
        # Extract domain using urllib
        from urllib.parse import urlparse
        parsed_url = urlparse(url)
        return parsed_url.netloc.lower()  # Return domain in lowercase
    except Exception:
        # If URL is invalid, return the full URL for comparison
        return url.lower()
