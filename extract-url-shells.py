
from urllib.parse import urlparse

# Input file containing URLs
input_file_path = "extract-shell-url.txt"

# Output file to store extracted domains
output_file_path = "extract-url-domains.txt"

def extract_domain(url):
    """
    Extract the protocol and domain from a URL.
    """
    parsed_url = urlparse(url)
    return f"{parsed_url.scheme}://{parsed_url.netloc}/"

def process_urls(input_file, output_file):
    try:
        with open(input_file, "r") as file:
            urls = [line.strip() for line in file if line.strip()]
        
        # Extract domains
        domains = [extract_domain(url) for url in urls]
        
        # Write domains to the output file
        with open(output_file, "w") as out_file:
            for domain in domains:
                out_file.write(domain + "\n")
        
        print(f"Extracted domains saved to {output_file}")
    except FileNotFoundError:
        print(f"File not found: {input_file}")

if __name__ == "__main__":
    process_urls(input_file_path, output_file_path)
