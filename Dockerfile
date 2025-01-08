# Use Python base image
FROM python:3.10-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1

# Install required dependencies for Chrome
RUN apt-get update && apt-get install -y \
    wget \
    gnupg2 \
    unzip \
    curl \
    ca-certificates \
    libx11-6 \
    libxcomposite1 \
    libxrandr2 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdbus-1-3 \
    libdrm2 \
    libexpat1 \
    libgbm1 \
    libglib2.0-0 \
    libgtk-3-0 \
    libnss3 \
    libpango-1.0-0 \
    libvulkan1 \
    libasound2 \
    xdg-utils \
    fonts-liberation \
    && apt-get clean

# Install Google Chrome
RUN wget https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb \
    && dpkg -i google-chrome-stable_current_amd64.deb \
    && apt-get install -f -y \
    && rm google-chrome-stable_current_amd64.deb

# Install the correct version of ChromeDriver that matches Google Chrome version 131
RUN wget https://storage.googleapis.com/chrome-for-testing-public/131.0.6778.204/linux64/chromedriver-linux64.zip \
    && unzip chromedriver-linux64.zip \
    && mv chromedriver-linux64/chromedriver /usr/local/bin/ \
    && rm -rf chromedriver-linux64 chromedriver-linux64.zip

# Set working directory inside the container
WORKDIR /app

# Copy requirements.txt and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the entire project
COPY . .

# Expose ports for the APIs
EXPOSE 8080
EXPOSE 8200
EXPOSE 8500

# Default command (can be overridden..)
CMD ["uvicorn"]
