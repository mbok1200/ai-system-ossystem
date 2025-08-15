output "instance_public_ip" {
  description = "EC2 public IP"
  value       = aws_instance.gradio.public_ip
}

output "duckdns_domain" {
  description = "DuckDNS domain"
  value       = "${var.duckdns_subdomain}.duckdns.org"
}

output "https_url" {
  description = "Public HTTPS URL"
  value       = "https://${var.duckdns_subdomain}.duckdns.org"
}
