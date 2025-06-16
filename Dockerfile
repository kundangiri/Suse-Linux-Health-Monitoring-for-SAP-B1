FROM debian:bookworm

# Install system dependencies
RUN apt update && apt install -y python3 python3-pip python3-venv gcc libpam0g-dev

WORKDIR /app

COPY . .

# Create virtual environment
RUN python3 -m venv /opt/venv

# Install dependencies into venv
RUN /opt/venv/bin/pip install --no-cache-dir python-pam && \
    /opt/venv/bin/pip install --no-cache-dir -r requirements.txt

# Activate venv by default
ENV PATH="/opt/venv/bin:$PATH"

# Run the script
CMD ["python3", "monitor.py"]
