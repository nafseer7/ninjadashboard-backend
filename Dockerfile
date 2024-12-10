# Use Python base image
FROM python:3.10-slim

# Set working directory inside the container
WORKDIR /app

# Install dependencies (including Chromium and ChromeDriver)
RUN apt-get update && apt-get install -y \
    wget \
    curl \
    unzip \
    chromium \
    chromium-driver \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install Selenium
RUN pip install selenium

# Copy the entire project
COPY . .

# Expose ports for the APIs
EXPOSE 8080
EXPOSE 8200

# Set environment variables for Chromium
ENV CHROME_BIN=/usr/bin/chromium
ENV CHROME_DRIVER=/usr/lib/chromium/chromium-driver

# Default command (can be overridden)
CMD ["uvicorn"]
