# 1. Use a valid base image
FROM python:3.12-alpine

# 2. Set the working directory
WORKDIR /app

# 3. Copy ONLY requirements first to leverage Docker cache
COPY requirements.txt .

# 4. Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# 5. Copy the rest of your application code
COPY . .

# 6. Expose the port FastAPI usually runs on (optional but helpful)
EXPOSE 8000

# 7. Set the entrypoint
ENTRYPOINT ["fastapi", "run", "main.py"]
