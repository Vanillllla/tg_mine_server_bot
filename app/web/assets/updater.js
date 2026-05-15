const updaterState = {
  latest: null,
};

const $ = (selector) => document.querySelector(selector);

async function api(path, options = {}) {
  const response = await fetch(path, {
    credentials: "same-origin",
    headers: options.body instanceof FormData ? undefined : { "Content-Type": "application/json" },
    ...options,
  });
  if (!response.ok) {
    let detail = response.statusText;
    try {
      const body = await response.json();
      detail = body.detail || detail;
    } catch {
      // Keep HTTP status text.
    }
    const error = new Error(detail);
    error.status = response.status;
    throw error;
  }
  if (response.status === 204) return null;
  return response.json();
}

function toast(message) {
  const node = $("#toast");
  if (!node) return alert(message);
  node.textContent = message;
  node.classList.add("visible");
  window.setTimeout(() => node.classList.remove("visible"), 3200);
}

function createUpdaterPanel() {
  const settingsView = $("#view-settings");
  if (!settingsView || $("#updater-panel")) return;

  const panel = document.createElement("section");
  panel.id = "updater-panel";
  panel.className = "panel";
  panel.setAttribute("data-admin-only", "");
  panel.innerHTML = `
    <div class="panel-heading">
      <div>
        <p class="eyebrow">GitHub Release</p>
        <h2>Обновление панели</h2>
      </div>
      <div class="toolbar">
        <button id="check-update-btn" class="btn small" type="button">Проверить</button>
        <button id="apply-update-btn" class="btn primary small" type="button" disabled>Обновить</button>
      </div>
    </div>
    <div id="update-status" class="server-meta">Проверка обновлений ещё не выполнялась.</div>
  `;
  settingsView.appendChild(panel);

  $("#check-update-btn").addEventListener("click", checkUpdates);
  $("#apply-update-btn").addEventListener("click", applyUpdate);
}

function renderUpdateStatus(data) {
  updaterState.latest = data;
  const node = $("#update-status");
  const button = $("#apply-update-btn");
  if (!node || !button) return;

  if (!data.update_available) {
    node.textContent = `Установлена актуальная версия: ${data.current_version}.`;
    button.disabled = true;
    return;
  }

  node.innerHTML = `Доступно обновление: <strong>${escapeHtml(data.current_version)}</strong> → <strong>${escapeHtml(data.latest_version)}</strong>. Перед обновлением останови Minecraft-сервер.`;
  button.disabled = false;
}

async function checkUpdates() {
  try {
    const data = await api("/api/updater/check");
    renderUpdateStatus(data);
    toast(data.update_available ? "Обновление найдено" : "Обновлений нет");
  } catch (error) {
    toast(error.message);
  }
}

async function applyUpdate() {
  const latest = updaterState.latest;
  if (!latest?.update_available) return;
  const confirmed = confirm(`Обновить панель до ${latest.latest_version}? Minecraft-сервер должен быть остановлен. После запуска обновления сервис перезапустится.`);
  if (!confirmed) return;

  try {
    const data = await api("/api/updater/apply", { method: "POST" });
    if (!data.accepted) {
      renderUpdateStatus(data);
      toast(data.reason || "Обновление не требуется");
      return;
    }
    toast("Обновление запущено. Страница может временно отключиться.");
    $("#apply-update-btn").disabled = true;
  } catch (error) {
    toast(error.message);
  }
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

function bootWhenReady() {
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", createUpdaterPanel);
    return;
  }
  createUpdaterPanel();
}

bootWhenReady();
