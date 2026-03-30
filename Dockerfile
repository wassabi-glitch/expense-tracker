# 1. Use Python 3.12 as the base
FROM python:3.12-slim

# 2. Set the working directory inside the container
WORKDIR /app

# 3. Set environment variables
# Prevents Python from writing .pyc files
ENV PYTHONDONTWRITEBYTECODE 1
# Ensures logs are sent straight to the terminal
ENV PYTHONUNBUFFERED 1

# 4. Install system dependencies
# We need 'libpq-dev' and 'gcc' so the 'psycopg2' library can talk to Postgres
RUN apt-get update && apt-get install -y \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# 5. Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 6. Copy the entire project into the container
COPY . .

# 7. The command to run the app
# Bind to dual-stack (::) for Railway private/public networking compatibility.
# Use Railway-provided PORT in cloud and default to 9000 locally.
CMD ["sh", "-c", "uvicorn app.main:app --host :: --port ${PORT:-9000} --proxy-headers --forwarded-allow-ips='*'"]
