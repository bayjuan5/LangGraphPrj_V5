# 1. Base image: Python 3.11 slim (Linux) for stable dependency compatibility
FROM python:3.11-slim

# 2. Set working directory inside the container
WORKDIR /app

# 3. Install dependencies first (leverages Docker layer cache)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 4. Copy application code and frontend assets
COPY . .

# 5. Expose the application port
EXPOSE 5000

# 6. Launch the server (browser auto-open disabled in container)
ENV NO_BROWSER=1
CMD ["python", "app.py"]
