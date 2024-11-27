import re

def clean_file(input_file, output_file):
    with open(input_file, 'r') as file:
        lines = file.readlines()

    cleaned_lines = []
    for line in lines:
        # Remove whitespace and trailing characters
        line = line.strip()
        
        # Replace semicolons with commas
        line = line.replace(';', ',')
        
        # Remove double quotes
        line = re.sub(r'\"', '', line)
        
        # Add cleaned line if not empty
        if line:
            cleaned_lines.append(line)

    # Write cleaned lines to the output file
    with open(output_file, 'w') as file:
        for line in cleaned_lines:
            file.write(line + '\n')

if __name__ == '__main__':
    input_file = 'wordpress-login-notfiltered.txt'  # Replace with your input file name
    output_file = 'wordpress-login-notfiltered-cleanfile.txt'  # Replace with your desired output file name
    clean_file(input_file, output_file)
    print(f"Cleaned file has been saved to {output_file}")
