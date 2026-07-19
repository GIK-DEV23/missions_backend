#!/usr/bin/env bash
# Runs once on first boot as root (GCE startup-script).
# Sets up swap, installs Docker + compose, and prepares the app directory.
set -euxo pipefail

# --- Swap: the e2-micro only has ~1GB RAM. Swap prevents OOM during the image
#     build (pandas/pillow compile) and while Postgres + Redis run alongside. ---
if [ ! -f /swapfile ]; then
  fallocate -l ${swap_size_mb}M /swapfile || dd if=/dev/zero of=/swapfile bs=1M count=${swap_size_mb}
  chmod 600 /swapfile
  mkswap /swapfile
  swapon /swapfile
  echo '/swapfile none swap sw 0 0' >> /etc/fstab
fi

# --- Docker Engine + compose plugin ---
export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y ca-certificates curl git

install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/debian/gpg -o /etc/apt/keyrings/docker.asc
chmod a+r /etc/apt/keyrings/docker.asc

echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/debian \
  $(. /etc/os-release && echo "$${VERSION_CODENAME}") stable" \
  > /etc/apt/sources.list.d/docker.list

apt-get update
apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

systemctl enable docker
systemctl start docker

# --- Let the deploy user run docker without sudo ---
usermod -aG docker ${ssh_user} || true

# --- App directory (owned by the deploy user) ---
mkdir -p ${app_dir}
chown -R ${ssh_user}:${ssh_user} $(dirname ${app_dir})

# --- Optionally clone the repo on first boot ---
if [ -n "${git_repo_url}" ] && [ ! -d "${app_dir}/.git" ]; then
  sudo -u ${ssh_user} git clone ${git_repo_url} ${app_dir} || true
fi

echo "startup-script complete"
