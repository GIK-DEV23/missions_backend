# ---------------------------------------------------------------------------
# Networking: a small dedicated VPC + firewall rules for SSH/HTTP/HTTPS.
# ---------------------------------------------------------------------------
resource "google_compute_network" "vpc" {
  name                    = "${var.instance_name}-net"
  auto_create_subnetworks = true
}

resource "google_compute_firewall" "ssh" {
  name    = "${var.instance_name}-allow-ssh"
  network = google_compute_network.vpc.id

  allow {
    protocol = "tcp"
    ports    = ["22"]
  }

  source_ranges = var.allowed_ssh_source_ranges
  target_tags   = ["missions"]
}

resource "google_compute_firewall" "web" {
  name    = "${var.instance_name}-allow-web"
  network = google_compute_network.vpc.id

  allow {
    protocol = "tcp"
    ports    = ["80", "443"]
  }

  source_ranges = ["0.0.0.0/0"]
  target_tags   = ["missions"]
}

# ---------------------------------------------------------------------------
# A static external IP so the address survives instance restarts.
# (Free while attached to a running instance.)
# ---------------------------------------------------------------------------
resource "google_compute_address" "static_ip" {
  name   = "${var.instance_name}-ip"
  region = var.region
}

# ---------------------------------------------------------------------------
# The always-free e2-micro VM. Boots Debian 12, sets up swap + Docker,
# and (optionally) clones the repo via the startup script.
# ---------------------------------------------------------------------------
resource "google_compute_instance" "vm" {
  name         = var.instance_name
  machine_type = var.machine_type
  zone         = var.zone
  tags         = ["missions"]

  boot_disk {
    initialize_params {
      image = "debian-cloud/debian-12"
      size  = var.boot_disk_size_gb
      type  = "pd-standard" # standard PD is the free-tier disk type
    }
  }

  network_interface {
    network = google_compute_network.vpc.id
    access_config {
      nat_ip = google_compute_address.static_ip.address
    }
  }

  metadata = {
    ssh-keys = "${var.ssh_user}:${trimspace(file(pathexpand(var.ssh_public_key_path)))}"
  }

  metadata_startup_script = templatefile("${path.module}/startup-script.sh", {
    ssh_user     = var.ssh_user
    app_dir      = var.app_dir
    git_repo_url = var.git_repo_url
    swap_size_mb = var.swap_size_mb
  })

  # e2-micro is a shared-core machine; allow it to be stopped/started cheaply.
  scheduling {
    automatic_restart   = true
    on_host_maintenance = "MIGRATE"
  }
}
