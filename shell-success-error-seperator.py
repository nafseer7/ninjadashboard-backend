import requests
from concurrent.futures import ThreadPoolExecutor, as_completed

# Paths to the input and output files
input_file_path = "shell-urls.txt"  # Input file containing URLs
success_file_path = "success-urls.txt"  # File to store successful URLs
error_file_path = "error-urls.txt"  # File to store failed/error URLs

# Function to check the shell program URL
def check_shell_url(url):
    try:
        response = requests.get(url, timeout=5, stream=True)  # Use stream for efficiency
        if response.status_code == 200:
            return (url, "Success")
        else:
            return (url, f"Failed (Status code: {response.status_code})")
    except requests.exceptions.RequestException as e:
        return (url, f"Error: {e}")

# Process URLs concurrently and separate results into two files
def process_urls(input_file, success_file, error_file):
    try:
        # Read the input file
        with open(input_file, "r") as file:
            urls = [line.strip() for line in file if line.strip()]
        
        # Use ThreadPoolExecutor for concurrency
        results = []
        with ThreadPoolExecutor(max_workers=50) as executor:  # Increase max_workers for higher concurrency
            future_to_url = {executor.submit(check_shell_url, url): url for url in urls}
            for future in as_completed(future_to_url):
                try:
                    results.append(future.result())
                except Exception as e:
                    results.append((future_to_url[future], f"Error: {e}"))
        
        # Separate success and error results
        success_urls = [url for url, status in results if status == "Success"]
        error_urls = [f"{url},{status}" for url, status in results if status != "Success"]

        # Write success results to the success file
        with open(success_file, "w") as success_out:
            for url in success_urls:
                success_out.write(url + "\n")
        
        # Write error results to the error file
        with open(error_file, "w") as error_out:
            for error in error_urls:
                error_out.write(error + "\n")
        
        print(f"Success URLs saved to {success_file}")
        print(f"Error URLs saved to {error_file}")

    except FileNotFoundError:
        print(f"File not found: {input_file}")

# Run the program
if __name__ == "__main__":
    process_urls(input_file_path, success_file_path, error_file_path)
