variable "aws_region" { 
    description = "AWS region" 
    type = string 
    default = "eu-central-1" 
}
variable "instance_type" { 
    description = "Free-tier instance type" 
    type = string 
    default = "t2.micro" 
}
variable "root_volume_gb" { 
    description = "Root volume size (<=30GB for Free Tier)" 
    type = number 
    default = 20 
}

variable "key_pair_name" { 
    description = "EC2 key pair name" 
    type = string 
    default = "gradio-key" 
}
variable "public_key" { 
    description = "SSH public key contents" 
    type = string 
}

# DuckDNS settings
variable "duckdns_subdomain" { 
    description = "Your DuckDNS subdomain (without .duckdns.org)" 
    type = string 
}
variable "duckdns_token" { 
    description = "DuckDNS token" 
    type = string 
    sensitive = true 
}

# Certbot email
variable "admin_email" { 
    description = "Email for Let's Encrypt TOS and expiry notices" 
    type = string 
}

# (Optional) Deploy from your Git repo
variable "git_repo" { 
    description = "Git repository URL (leave empty to use demo app)" 
    type = string 
    default = "" 
}
variable "git_branch" { 
    description = "Git branch to deploy" 
    type = string 
    default = "main" 
}
variable "app_entry" { 
    description = "Path to your app entry (e.g., app.py)" 
    type = string 
    default = "app.py" 
}