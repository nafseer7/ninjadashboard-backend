# Paths to the input and output files
input_file_path = "results.txt"  # Input file containing site details
success_file_path = "wordpress-login-success-urls.txt"  # File to store successful URLs
error_file_path = "wordpress-login-error-urls.txt"  # File to store failed/error URLs

# Function to process the input and separate success and error URLs
def process_results(input_file, success_file, error_file):
    try:
        success_urls = []
        error_urls = []
        
        # Read the input file
        with open(input_file, "r") as file:
            for line in file:
                if line.strip():  # Skip empty lines
                    parts = line.strip().split(",")
                    if len(parts) == 4:  # Ensure correct format
                        site_name = parts[0].strip()
                        status = parts[3].strip()
                        
                        if "Login successful" in status:
                            success_urls.append(site_name)
                        else:
                            error_urls.append(f"{site_name},{status}")
        
        # Write success URLs to the success file
        with open(success_file, "w") as success_out:
            for url in success_urls:
                success_out.write(url + "\n")
        
        # Write error URLs to the error file
        with open(error_file, "w") as error_out:
            for error in error_urls:
                error_out.write(error + "\n")
        
        print(f"Success URLs saved to {success_file}")
        print(f"Error URLs saved to {error_file}")

    except FileNotFoundError:
        print(f"File not found: {input_file}")

# Run the program
if __name__ == "__main__":
    process_results(input_file_path, success_file_path, error_file_path)
