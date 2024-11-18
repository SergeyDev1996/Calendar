# Use an official Python image as a base
FROM python:3.10-slim

# Set the working directory
WORKDIR /app

# Copy the application code to the container
COPY . /app

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Expose a port if needed (e.g., if the app runs a web server)
# EXPOSE 8000

# Set environment variables for Python
ENV PYTHONUNBUFFERED=1

# Define the command to run the application
CMD ["python", "main.py"]