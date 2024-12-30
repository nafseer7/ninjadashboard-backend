# Use Python base image
FROM python:3.10-slim

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
