#!/usr/bin/env bash
set -euo pipefail

APP_DIR="/opt/algoritm-olimpiada"
APP_USER="${APP_USER:-ubuntu}"

sudo apt-get update
sudo apt-get install -y python3 python3-venv python3-pip git

sudo mkdir -p "$APP_DIR"
sudo chown -R "$APP_USER:$APP_USER" "$APP_DIR"

python3 -m venv "$APP_DIR/.venv"
"$APP_DIR/.venv/bin/pip" install --upgrade pip
"$APP_DIR/.venv/bin/pip" install -r "$APP_DIR/requirements.txt"

sudo cp "$APP_DIR/deploy/algoritm-olimpiada.service.example" /etc/systemd/system/algoritm-olimpiada.service
sudo sed -i "s/User=ubuntu/User=$APP_USER/" /etc/systemd/system/algoritm-olimpiada.service
sudo systemctl daemon-reload
sudo systemctl enable algoritm-olimpiada
sudo systemctl restart algoritm-olimpiada
sudo systemctl status algoritm-olimpiada --no-pager
