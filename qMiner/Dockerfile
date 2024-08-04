# Use an Alpine-based Python image
FROM python:3.12-alpine

# Set working directory
WORKDIR /app

# Copy requirements file
COPY requirements.txt .

# Install Python packages
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY . .

# Run the application
CMD ["flask", "run", "--host", "0.0.0.0"]