const state = {
  activeView: "dashboard",
  currentUser: null,
  publicLinks: null,
  servers: [],
  activeServer: null,
  workData: null,
  consoleItems: [],
  socket: null,
  filePath: "",
  fileItems: [],
  fileSearch: "",
  fileViewMode: "list",
  selectedFileItem: null,
  selectedFile: "",
  javaRuntimes: [],
  invite: null,
};

const defaultPublicLinks = {
  discord: {
    url: "https://discord.gg/cUt6nYVEyn",
    icon_path: "/assets/icons/discord.svg",
  },
};

const quickPropertyFields = [
  ["motd", "MOTD", "text"],
  ["server-port", "Port", "number"],
  ["max-players", "Max players", "number"],
  ["online-mode", "Online mode", "checkbox"],
  ["gamemode", "Gamemode", "select", ["survival", "creative", "adventure", "spectator"]],
  ["difficulty", "Difficulty", "select", ["peaceful", "easy", "normal", "hard"]],
  ["pvp", "PVP", "checkbox"],
  ["view-distance", "View distance", "number"],
  ["simulation-distance", "Simulation distance", "number"],
  ["enable-rcon", "RCON", "checkbox"],
];

const dangerousCommands = new Set([
  "stop",
  "op",
  "deop",
  "save-off",
  "reload",
  "ban",
  "pardon",
  "whitelist",
  "difficulty",
  "gamemode",
]);

const $ = (selector) => document.querySelector(selector);
const $$ = (selector) => [...document.querySelectorAll(selector)];

function hasPermission(permission) {
  return Boolean(state.currentUser?.permissions?.includes(permission));
}

function isAdmin() {
  return state.currentUser?.role === "admin";
}

function toast(message) {
  const node = $("#toast");
  node.textContent = message;
  node.classList.add("visible");
  window.setTimeout(() => node.classList.remove("visible"), 3200);
}

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

function inviteTokenFromPath() {
  const match = window.location.pathname.match(/^\/invite\/([^/]+)$/);
  return match ? decodeURIComponent(match[1]) : "";
}

function showLogin(message = "") {
  $("#auth-screen").hidden = false;
  $("#app-shell").hidden = true;
  $("#auth-message").textContent = message;
}

function showApp() {
  $("#auth-screen").hidden = true;
  $("#app-shell").hidden = false;
}

function clearSessionState(message = "") {
  if (state.socket) state.socket.close();
  state.socket = null;
  state.currentUser = null;
  state.servers = [];
  state.activeServer = null;
  state.workData = null;
  state.consoleItems = [];
  state.invite = null;
  showLogin(message);
}

async function loadCurrentUser() {
  const response = await api("/api/auth/me");
  state.currentUser = response.user;
}

async function loadPublicSettings() {
  try {
    const response = await api("/api/settings/public");
    state.publicLinks = { ...defaultPublicLinks, ...(response.links || {}) };
  } catch {
    state.publicLinks = defaultPublicLinks;
  }
  renderPublicLinks();
}

function renderPublicLinks() {
  const discord = state.publicLinks?.discord || defaultPublicLinks.discord;
  $$('[data-public-link="discord"]').forEach((link) => {
    link.href = discord.url || defaultPublicLinks.discord.url;
  });
  $$('[data-public-link-icon="discord"]').forEach((icon) => {
    icon.src = discord.icon_path || defaultPublicLinks.discord.icon_path;
  });
}

async function authenticateInviteIfPresent() {
  const token = inviteTokenFromPath();
  if (!token) return false;
  await api("/api/auth/invite-login", {
    method: "POST",
    body: JSON.stringify({ token }),
  });
  window.history.replaceState({}, "", "/");
  return true;
}

function applyAccessRules() {
  $$("[data-admin-only]").forEach((node) => {
    node.hidden = !isAdmin();
  });
  if (!isAdmin() && state.activeView !== "dashboard") {
    switchView("dashboard");
  }
}

function statusClass(status) {
  return `status-${String(status || "OFF").toLowerCase()}`;
}

function setStatusPill(node, status) {
  node.className = `pill ${statusClass(status)}`;
  node.textContent = status || "OFF";
}

function formatSeconds(value) {
  if (!value) return "0s";
  const seconds = Math.floor(value);
  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  const rest = seconds % 60;
  return hours ? `${hours}h ${minutes}m` : `${minutes}m ${rest}s`;
}

function formatBytes(size) {
  if (!Number.isFinite(size)) return "-";
  if (size < 1024) return `${size} B`;
  if (size < 1024 * 1024) return `${(size / 1024).toFixed(1)} KB`;
  return `${(size / 1024 / 1024).toFixed(1)} MB`;
}

function uploadForm(path, formData, onProgress) {
  return new Promise((resolve, reject) => {
    const request = new XMLHttpRequest();
    let latestProgress = { loaded: 0, total: null, percent: null };
    request.open("POST", path);
    request.withCredentials = true;
    request.upload.addEventListener("progress", (event) => {
      if (!event.lengthComputable) {
        latestProgress = { loaded: event.loaded, total: null, percent: null };
        onProgress?.(latestProgress);
        return;
      }
      latestProgress = {
        loaded: event.loaded,
        total: event.total,
        percent: Math.min(100, Math.round((event.loaded / event.total) * 100)),
      };
      onProgress?.(latestProgress);
    });
    request.upload.addEventListener("load", () => {
      onProgress?.({
        loaded: latestProgress.total || latestProgress.loaded,
        total: latestProgress.total,
        percent: 100,
      });
    });
    request.addEventListener("load", () => {
      if (request.status >= 200 && request.status < 300) {
        resolve(request.responseText ? JSON.parse(request.responseText) : null);
        return;
      }

      let detail = request.statusText;
      try {
        detail = JSON.parse(request.responseText).detail || detail;
      } catch {
        // Keep HTTP status text.
      }
      const error = new Error(detail);
      error.status = request.status;
      reject(error);
    });
    request.addEventListener("error", () => reject(new Error("upload_failed")));
    request.addEventListener("abort", () => reject(new Error("upload_aborted")));
    request.send(formData);
  });
}

function setUploadProgress(formNode, stateName, progress = {}) {
  const node = formNode.querySelector("[data-upload-progress]");
  if (!node) return;

  const status = node.querySelector("[data-upload-status]");
  const percent = node.querySelector("[data-upload-percent]");
  const size = node.querySelector("[data-upload-size]");
  const progressBar = node.querySelector("progress");
  const percentValue = Number.isFinite(progress.percent) ? progress.percent : 0;

  node.hidden = stateName === "hidden";
  if (stateName === "uploading") status.textContent = "Загрузка файла...";
  if (stateName === "processing") status.textContent = "Файл загружен, сервер обрабатывает данные...";
  if (stateName === "error") status.textContent = "Загрузка прервана";

  progressBar.value = stateName === "processing" ? 100 : percentValue;
  percent.textContent = stateName === "processing" ? "100%" : `${percentValue}%`;
  size.textContent = progress.total
    ? `${formatBytes(progress.loaded)} из ${formatBytes(progress.total)}`
    : progress.loaded
      ? `${formatBytes(progress.loaded)} загружено`
      : "";
}

function setFormBusy(formNode, busy) {
  formNode.querySelectorAll("input, select, button").forEach((node) => {
    node.disabled = busy;
  });
}

async function refreshAll() {
  const tasks = [refreshWorkData()];
  if (isAdmin()) {
    tasks.push(refreshServers(), refreshJavaRuntimes(), refreshInvite());
  }
  await Promise.all(tasks);
  if (!isAdmin()) {
    state.servers = [];
    state.activeServer = state.workData?.active_server || null;
    state.javaRuntimes = [];
  }
  applyAccessRules();
  renderHeader();
  renderDashboard();
  if (isAdmin()) {
    renderServers();
    renderJavaRuntimeSettings();
    renderJavaSelects();
    renderInviteSettings();
  }
}

async function refreshServers() {
  state.servers = await api("/api/servers");
  state.activeServer = await api("/api/servers/active");
}

async function refreshWorkData() {
  state.workData = await api("/api/servers/active/work-data");
}

async function refreshJavaRuntimes() {
  state.javaRuntimes = await api("/api/settings/java-runtimes");
}

async function refreshInvite() {
  state.invite = await api("/api/auth/invite");
}

function renderHeader() {
  const status = state.workData?.status || "OFF";
  $("#current-user-label").textContent = state.currentUser
    ? `${state.currentUser.username} · ${state.currentUser.role}`
    : "-";
  $("#active-server-label").textContent = state.activeServer?.display_name || "Не выбран";
  setStatusPill($("#server-status-pill"), status);
}

function metric(label, value) {
  return `<div class="metric"><span>${label}</span><strong>${value ?? "-"}</strong></div>`;
}

function renderDashboard() {
  const active = state.workData?.active_server || state.activeServer;
  const status = state.workData?.status || "OFF";
  $("#dashboard-server-name").textContent = active?.display_name || "Сервер не выбран";
  setStatusPill($("#dashboard-status"), status);
  $("#dashboard-summary").innerHTML = [
    metric("ID", active?.id || "-"),
    metric("Версия", active?.minecraft_version || "-"),
    metric("Тип", active?.server_type || "-"),
    metric("Uptime", formatSeconds(state.workData?.uptime_seconds)),
    metric("PID", state.workData?.pid || "-"),
    metric("Jar", active?.jar_file || "-"),
  ].join("");

  const metrics = state.workData?.metrics || {};
  const system = metrics.system || {};
  const proc = metrics.process || {};
  $("#metrics-grid").innerHTML = [
    metric("CPU VM", system.available ? `${system.cpu_percent}%` : "-"),
    metric("RAM VM", system.available ? `${system.ram_percent}%` : "-"),
    metric("RAM used", system.available ? `${system.ram_used_mb} MB` : "-"),
    metric("Java RAM", proc.is_running ? `${proc.ram_rss_mb} MB` : "-"),
    metric("Java CPU", proc.is_running ? `${proc.cpu_percent}%` : "-"),
    metric("Process", proc.is_running ? "RUNNING" : "OFF"),
  ].join("");

  const logs = state.workData?.recent_logs || [];
  $("#recent-logs").textContent = logs.map(formatLog).join("\n");

  const clientModsButton = $("#download-client-mods-btn");
  clientModsButton.hidden = !hasPermission("client_mods.download");
  clientModsButton.disabled = !active;
}

function renderServers() {
  const activeId = state.activeServer?.id;
  $("#servers-list").innerHTML =
    state.servers
      .map((server) => {
        const active = server.id === activeId;
        return `
          <article class="server-row">
            <div>
              <strong>${escapeHtml(server.display_name)}</strong>
              ${active ? '<span class="pill status-running">Активен</span>' : ""}
              <div class="server-meta">${escapeHtml(server.id)} · ${escapeHtml(server.server_type || "custom")} · ${escapeHtml(server.minecraft_version || "version?")} · ${escapeHtml(server.jar_file)}</div>
            </div>
            <div class="row-actions">
              <button class="btn small" data-action="activate" data-id="${escapeHtml(server.id)}" ${active ? "disabled" : ""}>Активировать</button>
              <button class="btn small" data-action="server-settings" data-id="${escapeHtml(server.id)}">Настройки сервера</button>
              <button class="btn small" data-action="game-settings" data-id="${escapeHtml(server.id)}">Настройки игры</button>
              <button class="btn small" data-action="files" data-id="${escapeHtml(server.id)}">Файлы</button>
              <button class="btn danger small" data-action="delete" data-id="${escapeHtml(server.id)}">Удалить</button>
            </div>
          </article>`;
      })
      .join("") || `<p class="server-meta">Серверы пока не созданы.</p>`;
}

function defaultJavaPath() {
  return state.javaRuntimes.find((runtime) => runtime.is_default)?.path || "java";
}

function renderJavaSelects() {
  const options = state.javaRuntimes
    .map((runtime) => {
      const label = runtime.is_default ? `${runtime.display_name} (default)` : runtime.display_name;
      return `<option value="${escapeHtml(runtime.path)}">${escapeHtml(label)}</option>`;
    })
    .join("");
  $$("[data-java-select]").forEach((select) => {
    const previous = select.value || defaultJavaPath();
    select.innerHTML = options || '<option value="java">System java from PATH</option>';
    select.value = state.javaRuntimes.some((runtime) => runtime.path === previous)
      ? previous
      : defaultJavaPath();
  });
}

function setJavaSelectValue(select, value) {
  if (!select) return;
  if (value && ![...select.options].some((option) => option.value === value)) {
    select.appendChild(new Option(value, value));
  }
  select.value = value || defaultJavaPath();
}

function showModal(id) {
  const modal = $(`#${id}`);
  if (!modal) return;
  modal.hidden = false;
  document.body.classList.add("modal-open");
}

function hideModal(id) {
  const modal = $(`#${id}`);
  if (!modal) return;
  modal.hidden = true;
  if (!$(".modal-backdrop:not([hidden])")) {
    document.body.classList.remove("modal-open");
  }
}

function openServerSettings(serverId) {
  const server = state.servers.find((candidate) => candidate.id === serverId);
  if (!server) return;

  const form = $("#server-settings-form");
  form.dataset.serverId = server.id;
  $("#server-settings-title").textContent = server.display_name;
  form.elements.id.value = server.id;
  form.elements.display_name.value = server.display_name || "";
  form.elements.jar_file.value = server.jar_file || "";
  form.elements.minecraft_version.value = server.minecraft_version || "";
  form.elements.server_type.value = server.server_type || "";
  form.elements.xms_mb.value = server.xms_mb || 512;
  form.elements.xmx_mb.value = server.xmx_mb || 1024;
  form.elements.eula_accept.checked = Boolean(server.eula_accept);
  setJavaSelectValue(form.elements.java_path, server.java_path || defaultJavaPath());
  showModal("server-settings-modal");
}

async function activateServerIfNeeded(serverId) {
  if (state.activeServer?.id === serverId) return;
  state.activeServer = await api(`/api/servers/${encodeURIComponent(serverId)}/activate`, { method: "POST" });
  await refreshAll();
}

function renderJavaRuntimeSettings() {
  const node = $("#java-runtime-list");
  if (!node) return;
  node.innerHTML =
    state.javaRuntimes
      .map(
        (runtime) => `
          <article class="server-row">
            <div>
              <strong>${escapeHtml(runtime.display_name)}</strong>
              ${runtime.is_default ? '<span class="pill status-running">Default</span>' : ""}
              <div class="server-meta">${escapeHtml(runtime.id)} · ${escapeHtml(runtime.path)}</div>
            </div>
            <div class="row-actions">
              <button class="btn small" data-java-action="default" data-id="${escapeHtml(runtime.id)}" ${runtime.is_default ? "disabled" : ""}>По умолчанию</button>
            </div>
          </article>`,
      )
      .join("") || '<p class="server-meta">Версии Java не настроены.</p>';
}

function renderInviteSettings() {
  const invite = state.invite || { active: false };
  setStatusPill($("#invite-status"), invite.active ? "RUNNING" : "OFF");
  $("#invite-status").textContent = invite.active ? "ACTIVE" : "OFF";
  $("#invite-link").value = invite.url || "";
  $("#revoke-invite-btn").disabled = !invite.active;
  $("#copy-invite-btn").disabled = !invite.active;
}

function formatLog(item) {
  const time = item.timestamp ? new Date(item.timestamp).toLocaleTimeString() : "";
  const stream = item.stream ? `[${item.stream}]` : "";
  return `${time} ${stream} ${item.line || ""}`.trim();
}

function renderConsole() {
  const filter = $("#log-filter").value;
  const lines = state.consoleItems
    .filter((item) => !filter || String(item.line || "").includes(filter))
    .map(formatLog);
  const node = $("#console-output");
  node.textContent = lines.join("\n");
  if ($("#autoscroll").checked) node.scrollTop = node.scrollHeight;
}

function connectConsole() {
  if (!hasPermission("console.view")) return;
  if (state.socket && state.socket.readyState < 2) return;
  const protocol = window.location.protocol === "https:" ? "wss" : "ws";
  state.socket = new WebSocket(`${protocol}://${window.location.host}/ws/servers/active/console`);
  state.socket.addEventListener("message", (event) => {
    const item = JSON.parse(event.data);
    state.consoleItems.push(item);
    state.consoleItems = state.consoleItems.slice(-1000);
    renderConsole();
  });
  state.socket.addEventListener("close", () => window.setTimeout(connectConsole, 2500));
}

async function serverCommand(action) {
  const result = await api(`/api/servers/active/${action}`, { method: "POST" });
  state.workData = { ...state.workData, ...result };
  await refreshAll();
}

async function loadProperties() {
  const data = await api("/api/servers/active/properties");
  $("#raw-properties").value = data.raw || "";
  renderPropertiesForm(data.values || {});
}

function renderPropertiesForm(values) {
  $("#properties-form").innerHTML = quickPropertyFields
    .map(([key, label, type, options]) => {
      const value = values[key] ?? "";
      if (type === "checkbox") {
        return `<label class="checkbox-row"><input name="${key}" type="checkbox" ${value === "true" ? "checked" : ""} /> ${label}</label>`;
      }
      if (type === "select") {
        return `<label>${label}<select name="${key}">${options.map((item) => `<option value="${item}" ${item === value ? "selected" : ""}>${item}</option>`).join("")}</select></label>`;
      }
      return `<label>${label}<input name="${key}" type="${type}" value="${escapeHtml(value)}" /></label>`;
    })
    .join("") + '<button class="btn primary" type="submit">Сохранить быстрые настройки</button>';
}

async function saveQuickProperties(event) {
  event.preventDefault();
  const form = new FormData(event.currentTarget);
  const values = {};
  for (const [key, , type] of quickPropertyFields) {
    if (type === "checkbox") {
      values[key] = event.currentTarget.elements[key].checked;
    } else {
      const value = String(form.get(key) || "").trim();
      if (value) values[key] = value;
    }
  }
  const data = await api("/api/servers/active/properties", {
    method: "PUT",
    body: JSON.stringify({ values }),
  });
  $("#raw-properties").value = data.raw || "";
  toast("server.properties сохранен");
}

async function loadFiles(path = state.filePath) {
  const data = await api(`/api/servers/active/files?path=${encodeURIComponent(path)}`);
  state.filePath = data.path || "";
  state.fileItems = data.items || [];
  state.selectedFileItem =
    state.fileItems.find((item) => item.path === state.selectedFileItem?.path) || null;
  renderFileBrowser();
}

async function openTextFile(path) {
  const data = await api(`/api/servers/active/files/text?path=${encodeURIComponent(path)}`);
  state.selectedFile = data.path;
  const item = state.fileItems.find((candidate) => candidate.path === data.path);
  if (item) {
    state.selectedFileItem = item;
    renderFileBrowser();
  }
  showFileEditor(data.path, data.content);
}

function showFileEditor(path, content) {
  $("#editor-title").textContent = path;
  $("#file-editor").value = content;
  $("#file-editor-modal").hidden = false;
  document.body.classList.add("modal-open");
  updateEditorHighlight();
  $("#file-editor").focus();
}

function closeFileEditor() {
  $("#file-editor-modal").hidden = true;
  document.body.classList.remove("modal-open");
}

function updateEditorHighlight() {
  const editor = $("#file-editor");
  const highlight = $("#file-editor-highlight");
  const mode = editorHighlightMode(state.selectedFile);
  const wrap = $("#file-editor-wrap");
  wrap.classList.toggle("json-mode", mode === "json");
  wrap.classList.toggle("properties-mode", mode === "properties");

  if (!mode) {
    highlight.innerHTML = "";
    return;
  }
  highlight.innerHTML =
    mode === "json" ? highlightJson(editor.value) : highlightProperties(editor.value);
  highlight.scrollTop = editor.scrollTop;
  highlight.scrollLeft = editor.scrollLeft;
}

function editorHighlightMode(path) {
  const lowerPath = (path || "").toLowerCase();
  if (lowerPath.endsWith(".json")) return "json";
  if (lowerPath.endsWith(".properties") || lowerPath.endsWith(".cfg")) return "properties";
  return "";
}

function highlightJson(value) {
  const tokenRe =
    /("(?:\\.|[^"\\])*"(?=\s*:))|("(?:\\.|[^"\\])*")|\b(true|false)\b|\b(null)\b|(-?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?)/g;
  let result = "";
  let lastIndex = 0;
  value.replace(tokenRe, (token, key, string, boolean, nil, number, offset) => {
    result += escapeHtml(value.slice(lastIndex, offset));
    lastIndex = offset + token.length;
    let className = "json-number";
    if (key) className = "json-key";
    if (string) className = "json-string";
    if (boolean) className = "json-boolean";
    if (nil) className = "json-null";
    if (number) className = "json-number";
    result += `<span class="${className}">${escapeHtml(token)}</span>`;
    return token;
  });
  result += escapeHtml(value.slice(lastIndex));
  return result || "\n";
}

function highlightProperties(value) {
  const lines = value.split(/(\r?\n)/);
  return lines
    .map((line) => {
      if (/^\r?\n$/.test(line)) return line;
      return highlightPropertyLine(line);
    })
    .join("") || "\n";
}

function highlightPropertyLine(line) {
  const trimmedLine = line.trimStart();
  if (!trimmedLine) return escapeHtml(line);
  if (trimmedLine.startsWith("#") || trimmedLine.startsWith(";")) {
    return `<span class="properties-comment">${escapeHtml(line)}</span>`;
  }
  if (/^\s*\[[^\]]+\]\s*$/.test(line)) {
    return `<span class="properties-section">${escapeHtml(line)}</span>`;
  }

  const separatorIndex = line.search(/[=:]/);
  if (separatorIndex === -1) {
    return `<span class="properties-key">${escapeHtml(line)}</span>`;
  }

  const key = line.slice(0, separatorIndex);
  const separator = line.slice(separatorIndex, separatorIndex + 1);
  const propertyValue = line.slice(separatorIndex + 1);
  return [
    `<span class="properties-key">${escapeHtml(key)}</span>`,
    `<span class="properties-separator">${escapeHtml(separator)}</span>`,
    `<span class="properties-value">${escapeHtml(propertyValue)}</span>`,
  ].join("");
}

function renderFileBrowser() {
  $("#files-path-title").textContent = state.filePath ? `/${state.filePath}` : "/";
  renderFileBreadcrumbs();
  renderFileRows();
  renderFileDetails();
  $$("[data-view-mode]").forEach((button) => {
    button.classList.toggle("active", button.dataset.viewMode === state.fileViewMode);
  });
}

function renderFileBreadcrumbs() {
  const parts = state.filePath ? state.filePath.split("/").filter(Boolean) : [];
  let current = "";
  const crumbs = [
    '<button class="breadcrumb-button" type="button" data-path="">Файлы</button>',
  ];
  for (const part of parts) {
    current = current ? `${current}/${part}` : part;
    crumbs.push(
      `<button class="breadcrumb-button" type="button" data-path="${escapeHtml(current)}">${escapeHtml(part)}</button>`,
    );
  }
  $("#files-breadcrumbs").innerHTML = crumbs.join('<span class="breadcrumb-separator">/</span>');
}

function renderFileRows() {
  const items = filteredFileItems();
  const list = $("#files-list");
  list.className = `file-list explorer-list ${state.fileViewMode}-mode`;
  $(".file-list-header").hidden = state.fileViewMode !== "list";

  if (!items.length) {
    list.innerHTML = '<div class="file-empty">В этой папке ничего не найдено.</div>';
    return;
  }

  list.innerHTML = items.map(renderFileRow).join("");
}

function renderFileRow(item) {
  const selected = state.selectedFileItem?.path === item.path;
  const iconClass = item.type === "directory" ? "folder" : "file";
  const coreTag = isServerCoreFile(item) ? '<span class="file-tag core">Ядро</span>' : "";
  return `
    <article class="file-row ${selected ? "selected" : ""}" data-file-row data-path="${escapeHtml(item.path)}" tabindex="0">
      <button class="file-name-cell" type="button" data-file-action="select" data-path="${escapeHtml(item.path)}">
        <span class="file-icon ${iconClass}" aria-hidden="true"></span>
        <span>
          <span class="file-title-line"><strong>${escapeHtml(item.name)}</strong>${coreTag}</span>
          <span class="file-meta mobile-only">${fileTypeLabel(item)} · ${formatBytes(item.size)}</span>
        </span>
      </button>
      <span class="file-type-col">${fileTypeLabel(item)}</span>
      <span class="file-size-col">${item.type === "directory" ? "-" : formatBytes(item.size)}</span>
      <span class="file-date-col">${formatFileDate(item.modified_at)}</span>
    </article>`;
}

function renderFileDetails() {
  const item = state.selectedFileItem;
  $("#file-details-name").textContent = item?.name || "Ничего не выбрано";
  $("#file-details-type").textContent = item ? fileTypeLabel(item) : "-";
  $("#file-details-size").textContent = item && item.type === "file" ? formatBytes(item.size) : "-";
  $("#file-details-path").textContent = item?.path || "-";
  $("#file-details-modified").textContent = item ? formatFileDate(item.modified_at) : "-";

  $("#file-details-open").hidden = item?.type !== "directory";
  $("#file-details-open").disabled = !item;
  $("#file-details-rename").disabled = !item;
  $("#file-details-delete").disabled = !item;
  $("#file-details-edit").hidden = !item?.editable;
  $("#file-details-download").hidden = item?.type !== "file";
  $("#file-details-download").href = item ? downloadUrl(item.path) : "#";
  $("#file-details-select-core").hidden = !isJarFile(item);
  $("#file-details-select-core").disabled = !isJarFile(item) || isServerCoreFile(item);
  $("#file-details-select-core").textContent = isServerCoreFile(item) ? "Текущее ядро" : "Выбрать ядро";
}

function filteredFileItems() {
  const query = state.fileSearch.trim().toLowerCase();
  const items = query
    ? state.fileItems.filter((item) => item.name.toLowerCase().includes(query))
    : state.fileItems;
  return [...items].sort((left, right) => {
    if (left.type !== right.type) return left.type === "directory" ? -1 : 1;
    return left.name.localeCompare(right.name, "ru", { sensitivity: "base" });
  });
}

function selectFileItem(path) {
  state.selectedFileItem = state.fileItems.find((item) => item.path === path) || null;
  $$("[data-file-row]").forEach((row) => {
    row.classList.toggle("selected", row.dataset.path === path);
  });
  renderFileDetails();
}

async function openFileItem(item) {
  if (!item) return;
  if (item.type === "directory") {
    await loadFiles(item.path);
    return;
  }
  if (item.editable) {
    await openTextFile(item.path);
  }
}

async function renameFileItem(item) {
  if (!item) return;
  const newName = prompt("Новое имя", item.name);
  if (!newName || newName === item.name) return;
  await api(`/api/servers/active/files?path=${encodeURIComponent(item.path)}`, {
    method: "PATCH",
    body: JSON.stringify({ new_name: newName }),
  });
  await loadFiles();
}

async function deleteFileItem(item) {
  if (!item || !confirm(`Удалить ${item.path}?`)) return;
  await api(`/api/servers/active/files?path=${encodeURIComponent(item.path)}`, { method: "DELETE" });
  if (state.selectedFileItem?.path === item.path) state.selectedFileItem = null;
  await loadFiles();
}

function selectedFileItem() {
  return state.selectedFileItem;
}

function fileItemByPath(path) {
  return state.fileItems.find((item) => item.path === path) || null;
}

function normalizeFilePath(path) {
  return String(path || "").replaceAll("\\", "/").toLowerCase();
}

function activeServerJarPath() {
  return normalizeFilePath(state.activeServer?.jar_file || state.workData?.active_server?.jar_file || "");
}

function isJarFile(item) {
  return item?.type === "file" && normalizeFilePath(item.path).endsWith(".jar");
}

function isServerCoreFile(item) {
  return isJarFile(item) && normalizeFilePath(item.path) === activeServerJarPath();
}

async function selectActiveServerCore(item) {
  if (!isJarFile(item)) return;
  const server = await api("/api/servers/active/jar", {
    method: "POST",
    body: JSON.stringify({ path: item.path }),
  });
  state.activeServer = server;
  state.servers = state.servers.map((candidate) => (candidate.id === server.id ? server : candidate));
  if (state.workData?.active_server?.id === server.id) {
    state.workData.active_server = server;
  }
  renderHeader();
  renderFileBrowser();
  toast("Ядро сервера выбрано");
}

function fileTypeLabel(item) {
  if (item.type === "directory") return "Папка";
  if (isJarFile(item)) return "JAR файл";
  return item.editable ? "Текстовый файл" : "Файл";
}

function formatFileDate(value) {
  if (!value) return "-";
  const date = new Date(Number(value) * 1000);
  if (Number.isNaN(date.getTime())) return "-";
  return date.toLocaleString();
}

function downloadUrl(path) {
  return `/api/servers/active/files/download?path=${encodeURIComponent(path)}`;
}

function joinFilePath(...parts) {
  return parts
    .join("/")
    .replaceAll("\\", "/")
    .split("/")
    .filter(Boolean)
    .join("/");
}

async function uploadFileToPath(file, path) {
  const form = new FormData();
  form.append("file", file);
  return api(`/api/servers/active/files/upload?path=${encodeURIComponent(path)}`, {
    method: "POST",
    body: form,
  });
}

async function ensureDirectoryPath(path) {
  const parts = path.split("/").filter(Boolean);
  let current = "";
  for (const part of parts) {
    const parent = current;
    current = joinFilePath(current, part);
    await api(`/api/servers/active/files/directories?path=${encodeURIComponent(parent)}`, {
      method: "POST",
      body: JSON.stringify({ name: part }),
    }).catch((error) => {
      const message = String(error.message || "");
      if (!message.includes("file_exists") && !message.includes("path_already_exists")) throw error;
    });
  }
}

async function uploadSelectedFiles(files) {
  const items = [...files];
  if (!items.length) return;
  toast(`Загрузка файлов: 0/${items.length}`);
  for (const [index, file] of items.entries()) {
    await uploadFileToPath(file, state.filePath);
    toast(`Загрузка файлов: ${index + 1}/${items.length}`);
  }
  await loadFiles();
  toast(`Загружено файлов: ${items.length}`);
}

async function uploadSelectedFolder(files) {
  const items = [...files].filter((file) => file.webkitRelativePath);
  if (!items.length) return;
  toast(`Загрузка папки: 0/${items.length}`);
  for (const [index, file] of items.entries()) {
    const relativeParts = file.webkitRelativePath.replaceAll("\\", "/").split("/").filter(Boolean);
    relativeParts.pop();
    const directory = joinFilePath(state.filePath, ...relativeParts);
    if (relativeParts.length) await ensureDirectoryPath(directory);
    await uploadFileToPath(file, directory || state.filePath);
    toast(`Загрузка папки: ${index + 1}/${items.length}`);
  }
  await loadFiles();
  toast(`Загружено файлов: ${items.length}`);
}

function downloadClientModsArchive() {
  const active = state.workData?.active_server || state.activeServer;
  if (!active) {
    toast("Активный сервер не выбран");
    return;
  }
  window.location.href = "/api/servers/active/client-mods/archive";
}

function switchView(view) {
  if (view !== "dashboard" && !isAdmin()) {
    view = "dashboard";
  }
  state.activeView = view;
  $$(".view").forEach((node) => node.classList.toggle("active", node.id === `view-${view}`));
  $$(".nav-item").forEach((node) => node.classList.toggle("active", node.dataset.view === view));
  $("#page-title").textContent = $(`.nav-item[data-view="${view}"]`)?.textContent || "Panel";
  if (view === "console") connectConsole();
  if (view === "properties") loadProperties().catch((error) => toast(error.message));
  if (view === "files") loadFiles().catch((error) => toast(error.message));
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

function normalizeServerForm(form, formNode, defaultType) {
  form.set("xms_mb", String(Number(form.get("xms_mb") || 512)));
  form.set("xmx_mb", String(Number(form.get("xmx_mb") || 1024)));
  form.set("eula_accept", formNode.elements.eula_accept.checked ? "true" : "false");
  form.set("server_type", String(form.get("server_type") || defaultType));
  form.set("java_path", String(form.get("java_path") || defaultJavaPath()));
}

function bindEvents() {
  $("#login-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    try {
      await api("/api/auth/login", {
        method: "POST",
        body: JSON.stringify(Object.fromEntries(form.entries())),
      });
    } catch (error) {
      showLogin(error.message);
      return;
    }

    event.currentTarget.reset();
    window.location.assign("/");
  });

  $("#logout-btn").addEventListener("click", async () => {
    await api("/api/auth/logout", { method: "POST" }).catch(() => null);
    clearSessionState("");
  });

  $$(".nav-item").forEach((button) => button.addEventListener("click", () => switchView(button.dataset.view)));
  $$("[data-view-jump]").forEach((button) => button.addEventListener("click", () => switchView(button.dataset.viewJump)));

  $("#start-btn").addEventListener("click", () => serverCommand("start").catch((error) => toast(error.message)));
  $("#download-client-mods-btn").addEventListener("click", downloadClientModsArchive);
  $("#stop-btn").addEventListener("click", () => serverCommand("stop").catch((error) => toast(error.message)));
  $("#restart-btn").addEventListener("click", () => serverCommand("restart").catch((error) => toast(error.message)));
  $("#kill-btn").addEventListener("click", () => {
    if (confirm("Принудительно завершить процесс сервера?")) {
      serverCommand("kill").catch((error) => toast(error.message));
    }
  });

  $("#toggle-add-server-btn").addEventListener("click", () => {
    const choices = $("#add-server-choices");
    choices.hidden = !choices.hidden;
  });
  $("#open-create-jar-modal-btn").addEventListener("click", () => {
    $("#add-server-choices").hidden = true;
    showModal("create-jar-modal");
  });
  $("#open-import-zip-modal-btn").addEventListener("click", () => {
    $("#add-server-choices").hidden = true;
    showModal("import-zip-modal");
  });
  $$("[data-close-modal]").forEach((button) => {
    button.addEventListener("click", () => hideModal(button.dataset.closeModal));
  });
  $$(".modal-backdrop").forEach((backdrop) => {
    backdrop.addEventListener("click", (event) => {
      if (event.target === backdrop) hideModal(backdrop.id);
    });
  });

  $("#create-server-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    const formNode = event.currentTarget;
    const form = new FormData(formNode);
    normalizeServerForm(form, formNode, "custom");
    setFormBusy(formNode, true);
    setUploadProgress(formNode, "uploading", { loaded: 0, total: form.get("core_file")?.size || 0, percent: 0 });
    try {
      await uploadForm("/api/servers/upload-core", form, (progress) => {
        setUploadProgress(formNode, progress.percent === 100 ? "processing" : "uploading", progress);
      });
      formNode.reset();
      await refreshAll();
      setUploadProgress(formNode, "hidden");
      hideModal("create-jar-modal");
      toast("Сервер создан");
    } catch (error) {
      setUploadProgress(formNode, "error");
      toast(error.message);
    } finally {
      setFormBusy(formNode, false);
    }
  });

  $("#import-server-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    const formNode = event.currentTarget;
    const form = new FormData(formNode);
    normalizeServerForm(form, formNode, "forge");
    setFormBusy(formNode, true);
    setUploadProgress(formNode, "uploading", { loaded: 0, total: form.get("archive_file")?.size || 0, percent: 0 });
    try {
      await uploadForm("/api/servers/import-archive", form, (progress) => {
        setUploadProgress(formNode, progress.percent === 100 ? "processing" : "uploading", progress);
      });
      formNode.reset();
      await refreshAll();
      setUploadProgress(formNode, "hidden");
      hideModal("import-zip-modal");
      toast("Сервер импортирован");
    } catch (error) {
      setUploadProgress(formNode, "error");
      toast(error.message);
    } finally {
      setFormBusy(formNode, false);
    }
  });

  $("#server-settings-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    const formNode = event.currentTarget;
    const id = formNode.dataset.serverId;
    if (!id) return;
    const payload = {
      display_name: String(formNode.elements.display_name.value || "").trim(),
      minecraft_version: String(formNode.elements.minecraft_version.value || "").trim(),
      server_type: String(formNode.elements.server_type.value || "").trim() || "custom",
      java_path: String(formNode.elements.java_path.value || "").trim() || defaultJavaPath(),
      xms_mb: Number(formNode.elements.xms_mb.value || 512),
      xmx_mb: Number(formNode.elements.xmx_mb.value || 1024),
      eula_accept: formNode.elements.eula_accept.checked,
    };
    try {
      const server = await api(`/api/servers/${encodeURIComponent(id)}`, {
        method: "PATCH",
        body: JSON.stringify(payload),
      });
      state.servers = state.servers.map((candidate) => (candidate.id === id ? server : candidate));
      if (state.activeServer?.id === id) state.activeServer = server;
      if (state.workData?.active_server?.id === id) state.workData.active_server = server;
      renderServers();
      renderHeader();
      renderDashboard();
      hideModal("server-settings-modal");
      toast("Настройки сервера сохранены");
    } catch (error) {
      toast(error.message);
    }
  });

  $("#reload-java-btn").addEventListener("click", () => {
    refreshJavaRuntimes()
      .then(() => {
        renderJavaRuntimeSettings();
        renderJavaSelects();
      })
      .catch((error) => toast(error.message));
  });

  $("#java-runtime-list").addEventListener("click", async (event) => {
    const button = event.target.closest("button");
    if (!button || button.dataset.javaAction !== "default") return;
    await api("/api/settings/java-runtimes/default", {
      method: "POST",
      body: JSON.stringify({ id: button.dataset.id }),
    });
    await refreshJavaRuntimes();
    renderJavaRuntimeSettings();
    renderJavaSelects();
  });

  $("#java-runtime-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const payload = Object.fromEntries(form.entries());
    payload.is_default = event.currentTarget.elements.is_default.checked;
    await api("/api/settings/java-runtimes", {
      method: "POST",
      body: JSON.stringify(payload),
    });
    event.currentTarget.reset();
    await refreshJavaRuntimes();
    renderJavaRuntimeSettings();
    renderJavaSelects();
    toast("Java добавлена");
  });

  $("#admin-password-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const currentPassword = String(form.get("current_password") || "");
    const newPassword = String(form.get("new_password") || "");
    const confirmPassword = String(form.get("confirm_password") || "");
    if (newPassword !== confirmPassword) {
      toast("Новые пароли не совпадают");
      return;
    }
    try {
      await api("/api/auth/admin/password", {
        method: "POST",
        body: JSON.stringify({
          current_password: currentPassword,
          new_password: newPassword,
        }),
      });
      event.currentTarget.reset();
      toast("Пароль администратора изменён");
    } catch (error) {
      toast(error.message);
    }
  });

  $("#create-invite-btn").addEventListener("click", async () => {
    state.invite = await api("/api/auth/invite", { method: "POST" });
    renderInviteSettings();
    toast("Invite-ссылка создана");
  });

  $("#revoke-invite-btn").addEventListener("click", async () => {
    state.invite = await api("/api/auth/invite", { method: "DELETE" });
    renderInviteSettings();
    toast("Invite-ссылка закрыта");
  });

  $("#copy-invite-btn").addEventListener("click", async () => {
    const link = $("#invite-link").value;
    if (!link) return;
    await navigator.clipboard.writeText(link);
    toast("Ссылка скопирована");
  });

  $("#servers-list").addEventListener("click", async (event) => {
    const button = event.target.closest("button");
    if (!button) return;
    const id = button.dataset.id;
    try {
      if (button.dataset.action === "activate") {
        await api(`/api/servers/${encodeURIComponent(id)}/activate`, { method: "POST" });
        await refreshAll();
      }
      if (button.dataset.action === "delete" && confirm(`Удалить сервер ${id} и его файлы?`)) {
        await api(`/api/servers/${encodeURIComponent(id)}?delete_files=true`, { method: "DELETE" });
        await refreshAll();
      }
      if (button.dataset.action === "server-settings") openServerSettings(id);
      if (button.dataset.action === "game-settings") {
        await activateServerIfNeeded(id);
        switchView("properties");
      }
      if (button.dataset.action === "files") {
        await activateServerIfNeeded(id);
        switchView("files");
      }
    } catch (error) {
      toast(error.message);
    }
  });

  $("#console-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    const input = $("#console-command");
    const command = input.value.trim();
    if (!command) return;
    const firstWord = command.split(/\s+/)[0].toLowerCase();
    if (dangerousCommands.has(firstWord) && !confirm(`Команда "${firstWord}" может изменить состояние сервера. Отправить?`)) return;
    if (state.socket && state.socket.readyState === WebSocket.OPEN) {
      state.socket.send(JSON.stringify({ type: "command", command }));
    } else {
      await api("/api/servers/active/console/command", {
        method: "POST",
        body: JSON.stringify({ command }),
      });
    }
    input.value = "";
  });
  $("#clear-console-btn").addEventListener("click", () => {
    state.consoleItems = [];
    renderConsole();
  });
  $("#log-filter").addEventListener("change", renderConsole);

  $("#reload-properties-btn").addEventListener("click", () => loadProperties().catch((error) => toast(error.message)));
  $("#properties-form").addEventListener("submit", (event) => saveQuickProperties(event).catch((error) => toast(error.message)));
  $("#save-raw-properties-btn").addEventListener("click", async () => {
    await api("/api/servers/active/properties", {
      method: "PUT",
      body: JSON.stringify({ raw: $("#raw-properties").value }),
    });
    await loadProperties();
    toast("Raw server.properties сохранен");
  });

  $("#files-list").addEventListener("click", async (event) => {
    const action = event.target.closest("[data-file-action]");
    if (action) {
      if (action.dataset.fileAction === "select") selectFileItem(action.dataset.path);
      return;
    }

    const row = event.target.closest("[data-file-row]");
    if (row) selectFileItem(row.dataset.path);
  });
  $("#files-list").addEventListener("dblclick", async (event) => {
    const row = event.target.closest("[data-file-row]");
    if (!row) return;
    await openFileItem(fileItemByPath(row.dataset.path));
  });
  $("#files-list").addEventListener("keydown", async (event) => {
    if (event.key !== "Enter") return;
    const row = event.target.closest("[data-file-row]");
    if (!row) return;
    await openFileItem(fileItemByPath(row.dataset.path));
  });
  $("#files-breadcrumbs").addEventListener("click", (event) => {
    const button = event.target.closest("[data-path]");
    if (button) loadFiles(button.dataset.path).catch((error) => toast(error.message));
  });
  $("#files-refresh-btn").addEventListener("click", () => {
    loadFiles().catch((error) => toast(error.message));
  });
  $("#client-mods-folder-btn").addEventListener("click", async () => {
    await api("/api/servers/active/client-mods/ensure", { method: "POST" });
    await loadFiles("client-mods");
  });
  $("#files-search").addEventListener("input", (event) => {
    state.fileSearch = event.target.value;
    renderFileBrowser();
  });
  $$("[data-view-mode]").forEach((button) => {
    button.addEventListener("click", () => {
      state.fileViewMode = button.dataset.viewMode;
      renderFileBrowser();
    });
  });
  $("#file-details-open").addEventListener("click", () => {
    openFileItem(selectedFileItem()).catch((error) => toast(error.message));
  });
  $("#file-details-edit").addEventListener("click", () => {
    const item = selectedFileItem();
    if (item) openTextFile(item.path).catch((error) => toast(error.message));
  });
  $("#file-details-rename").addEventListener("click", () => {
    renameFileItem(selectedFileItem()).catch((error) => toast(error.message));
  });
  $("#file-details-delete").addEventListener("click", () => {
    deleteFileItem(selectedFileItem()).catch((error) => toast(error.message));
  });
  $("#file-details-select-core").addEventListener("click", () => {
    selectActiveServerCore(selectedFileItem()).catch((error) => toast(error.message));
  });
  $("#files-up-btn").addEventListener("click", () => {
    if (!state.filePath) return;
    const parent = state.filePath.split("/").slice(0, -1).join("/");
    loadFiles(parent).catch((error) => toast(error.message));
  });
  $("#mkdir-btn").addEventListener("click", async () => {
    const name = prompt("Имя папки");
    if (!name) return;
    await api(`/api/servers/active/files/directories?path=${encodeURIComponent(state.filePath)}`, {
      method: "POST",
      body: JSON.stringify({ name }),
    });
    await loadFiles();
  });
  $("#upload-input").addEventListener("change", async (event) => {
    try {
      await uploadSelectedFiles(event.target.files);
    } catch (error) {
      toast(error.message);
    } finally {
      event.target.value = "";
    }
  });
  $("#folder-upload-input").addEventListener("change", async (event) => {
    try {
      await uploadSelectedFolder(event.target.files);
    } catch (error) {
      toast(error.message);
    } finally {
      event.target.value = "";
    }
  });
  $("#close-file-editor-btn").addEventListener("click", closeFileEditor);
  $("#cancel-file-editor-btn").addEventListener("click", closeFileEditor);
  $("#file-editor-modal").addEventListener("click", (event) => {
    if (event.target.id === "file-editor-modal") closeFileEditor();
  });
  $("#file-editor").addEventListener("input", updateEditorHighlight);
  $("#file-editor").addEventListener("scroll", updateEditorHighlight);
  window.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && !$("#file-editor-modal").hidden) closeFileEditor();
  });
  $("#save-file-btn").addEventListener("click", async () => {
    if (!state.selectedFile) return toast("Файл не выбран");
    await api(`/api/servers/active/files/text?path=${encodeURIComponent(state.selectedFile)}`, {
      method: "PUT",
      body: JSON.stringify({ content: $("#file-editor").value }),
    });
    await loadFiles();
    toast("Файл сохранен");
  });
}

async function boot() {
  const inviteMode = Boolean(inviteTokenFromPath());
  await loadPublicSettings();
  try {
    await authenticateInviteIfPresent();
    await loadCurrentUser();
    showApp();
    await refreshAll();
    if (hasPermission("console.view")) connectConsole();
  } catch (error) {
    if (inviteMode) window.history.replaceState({}, "", "/");
    showLogin(inviteMode ? "Ссылка доступа закрыта или недействительна." : "");
  }
}

bindEvents();
boot();
window.setInterval(() => {
  if (state.currentUser) {
    refreshAll().catch((error) => {
      if (error.status === 401) clearSessionState("Сессия завершена.");
    });
  }
}, 3000);
