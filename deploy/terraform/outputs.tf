output "instance_ip" {
  description = "Public static IP of the VM. Point your DNS / GitHub Actions HOST secret here."
  value       = google_compute_address.static_ip.address
}

output "ssh_command" {
  description = "Ready-to-use SSH command."
  value       = "ssh ${var.ssh_user}@${google_compute_address.static_ip.address}"
}

output "app_dir" {
  description = "Directory on the VM where docker compose runs."
  value       = var.app_dir
}

output "app_url" {
  description = "HTTP URL once containers are up (nginx listens on port 80)."
  value       = "http://${google_compute_address.static_ip.address}/"
}
