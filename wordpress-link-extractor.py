# Input and output file names
input_file = "wordpress-login-notfiltered.txt"  # Replace with your input file name
output_file = "wordpress-linkonly.txt"  # The output file with only URLs

# Read the input file and process each line
with open(input_file, "r") as infile:
    
    lines = infile.readlines()

# Extract only the URL part (first item before the first comma)
urls = [line.split(",")[0].strip() for line in lines if "," in line]

# Write the URLs to the output file
with open(output_file, "w") as outfile:
    outfile.write("\n".join(urls))

print(f"URLs extracted and saved to {output_file}")
