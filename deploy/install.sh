#!/usr/bin/env bash
set -euo pipefail

REPO="${MC_PANEL_GITHUB_REPO:-Vanillllla/mc-server-controller}"
BRANCH="${MC_PANEL_BRANCH:-WEB-gui-tg-server-controller}"
APP_DIR="${MC_PANEL_APP_DIR:-/opt/mc-server-controller}"
PANEL_HOME="${MC_PANEL_HOME:-/srv/mc-panel}"
SERVICE_NAME="${MC_PANEL_SERVICE_NAME:-mc-panel.service}"
SERVICE_USER="${MC_PANEL_SERVICE_USER:-mc-panel}"

apt-get update
apt-get install -y python3 python3-venv python3-pip git curl rsync openjdk-8-jre-headless openjdk-17-jre-headless

if ! id "$SERVICE_USER" >/dev/null 2>&1; then
  useradd --system --create-home --shell /usr/sbin/nologin "$SERVICE_USER"
fi

mkdir -p "$APP_DIR" "$PANEL_HOME" /opt/mc-server-controller-backups
if [[ ! -d "$APP_DIR/.git" ]]; then
  rm -rf "$APP_DIR"
  git clone --branch "$BRANCH" "https://github.com/${REPO}.git" "$APP_DIR"
else
  git -C "$APP_DIR" fetch origin "$BRANCH"
  git -C "$APP_DIR" checkout "$BRANCH"
  git -C "$APP_DIR" reset --hard "origin/$BRANCH"
fi

python3 -m venv "$APP_DIR/.venv"
"$APP_DIR/.venv/bin/pip" install --upgrade pip
"$APP_DIR/.venv/bin/pip" install -r "$APP_DIR/requirements.txt"

install -m 0755 "$APP_DIR/deploy/mc-panel-update" /usr/local/sbin/mc-panel-update
install -m 0644 "$APP_DIR/deploy/mc-panel.service" "/etc/systemd/system/$SERVICE_NAME"

chown -R "$SERVICE_USER:$SERVICE_USER" "$APP_DIR" "$PANEL_HOME" /opt/mc-server-controller-backups

systemctl daemon-reload
systemctl enable --now "$SERVICE_NAME"

echo "Installed. Check: systemctl status $SERVICE_NAME --no-pager"
