
terraform {
  required_version = ">= 1.5.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = ">= 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

data "aws_vpc" "default" { 
  default = true 
}

data "aws_subnets" "default" {
  filter { 
    name = "vpc-id" 
    values = [data.aws_vpc.default.id] 
  }
}

# Ubuntu 22.04 (Jammy) by Canonical
data "aws_ami" "ubuntu_2204" {
  most_recent = true
  owners      = ["099720109477"]
  filter { 
    name = "name" 
    values = ["ubuntu/images/hvm-ssd/ubuntu-jammy-22.04-amd64-server-*"] 
  }
  filter { 
    name = "virtualization-type" 
    values = ["hvm"] 
  }
}

# SSH key
resource "aws_key_pair" "this" {
  key_name   = var.key_pair_name
  public_key = var.public_key
}

# Allow SSH + HTTP/HTTPS only (Gradio runs behind Nginx on 127.0.0.1:7860)
resource "aws_security_group" "web_sg" {
  name        = "gradio-web-sg"
  description = "Allow SSH, HTTP, HTTPS"
  vpc_id      = data.aws_vpc.default.id

  ingress { 
    from_port = 22
    to_port = 22
    protocol = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
  ingress { 
    from_port = 80
    to_port = 80
    protocol = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
  ingress { 
    from_port = 443
    to_port = 443
    protocol = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress  { 
    from_port = 0
    to_port = 0
    protocol = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

locals {
  domain = "${var.duckdns_subdomain}.duckdns.org"

  user_data = <<-EOF
    #!/usr/bin/env bash
    set -euxo pipefail
    export DEBIAN_FRONTEND=noninteractive

    # --- Base packages ---
    apt-get update -y
    apt-get upgrade -y
    apt-get install -y python3 python3-venv python3-pip git nginx python3-certbot-nginx cron curl dnsutils

    # --- Discover public IP ---
    META_URL=169.254.169.254
    PUB_IP=$(curl -s http://$META_URL/latest/meta-data/public-ipv4 || true)

    # --- DuckDNS updater (systemd service + timer) ---
    mkdir -p /opt/duckdns
    cat > /opt/duckdns/update.sh <<'SH'
#!/usr/bin/env bash
set -euo pipefail
DOMAIN="${var.duckdns_subdomain}"
TOKEN="${var.duckdns_token}"
URL="https://www.duckdns.org/update?domains=$DOMAIN&token=$TOKEN&ip="
curl -fsS "$URL" | tee -a /var/log/duckdns.log
SH
    chmod +x /opt/duckdns/update.sh

    cat > /etc/systemd/system/duckdns.service <<'UNIT'
[Unit]
Description=DuckDNS updater
After=network-online.target
Wants=network-online.target

[Service]
Type=oneshot
ExecStart=/opt/duckdns/update.sh

[Install]
WantedBy=multi-user.target
UNIT

    cat > /etc/systemd/system/duckdns.timer <<'UNIT'
[Unit]
Description=Run DuckDNS updater every 5 minutes

[Timer]
OnBootSec=30s
OnUnitActiveSec=5min
Unit=duckdns.service

[Install]
WantedBy=timers.target
UNIT

    systemctl daemon-reload
    systemctl enable --now duckdns.timer

    # Run once immediately to set DNS
    systemctl start duckdns.service || true

    # --- App setup ---
    APP_DIR=/opt/app
    mkdir -p "$APP_DIR"
    cd "$APP_DIR"
    python3 -m venv venv
    source venv/bin/activate
    pip install --upgrade pip

    if [ -n "${var.git_repo}" ]; then
      # Deploy user's repo
      git init .
      git remote add origin ${var.git_repo}
      git fetch --depth=1 origin ${var.git_branch}
      git checkout -b ${var.git_branch} origin/${var.git_branch}
      if [ -f requirements.txt ]; then pip install -r requirements.txt; else pip install gradio; fi
      APP_ENTRY=${var.app_entry}
      if [ ! -f "$APP_ENTRY" ]; then echo "ERROR: app entry ${var.app_entry} not found"; exit 1; fi
    else
      # Minimal demo
      pip install gradio
      cat > app.py <<'PY'
import gradio as gr
import os

def greet(name):
    return f"Привіт, {name}!"

port = int(os.environ.get("PORT", 7860))
demo = gr.Interface(fn=greet, inputs="text", outputs="text")
demo.launch(server_name="127.0.0.1", server_port=port)
PY
      APP_ENTRY=app.py
    fi

    # --- systemd service for Gradio ---
    cat > /etc/systemd/system/gradio.service <<UNIT
[Unit]
Description=Gradio App
After=network.target

[Service]
User=ubuntu
WorkingDirectory=$APP_DIR
Environment=PORT=7860
ExecStart=$APP_DIR/venv/bin/python $APP_ENTRY
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
UNIT

    systemctl daemon-reload
    systemctl enable --now gradio.service

    # --- Nginx reverse proxy ---
    cat > /etc/nginx/sites-available/gradio <<NGINX
server {
    listen 80;
    server_name ${local.domain};

    location / {
        proxy_pass http://127.0.0.1:7860/;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
NGINX

    rm -f /etc/nginx/sites-enabled/default || true
    ln -sf /etc/nginx/sites-available/gradio /etc/nginx/sites-enabled/gradio
    nginx -t
    systemctl enable --now nginx

    # --- Wait until DuckDNS resolves to our public IP ---
    echo "Waiting for DNS ${local.domain} -> $PUB_IP"
    ATTEMPTS=0
    until [ $ATTEMPTS -ge 30 ]; do
      RESOLVED=$(dig +short ${local.domain} | tail -n1 || true)
      if [ "$RESOLVED" = "$PUB_IP" ]; then echo "DNS OK: $RESOLVED"; break; fi
      ATTEMPTS=$((ATTEMPTS+1))
      sleep 10
    done

    # --- Obtain/enable HTTPS with Certbot (HTTP-01 via Nginx) ---
    certbot --nginx -d ${local.domain} --redirect -m ${var.admin_email} --agree-tos --non-interactive --no-eff-email || true

    # Enable auto-renewal (already via systemd timer, but ensure cron too)
    echo "0 3 * * * root certbot renew --quiet" > /etc/cron.d/certbot_renew
  EOF
}

resource "aws_instance" "gradio" {
  ami                    = data.aws_ami.ubuntu_2204.id
  instance_type          = var.instance_type
  subnet_id              = data.aws_subnets.default.ids[0]
  vpc_security_group_ids = [aws_security_group.web_sg.id]
  key_name               = aws_key_pair.this.key_name

  user_data = local.user_data

  root_block_device {
    volume_size           = var.root_volume_gb
    volume_type           = "gp3"
    delete_on_termination = true
  }

  tags = { Name = "gradio-https-duckdns" }
}