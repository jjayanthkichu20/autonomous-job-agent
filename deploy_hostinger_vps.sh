#!/usr/bin/env bash
# Turnkey Hostinger VPS Deployment Script for Autonomous Job Application Platform
set -euo pipefail

echo "=========================================================="
echo " Starting Hostinger VPS Deployment for Autonomous Job App "
echo "=========================================================="

APP_DIR="/var/www/autonomous-job-agent"
SERVICE_NAME="autonomous-job-platform"

# 1. Update OS and install prerequisites
echo "--> Updating system packages..."
apt-get update -y && apt-get install -y python3 python3-pip python3-venv git nginx curl ufw

# 2. Setup project directory
mkdir -p "$APP_DIR"
cd "$APP_DIR"

# 3. Create virtual environment
echo "--> Setting up Python virtual environment..."
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# 4. Create persistent storage directories
mkdir -p storage/artifacts
chmod -R 755 storage

# 5. Configure systemd service
echo "--> Setting up systemd service..."
cat <<EOF > /etc/systemd/system/${SERVICE_NAME}.service
[Unit]
Description=Autonomous Job Application Platform
After=network.target

[Service]
User=root
WorkingDirectory=${APP_DIR}
Environment="PATH=${APP_DIR}/.venv/bin"
Environment="PYTHONPATH=${APP_DIR}"
ExecStart=${APP_DIR}/.venv/bin/uvicorn autonomous_job_agent.web.app:app --host 127.0.0.1 --port 8000 --workers 2
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable ${SERVICE_NAME}
systemctl restart ${SERVICE_NAME}

# 6. Configure Nginx Reverse Proxy
echo "--> Configuring Nginx reverse proxy..."
cat <<EOF > /etc/nginx/sites-available/${SERVICE_NAME}
server {
    listen 80;
    server_name _;

    client_max_body_size 50M;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_read_timeout 120s;
    }
}
EOF

ln -sf /etc/nginx/sites-available/${SERVICE_NAME} /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default
nginx -t
systemctl restart nginx

echo "=========================================================="
echo " Deployment Complete! Platform is now LIVE on Port 80! "
echo " Check health: curl http://localhost/api/health            "
echo "=========================================================="
