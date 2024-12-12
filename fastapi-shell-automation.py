from fastapi import FastAPI, File, UploadFile, HTTPException, Request
from fastapi.responses import JSONResponse
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import WebDriverException, TimeoutException, NoSuchElementException
from concurrent.futures import ThreadPoolExecutor, as_completed
import os
import tempfile
from fastapi.middleware.cors import CORSMiddleware
import requests
from pymongo import MongoClient
from bson import ObjectId
from datetime import datetime
from bs4 import BeautifulSoup
import traceback

# MongoDB Configuration
MONGO_URI = "mongodb+srv://nafseerck:7gbNMNAc5s236F5K@overthetop.isxuv3s.mongodb.net/smaiDB"
DB_NAME = "ninjadb"
COLLECTION_NAME = "urls"

client = MongoClient(MONGO_URI)
db = client[DB_NAME]
collection = db[COLLECTION_NAME]

# FastAPI app setup
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Paths for ChromeDriver and output directories
CHROMEDRIVER_PATH = "/usr/bin/chromedriver"
OUTPUT_DIR = "output_files_shells"
SUCCESS_DIR = os.path.join(OUTPUT_DIR, "success")
ERROR_DIR = os.path.join(OUTPUT_DIR, "error")

os.makedirs(SUCCESS_DIR, exist_ok=True)
os.makedirs(ERROR_DIR, exist_ok=True)


@app.get("/list-success-files/")
async def list_success_files():
    """List all files in the success folder."""
    try:
        files = os.listdir(SUCCESS_DIR)
        success_files = [file for file in files if file.startswith("success_")]
        return JSONResponse(content={"success_files": success_files})
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")


@app.post("/upload/")
async def upload_file(file: UploadFile = File(...)):
    """Upload a file containing URLs and save success/error results."""
    if not file.filename.endswith(".txt"):
        raise HTTPException(status_code=400, detail="Only .txt files are allowed.")

    try:
        temp_file = tempfile.NamedTemporaryFile(delete=False)
        temp_file.write(await file.read())
        temp_file.close()

        with open(temp_file.name, "r") as f:
            urls = [line.strip() for line in f.readlines() if line.strip()]

        results = process_sites(urls, CHROMEDRIVER_PATH)

        os.unlink(temp_file.name)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        success_file = os.path.join(SUCCESS_DIR, f"success_{timestamp}.txt")
        error_file = os.path.join(ERROR_DIR, f"error_{timestamp}.txt")

        with open(success_file, "w") as sf:
            sf.writelines([f"{url}\n" for url in results["working"]])

        with open(error_file, "w") as ef:
            ef.writelines([f"{url}\n" for url in results["not_working"]])

        return JSONResponse(content={"success_file": success_file, "error_file": error_file})

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")


@app.get("/view-file/")
async def view_file(file_name: str):
    """View the content of a success or error file as JSON."""
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
    """Create a Selenium WebDriver instance with optimized settings."""
    service = Service(driver_path)
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.page_load_strategy = "eager"
    return webdriver.Chrome(service=service, options=options)


def check_file_management_interface(url: str, driver: webdriver.Chrome) -> str:
    """Check if the URL has a file upload and management interface."""
    try:
        driver.get(url)
        WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.TAG_NAME, "body")))

        page_title = driver.title.lower()
        if "404" in page_title or "not found" in page_title:
            return f"Not working: {url} - 404 Not Found"

        try:
            driver.find_element(By.CSS_SELECTOR, "input[type='file']")
            return f"Working: {url}"
        except NoSuchElementException:
            return f"Not working: {url} - No file input found"

    except Exception as e:
        return f"Not working: {url} - {str(e)}"


def process_sites(sites: list, driver_path: str) -> dict:
    """Process multiple sites concurrently."""
    results = {"working": [], "not_working": []}

    def process_single_site(site):
        driver = create_driver(driver_path)
        try:
            result = check_file_management_interface(site, driver)
            if "Working" in result:
                results["working"].append(site)
            else:
                results["not_working"].append(site)
        finally:
            driver.quit()

    with ThreadPoolExecutor(max_workers=100) as executor:
        executor.map(process_single_site, sites)

    return results


def serialize_document(document):
    """Serialize MongoDB documents, converting ObjectId and datetime."""
    for key, value in document.items():
        if isinstance(value, ObjectId):
            document[key] = str(value)
        elif isinstance(value, datetime):
            document[key] = value.isoformat()
    return document


@app.post("/process-url-mappings/{document_id}")
async def process_url_mappings(document_id: str):
    """Process URL mappings from a MongoDB document and update the document."""
    try:
        document = collection.find_one({"_id": ObjectId(document_id)})
        if not document:
            raise HTTPException(status_code=404, detail="Document not found.")

        url_mappings = document.get("urlMappings", [])
        if not url_mappings:
            raise HTTPException(status_code=400, detail="No URL mappings found in the document.")

        original_urls = [url_mapping["original"] for url_mapping in url_mappings if "original" in url_mapping]
        working_urls = process_sites(original_urls, CHROMEDRIVER_PATH)

        updated_url_mappings = [
            url_mapping for url_mapping in url_mappings if url_mapping["original"] in working_urls["working"]
        ]
        collection.update_one(
            {"_id": ObjectId(document_id)},
            {"$set": {"urlMappings": updated_url_mappings, "status": "processed"}}
        )

        updated_document = serialize_document(collection.find_one({"_id": ObjectId(document_id)}))
        return JSONResponse(content={"message": "Document updated successfully.", "updated_document": updated_document})

    except Exception as e:
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")
