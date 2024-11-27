import requests
from concurrent.futures import ThreadPoolExecutor, as_completed

# Path to the input and output files
input_file_path = "shell-urls.txt"  # Input file containing URLs
output_file_path = "shell-check-results.txt"  # Output file for results

# Function to check the shell program URL
def check_shell_url(url):
    try:
        response = requests.get(url, timeout=5, stream=True)  # Use stream for faster response handling
        if response.status_code == 200:
            return f"{url},Success"
        else:
            return f"{url},Failed (Status code: {response.status_code})"
    except requests.exceptions.RequestException as e:
        return f"{url},Error: {e}"

# Process URLs concurrently and write results to a file
def process_urls(input_file, output_file):
    try:
        # Read the input file
        with open(input_file, "r") as file:
            urls = [line.strip() for line in file if line.strip()]
        
        # Use ThreadPoolExecutor for concurrency
        results = []
        with ThreadPoolExecutor(max_workers=100) as executor:  # Increase max_workers for higher concurrency
            future_to_url = {executor.submit(check_shell_url, url): url for url in urls}
            for future in as_completed(future_to_url):
                try:
                    results.append(future.result())
                except Exception as e:
                    results.append(f"{future_to_url[future]},Error: {e}")
        
        # Write results to the output file
        with open(output_file, "w") as out_file:
            out_file.write("url,status\n")  # Write header
            out_file.writelines(result + "\n" for result in results)
        print(f"Results saved to {output_file}")

    except FileNotFoundError:
        print(f"File not found: {input_file}")

# Run the program
if __name__ == "__main__":
    process_urls(input_file_path, output_file_path)
