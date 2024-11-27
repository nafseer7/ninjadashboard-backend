import requests

# Function to download a video from a URL
def download_video(video_url, output_file):
    try:
        # Send a GET request to the video URL
        response = requests.get(video_url, stream=True)
        response.raise_for_status()  # Raise an error for bad HTTP status codes

        # Write the video content to the output file
        with open(output_file, "wb") as file:
            for chunk in response.iter_content(chunk_size=1024):
                if chunk:
                    file.write(chunk)

        print(f"Video downloaded successfully as {output_file}")

    except requests.exceptions.RequestException as e:
        print(f"Error downloading {video_url}: {e}")

# Function to process the input file with video URLs
def process_input_file(input_file):
    try:
        with open(input_file, "r") as file:
            urls = [line.strip() for line in file if line.strip()]  # Read and clean up lines

        for i, url in enumerate(urls):
            # Generate a unique output file name for each video
            output_file = f"video_{i + 1}.mp4"
            print(f"Downloading video {i + 1} from {url}...")
            download_video(url, output_file)

    except FileNotFoundError:
        print(f"Input file '{input_file}' not found.")

if __name__ == "__main__":
    # Ask user for the input file name
    input_file = input("Enter the input file name containing video URLs: ").strip()
    process_input_file(input_file)
