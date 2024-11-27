import csv

# Input file name
input_file = "results.txt"

# Output files
successful_file = "wordpress-successful.txt"
errors_file = "wordpress-errors.txt"

# Open input and output files
with open(input_file, "r") as infile:
    csv_reader = csv.reader(infile)
    
    # Skip the header row
    header = next(csv_reader)
    
    # Prepare data holders
    successful_entries = []
    error_entries = []
    
    # Read the input file row by row
    for row in csv_reader:
        if len(row) < 4:
            continue  # Skip invalid rows
        
        site_name, username, password, status = row[:4]
        
        # Categorize based on the status
        if "successful" in status.lower():
            successful_entries.append(f"{site_name},{username},{password}")
        else:
            error_entries.append(f"{site_name},{username},{password}")

# Write successful logins to the successful file
with open(successful_file, "w") as success_file:
    success_file.write("\n".join(successful_entries))

# Write errors to the errors file
with open(errors_file, "w") as error_file:
    error_file.write("\n".join(error_entries))

print("Splitting completed! Check 'successful.txt' and 'errors.txt'.")
