FROM python:3.9-slim

# Set working directory
WORKDIR /app

# Copy requirements first to leverage Docker cache
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

# Expose port 80
EXPOSE 80

# Set environment variables
ENV FLASK_APP=app.py
ENV FLASK_ENV=production

# Create directory for SQLite database
RUN mkdir -p db

# Run the application
CMD ["python", "app.py"]