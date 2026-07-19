variable "project_id" {
  type        = string
  description = "GCP project ID to deploy into."
}

# Free tier note: an e2-micro instance is only free in us-west1, us-central1,
# and us-east1. Keep region/zone within one of these to stay at $0.
variable "region" {
  type        = string
  description = "GCP region. Must be us-west1, us-central1, or us-east1 for the always-free e2-micro."
  default     = "us-central1"
}

variable "zone" {
  type        = string
  description = "GCP zone within the free-tier region."
  default     = "us-central1-a"
}

variable "machine_type" {
  type        = string
  description = "Instance machine type. e2-micro is the always-free size."
  default     = "e2-micro"
}

variable "boot_disk_size_gb" {
  type        = number
  description = "Boot disk size in GB. Free tier includes up to 30GB of standard persistent disk."
  default     = 30
}

variable "instance_name" {
  type        = string
  description = "Name for the VM instance."
  default     = "missions-backend"
}

variable "ssh_user" {
  type        = string
  description = "Linux username created on the VM and granted docker + SSH access."
  default     = "deployer"
}

variable "ssh_public_key_path" {
  type        = string
  description = "Path to the SSH public key used to log into the VM."
  default     = "~/.ssh/id_rsa.pub"
}

variable "allowed_ssh_source_ranges" {
  type        = list(string)
  description = "CIDR ranges allowed to SSH (port 22). Tighten this to your IP for better security."
  default     = ["0.0.0.0/0"]
}

variable "git_repo_url" {
  type        = string
  description = "Optional git URL to clone into the app directory on first boot. Leave empty to clone manually."
  default     = ""
}

variable "app_dir" {
  type        = string
  description = "Directory on the VM where the repo lives / docker compose runs."
  default     = "/opt/missions/app"
}

variable "swap_size_mb" {
  type        = number
  description = "Swap file size in MB. Helps the 1GB e2-micro build the image and run Postgres+Redis without OOM."
  default     = 2048
}
