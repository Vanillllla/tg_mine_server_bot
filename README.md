# Minecraft Web Panel / Minecraft Server Controller

A web control panel for managing Minecraft server instances from a browser.  
The project is built around a FastAPI backend, a static Web UI, process-level Minecraft server control, a WebSocket console, JSON-based local storage, and a permission-based access model.

> Current project status: **beta / active development**.  
> The Telegram section exists in the interface and backend planning, but the current repository state mainly implements the Web UI and backend API.

---

## English README

### Overview

**Minecraft Web Panel** is a self-hosted panel for running and administering Minecraft servers on a local machine, VPS, or Linux VM.

It is designed for cases where you want to:

- start, stop, restart, or force-kill an active Minecraft server;
- manage several Minecraft server instances from one panel;
- upload a server core as a `.jar` file;
- import a ready server assembly from a `.zip` archive;
- configure Java path, Minecraft version, server type, Xms/Xmx memory, JVM arguments, and server arguments;
- view server status, uptime, PID, exit code, recent logs, and system/process metrics;
- use a live WebSocket console to read logs and send commands;
- edit `server.properties` through a quick editor or raw editor;
- browse, upload, download, rename, delete, and edit files inside the active server directory;
- prepare a `client-mods` folder and download it as a `.zip` archive;
- provide limited invite access for regular users;
- keep the backend, Web UI, and future Telegram bot integration behind one control API.

---

### Main features

#### Server instance management

- Create server instances from:
  - a single uploaded `.jar` core;
  - a `.zip` archive containing a ready server folder.
- Store each server instance under the configured panel runtime directory.
- Activate one server instance at a time.
- Prevent switching the active server while it is running.
- Delete server instances with optional file deletion.
- Validate server IDs as safe slugs.
- Automatically write `eula.txt` when EULA acceptance is enabled.

#### Server process control

The panel can control the active Minecraft server process:

- start;
- stop using the standard `stop` command through stdin;
- restart;
- force kill;
- send console commands through stdin;
- track process PID;
- track uptime;
- track exit code;
- detect startup state from server logs;
- store startup errors;
- shut the process down when the backend exits.

The default `jar` launch mode is assembled from the selected server settings:

```text
<java_path> -Xms<XMS>M -Xmx<XMX>M <jvm_args> -jar <server.jar> <server_args>
```

Forge 1.17+ servers can use the `forge_args` launch mode instead of `-jar`.
In this mode the active launch target is the Forge args file inside the server
folder, for example:

```text
libraries/net/minecraftforge/forge/1.20.1-47.x.x/win_args.txt
```

The resulting command is:

```text
<java_path> -Xms<XMS>M -Xmx<XMX>M <jvm_args> @user_jvm_args.txt @libraries/net/minecraftforge/forge/<version>/win_args.txt <server_args>
```

On Linux/macOS the target is `unix_args.txt` instead of `win_args.txt`.
Minecraft 1.20.1 requires Java 17.

Default JVM/server arguments:

```text
-Dfile.encoding=UTF-8
nogui
```

#### Dashboard and metrics

The dashboard shows:

- active server name;
- server status;
- start/stop/restart/kill controls;
- system CPU usage;
- system RAM usage;
- Java/Minecraft process memory usage;
- recent logs.

Metrics are collected with `psutil`.

#### WebSocket console

The Web UI includes a live console connected through:

```text
/ws/servers/active/console
```

The console supports:

- recent log replay on connection;
- live log streaming;
- command sending;
- permission checks;
- log filtering in the UI;
- autoscroll control;
- clear console button.

#### `server.properties` editor

The panel supports both:

- quick editing of selected common properties;
- raw editing of the full `server.properties` file.

Supported validation currently includes common boolean, integer, and enum properties, for example:

- `online-mode`;
- `pvp`;
- `enable-rcon`;
- `broadcast-rcon-to-ops`;
- `max-players`;
- `server-port`;
- `view-distance`;
- `simulation-distance`;
- `difficulty`;
- `gamemode`.

The panel creates timestamped backups before overwriting an existing `server.properties` file.

#### File manager

The built-in file manager works inside the active server directory and prevents path traversal outside it.

Supported actions:

- list files and directories;
- open editable text files;
- edit text files;
- create directories;
- upload files;
- download files;
- rename files and directories;
- delete files and directories;
- select a `.jar` file as the active server core or a Forge 1.17+ args file as the active launch target.

Editable text file types include:

```text
.json, .log, .properties, .txt, .yml, .yaml, .cfg, .conf, .toml, .ini
```

Additionally, these files are treated as editable:

```text
eula.txt
ops.json
whitelist.json
```

#### Client mods archive

The panel can manage a dedicated folder:

```text
client-mods/
```

Available actions:

- check whether the folder exists;
- create the folder;
- count files and total size;
- download the folder as a `.zip` archive.

This is useful when the server uses mods and players need a matching client-side mod pack.

#### Authentication and permissions

The current authentication model includes:

- admin login;
- HTTP-only session cookie;
- admin password change;
- public invite token creation;
- invite revocation;
- limited invited-user access.

Admin users receive all permissions.

Invited users currently receive safe limited permissions:

- start the server;
- view status;
- view metrics;
- download client mods.

The system already defines a larger permissions model for future role expansion, including permissions for servers, console, files, properties, RCON, Telegram, users, roles, localization, and audit log.

#### Java runtime settings

The settings page supports Java runtime configuration:

- list Java runtimes;
- add or update a runtime;
- set a default runtime;
- use the system `java` from `PATH`.

Built-in runtime presets include:

- system Java from `PATH`;
- Java 8 Oracle path example for Windows;
- Java 21 Temurin path example for Windows.

#### Web UI

The project includes a static Web UI served by FastAPI.

Main UI sections:

- Dashboard;
- Servers;
- Console;
- Properties;
- Files;
- Telegram;
- Users;
- Settings.

Some sections are currently placeholders for later development, especially Telegram and advanced users/roles/audit features.

#### Updater API

The backend includes an updater API that can:

- check the latest GitHub release;
- compare the current version with the latest release tag;
- dispatch an external update command;
- reject updates while the Minecraft server is running.

This is intended for controlled Linux deployment where the actual update is performed by a separate privileged system script.

---

### Tech stack

Backend:

- Python 3;
- FastAPI;
- Uvicorn;
- Pydantic v2;
- psutil;
- aiofiles;
- python-multipart;
- aiogram 3.x.

Frontend:

- static HTML;
- CSS;
- JavaScript modules;
- WebSocket connection for live console.

Storage:

- JSON files under the panel runtime directory.

---

### Repository structure

Approximate structure of the project:

```text
mc-server-controller/
├── app/
│   ├── api/
│   │   └── routes/
│   │       ├── auth.py
│   │       ├── client_mods.py
│   │       ├── console_ws.py
│   │       ├── files.py
│   │       ├── health.py
│   │       ├── properties.py
│   │       ├── servers.py
│   │       ├── settings.py
│   │       ├── updater.py
│   │       └── web.py
│   ├── core/
│   │   ├── json_store.py
│   │   └── settings.py
│   ├── models/
│   ├── services/
│   │   ├── auth.py
│   │   ├── file_manager.py
│   │   ├── log_buffer.py
│   │   ├── minecraft_manager.py
│   │   ├── panel_settings.py
│   │   ├── server_instances.py
│   │   └── server_properties.py
│   └── web/
│       ├── index.html
│       └── assets/
├── requirements.txt
├── VERSION
└── README.md
```

---

### Runtime layout

The panel uses `MC_PANEL_HOME` as its runtime directory.

If `MC_PANEL_HOME` is not set, the default path is:

```text
./runtime/mc-panel
```

On startup, the backend creates this layout:

```text
MC_PANEL_HOME/
├── config/
│   ├── panel.json
│   ├── servers.json
│   └── auth.json
├── data/
├── uploads/
│   ├── cores/
│   ├── worlds/
│   └── temp/
├── backups/
│   ├── properties/
│   ├── worlds/
│   └── icons/
└── servers/
```

---

### Installation

#### 1. Clone the repository

```bash
git clone https://github.com/Vanillllla/mc-server-controller.git
cd mc-server-controller
```

#### 2. Create a virtual environment

Linux/macOS:

```bash
python -m venv .venv
source .venv/bin/activate
```

Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

#### 3. Install dependencies

```bash
pip install -r requirements.txt
```

#### 4. Configure environment variables

Linux/macOS:

```bash
export MC_PANEL_HOME="./runtime/mc-panel"
export MC_PANEL_ADMIN_USERNAME="admin"
export MC_PANEL_ADMIN_PASSWORD="change-me"
```

Windows PowerShell:

```powershell
$env:MC_PANEL_HOME = ".\runtime\mc-panel"
$env:MC_PANEL_ADMIN_USERNAME = "admin"
$env:MC_PANEL_ADMIN_PASSWORD = "change-me"
```

For a real deployment, change the default password before exposing the panel to a network.

#### 5. Run the backend

```bash
uvicorn app.main:app --reload
```

Open:

```text
http://127.0.0.1:8000/
```

---

### Production notes

For a Linux VM or server deployment, use a persistent runtime directory:

```bash
export MC_PANEL_HOME=/srv/mc-panel
```

Recommended production setup:

- run the panel behind Nginx or another reverse proxy;
- use HTTPS;
- bind Uvicorn to localhost;
- use a systemd service;
- set a strong admin password;
- keep `MC_PANEL_HOME` outside the repository directory;
- restrict filesystem permissions for the runtime directory;
- do not expose the panel directly to the public internet without authentication and HTTPS.

Example Uvicorn command:

```bash
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

---

### Environment variables

| Variable | Default | Description |
|---|---:|---|
| `MC_PANEL_HOME` | `./runtime/mc-panel` | Main runtime directory for config, uploads, backups, and servers. |
| `MC_PANEL_LOG_BUFFER_LINES` | `5000` | Maximum number of recent log lines kept in memory. Minimum effective value is 300. |
| `MC_PANEL_ADMIN_USERNAME` | `admin` | Admin login username. |
| `MC_PANEL_ADMIN_PASSWORD` | `change-me` | Initial admin password if no stored password hash exists yet. |
| `MC_PANEL_SESSION_TTL_SECONDS` | `604800` | Session lifetime in seconds. Minimum effective value is 600. |
| `MC_PANEL_GITHUB_REPO` | `Vanillllla/mc-server-controller` | Repository used by the updater API. |
| `MC_PANEL_VERSION` | `0.1.1` | Fallback version if the `VERSION` file cannot be read. |
| `MC_PANEL_UPDATE_COMMAND` | `/usr/bin/sudo /usr/local/sbin/mc-panel-update-dispatch` | External command used by the updater API. |

---

### Basic usage

#### Create a server from a `.jar`

1. Log in as admin.
2. Open **Servers**.
3. Click **Add server**.
4. Select **Create from jar**.
5. Fill in:
   - server ID;
   - display name;
   - `.jar` core file;
   - Minecraft version;
   - server type;
   - Java runtime;
   - Xms/Xmx memory;
   - EULA checkbox.
6. Create the server.
7. Activate it if needed.
8. Start it from the dashboard.

#### Import a server from `.zip`

1. Open **Servers**.
2. Click **Add server**.
3. Select **Import from zip**.
4. Upload a `.zip` archive with the ready server folder.
5. Choose the launch mode:
   - **JAR core** for Vanilla, Paper, Spigot, and old Forge servers.
   - **Forge 1.17+ / args launch** for new Forge servers.
6. Optionally specify the launch target inside the archive.
7. If no target is specified, the backend tries to choose a suitable `.jar` or Forge args file automatically.
8. For Forge 1.20.1 the args file usually looks like `libraries/net/minecraftforge/forge/1.20.1-47.x.x/win_args.txt`.
9. Minecraft 1.20.1 requires Java 17.
10. Create and activate the server.

#### Use the console

1. Start the active server.
2. Open **Console**.
3. Watch live logs.
4. Send commands without `/`, for example:

```text
say Hello from the web panel
time set day
list
stop
```

#### Edit `server.properties`

1. Stop the active server.
2. Open **Properties**.
3. Use either quick settings or the raw editor.
4. Save changes.
5. Start the server again.

The backend rejects `server.properties` edits while the server is running.

#### Manage files

1. Open **Files**.
2. Browse the active server directory.
3. Use upload/download/edit/rename/delete actions.
4. Use **Client mods** to open or create the `client-mods` folder.
5. Download the client mods archive from the dashboard.

---

### API overview

Important routes:

```text
POST   /api/auth/login
POST   /api/auth/logout
GET    /api/auth/me
POST   /api/auth/admin/password
POST   /api/auth/invite-login
GET    /api/auth/invite
POST   /api/auth/invite
DELETE /api/auth/invite

GET    /api/servers
POST   /api/servers
POST   /api/servers/upload-core
POST   /api/servers/import-archive
GET    /api/servers/active
POST   /api/servers/{server_id}/activate
GET    /api/servers/{server_id}
PATCH  /api/servers/{server_id}
DELETE /api/servers/{server_id}

POST   /api/servers/active/start
POST   /api/servers/active/stop
POST   /api/servers/active/restart
POST   /api/servers/active/kill
GET    /api/servers/active/status
GET    /api/servers/active/work-data
GET    /api/servers/active/metrics
GET    /api/servers/active/logs/recent
POST   /api/servers/active/console/command
WS     /ws/servers/active/console

GET    /api/servers/active/properties
PUT    /api/servers/active/properties

GET    /api/servers/active/files
GET    /api/servers/active/files/text
PUT    /api/servers/active/files/text
POST   /api/servers/active/files/directories
POST   /api/servers/active/files/upload
GET    /api/servers/active/files/download
DELETE /api/servers/active/files
PATCH  /api/servers/active/files

GET    /api/servers/active/client-mods
POST   /api/servers/active/client-mods/ensure
GET    /api/servers/active/client-mods/archive

GET    /api/settings/public
GET    /api/settings/java-runtimes
POST   /api/settings/java-runtimes
POST   /api/settings/java-runtimes/default

GET    /api/updater/check
POST   /api/updater/apply
```

FastAPI also provides generated API documentation at:

```text
/docs
```

when the application is running.

---

### Security notes

This project can start real server processes and modify files on disk. Treat it as an administrative tool.

Important recommendations:

- change the default admin password;
- use HTTPS in production;
- do not expose the panel publicly without additional network protection;
- run it under a dedicated OS user;
- keep the server directory inside `MC_PANEL_HOME/servers`;
- do not grant write access to untrusted users;
- review dangerous console commands before giving command permissions;
- keep the updater command restricted and auditable.

---

### Development status and planned work

Implemented or partially implemented:

- Web UI shell;
- server instance CRUD;
- process control;
- metrics;
- live console;
- file manager;
- `server.properties` editor;
- invite access;
- Java runtime settings;
- updater API.

Planned / future work:

- full Telegram bot integration;
- advanced user and role management;
- audit log;
- localization editor;
- RCON management;
- backup management;
- richer server health checks;
- improved deployment scripts;
- Docker/systemd examples;
- automated tests.

---

### License

Recommended license: **MIT License**.

MIT is a good fit for this project because it is:

- simple;
- permissive;
- familiar to Python and web developers;
- convenient for open-source use;
- compatible with private forks and personal deployments.

Add a `LICENSE` file to the repository with the MIT license text.

---

## Русский README

### Описание

**Minecraft Web Panel** — это self-hosted веб-панель для запуска и администрирования Minecraft-серверов через браузер.

Проект подходит, если нужно:

- запускать, останавливать, перезапускать или принудительно завершать активный Minecraft-сервер;
- управлять несколькими серверными экземплярами из одной панели;
- загружать ядро сервера как `.jar`;
- импортировать готовую сборку сервера из `.zip`;
- настраивать путь к Java, версию Minecraft, тип сервера, память Xms/Xmx, JVM-аргументы и аргументы запуска сервера;
- смотреть статус сервера, uptime, PID, exit code, последние логи и метрики системы/процесса;
- использовать live-консоль через WebSocket;
- редактировать `server.properties` через быстрый редактор или raw-редактор;
- работать с файлами активного сервера: открывать, загружать, скачивать, переименовывать, удалять и редактировать;
- подготовить папку `client-mods` и скачать её как `.zip`;
- выдавать ограниченный доступ обычным пользователям через invite-ссылку;
- держать Web UI, backend API и будущую Telegram-интеграцию в одной системе управления.

---

### Основные возможности

#### Управление серверными экземплярами

- Создание серверов из:
  - одного `.jar`-ядра;
  - `.zip`-архива с готовой серверной папкой.
- Хранение серверов в runtime-директории панели.
- Выбор одного активного сервера.
- Защита от смены активного сервера во время работы.
- Удаление серверов с возможностью удалить файлы.
- Проверка ID сервера как безопасного slug.
- Автоматическая запись `eula.txt`, если EULA принята.

#### Управление процессом Minecraft-сервера

Панель умеет управлять процессом активного сервера:

- запуск;
- остановка через стандартную команду `stop` в stdin;
- перезапуск;
- принудительное завершение;
- отправка команд в консоль через stdin;
- отслеживание PID;
- отслеживание uptime;
- отслеживание exit code;
- определение состояния запуска по логам;
- сохранение ошибки запуска;
- остановка процесса при выключении backend-приложения.

Команда запуска собирается из настроек выбранного сервера:

```text
<java_path> -Xms<XMS>M -Xmx<XMX>M <jvm_args> -jar <server.jar> <server_args>
```

Forge 1.17+ can also use `forge_args` launch mode:

```text
<java_path> -Xms<XMS>M -Xmx<XMX>M <jvm_args> @user_jvm_args.txt @libraries/net/minecraftforge/forge/<version>/unix_args.txt <server_args>
```

Use `win_args.txt` on Windows and `unix_args.txt` on Linux/macOS. For Forge
1.20.1 the path usually looks like
`libraries/net/minecraftforge/forge/1.20.1-47.x.x/win_args.txt`, and Minecraft
1.20.1 requires Java 17.

Аргументы по умолчанию:

```text
-Dfile.encoding=UTF-8
nogui
```

#### Dashboard и метрики

Dashboard показывает:

- имя активного сервера;
- статус сервера;
- кнопки Start/Stop/Restart/Kill;
- загрузку CPU;
- использование RAM;
- использование памяти Java/Minecraft-процессом;
- последние строки логов.

Метрики собираются через `psutil`.

#### WebSocket-консоль

В Web UI есть live-консоль, подключённая через:

```text
/ws/servers/active/console
```

Консоль поддерживает:

- выдачу последних логов при подключении;
- потоковую передачу новых логов;
- отправку команд;
- проверку permissions;
- фильтрацию логов в интерфейсе;
- autoscroll;
- очистку окна консоли.

#### Редактор `server.properties`

Панель поддерживает:

- быстрое редактирование отдельных частых параметров;
- raw-редактирование всего файла `server.properties`.

Сейчас валидируются распространённые boolean, integer и enum-поля, например:

- `online-mode`;
- `pvp`;
- `enable-rcon`;
- `broadcast-rcon-to-ops`;
- `max-players`;
- `server-port`;
- `view-distance`;
- `simulation-distance`;
- `difficulty`;
- `gamemode`.

Перед перезаписью существующего `server.properties` создаётся backup-копия с timestamp.

#### Файловый менеджер

Встроенный файловый менеджер работает внутри директории активного сервера и защищён от выхода за её пределы через path traversal.

Поддерживаются действия:

- просмотр файлов и папок;
- открытие редактируемых текстовых файлов;
- редактирование текстовых файлов;
- создание папок;
- загрузка файлов;
- скачивание файлов;
- переименование файлов и папок;
- удаление файлов и папок;
- выбор `.jar` как ядра активного сервера.

Редактируемые расширения:

```text
.json, .log, .properties, .txt, .yml, .yaml, .cfg, .conf, .toml, .ini
```

Также редактируемыми считаются:

```text
eula.txt
ops.json
whitelist.json
```

#### Архив клиентских модов

Панель умеет работать с отдельной папкой:

```text
client-mods/
```

Доступные действия:

- проверить существование папки;
- создать папку;
- посчитать количество файлов и общий размер;
- скачать папку как `.zip`.

Это удобно для модовых серверов, где игрокам нужно выдать одинаковый набор клиентских модов.

#### Авторизация и permissions

Текущая модель авторизации включает:

- вход администратора;
- HTTP-only session cookie;
- смену пароля администратора;
- создание публичного invite-token;
- отзыв invite-ссылки;
- ограниченный доступ для invited user.

Администратор получает все permissions.

Обычный пользователь по invite-ссылке получает безопасный ограниченный доступ:

- запуск сервера;
- просмотр статуса;
- просмотр метрик;
- скачивание client mods.

В коде уже заложена расширенная модель permissions для будущих ролей: servers, console, files, properties, RCON, Telegram, users, roles, localization, audit log.

#### Настройки Java Runtime

Страница настроек поддерживает Java runtimes:

- просмотр списка Java;
- добавление или обновление runtime;
- выбор Java по умолчанию;
- использование системного `java` из `PATH`.

Встроенные presets:

- system Java from `PATH`;
- пример пути Java 8 Oracle для Windows;
- пример пути Java 21 Temurin для Windows.

#### Web UI

Проект содержит статический Web UI, который отдаётся через FastAPI.

Основные разделы интерфейса:

- Dashboard;
- Servers;
- Console;
- Properties;
- Files;
- Telegram;
- Users;
- Settings.

Некоторые разделы пока являются заготовками под будущую разработку, особенно Telegram и расширенное управление пользователями/ролями/audit log.

#### Updater API

Backend содержит updater API, который умеет:

- проверять latest GitHub release;
- сравнивать текущую версию с последним release tag;
- запускать внешнюю update-команду;
- запрещать обновление, пока Minecraft-сервер запущен.

Это рассчитано на контролируемый Linux deployment, где реальное обновление выполняет отдельный системный скрипт с нужными правами.

---

### Технологический стек

Backend:

- Python 3;
- FastAPI;
- Uvicorn;
- Pydantic v2;
- psutil;
- aiofiles;
- python-multipart;
- aiogram 3.x.

Frontend:

- статический HTML;
- CSS;
- JavaScript modules;
- WebSocket для live-консоли.

Хранилище:

- JSON-файлы внутри runtime-директории панели.

---

### Структура репозитория

Примерная структура проекта:

```text
mc-server-controller/
├── app/
│   ├── api/
│   │   └── routes/
│   │       ├── auth.py
│   │       ├── client_mods.py
│   │       ├── console_ws.py
│   │       ├── files.py
│   │       ├── health.py
│   │       ├── properties.py
│   │       ├── servers.py
│   │       ├── settings.py
│   │       ├── updater.py
│   │       └── web.py
│   ├── core/
│   │   ├── json_store.py
│   │   └── settings.py
│   ├── models/
│   ├── services/
│   │   ├── auth.py
│   │   ├── file_manager.py
│   │   ├── log_buffer.py
│   │   ├── minecraft_manager.py
│   │   ├── panel_settings.py
│   │   ├── server_instances.py
│   │   └── server_properties.py
│   └── web/
│       ├── index.html
│       └── assets/
├── requirements.txt
├── VERSION
└── README.md
```

---

### Runtime layout

Панель использует `MC_PANEL_HOME` как основную runtime-директорию.

Если `MC_PANEL_HOME` не задан, используется путь:

```text
./runtime/mc-panel
```

При запуске backend создаёт такую структуру:

```text
MC_PANEL_HOME/
├── config/
│   ├── panel.json
│   ├── servers.json
│   └── auth.json
├── data/
├── uploads/
│   ├── cores/
│   ├── worlds/
│   └── temp/
├── backups/
│   ├── properties/
│   ├── worlds/
│   └── icons/
└── servers/
```

---

### Установка

#### 1. Клонировать репозиторий

```bash
git clone https://github.com/Vanillllla/mc-server-controller.git
cd mc-server-controller
```

#### 2. Создать виртуальное окружение

Linux/macOS:

```bash
python -m venv .venv
source .venv/bin/activate
```

Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

#### 3. Установить зависимости

```bash
pip install -r requirements.txt
```

#### 4. Настроить переменные окружения

Linux/macOS:

```bash
export MC_PANEL_HOME="./runtime/mc-panel"
export MC_PANEL_ADMIN_USERNAME="admin"
export MC_PANEL_ADMIN_PASSWORD="change-me"
```

Windows PowerShell:

```powershell
$env:MC_PANEL_HOME = ".\runtime\mc-panel"
$env:MC_PANEL_ADMIN_USERNAME = "admin"
$env:MC_PANEL_ADMIN_PASSWORD = "change-me"
```

Для реального deployment обязательно поменяй пароль по умолчанию.

#### 5. Запустить backend

```bash
uvicorn app.main:app --reload
```

Открыть:

```text
http://127.0.0.1:8000/
```

---

### Production notes

Для Linux VM или сервера лучше использовать постоянную runtime-директорию:

```bash
export MC_PANEL_HOME=/srv/mc-panel
```

Рекомендуемая схема production-запуска:

- запускать панель за Nginx или другим reverse proxy;
- использовать HTTPS;
- привязать Uvicorn к localhost;
- оформить запуск через systemd;
- задать сильный пароль администратора;
- держать `MC_PANEL_HOME` вне директории репозитория;
- ограничить права на runtime-директорию;
- не публиковать панель напрямую в интернет без HTTPS и нормальной авторизации.

Пример команды Uvicorn:

```bash
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

---

### Переменные окружения

| Переменная | Значение по умолчанию | Назначение |
|---|---:|---|
| `MC_PANEL_HOME` | `./runtime/mc-panel` | Основная runtime-директория для конфигов, загрузок, backup и серверов. |
| `MC_PANEL_LOG_BUFFER_LINES` | `5000` | Максимальное количество строк логов в памяти. Минимальное эффективное значение — 300. |
| `MC_PANEL_ADMIN_USERNAME` | `admin` | Логин администратора. |
| `MC_PANEL_ADMIN_PASSWORD` | `change-me` | Начальный пароль администратора, если ещё нет сохранённого hash пароля. |
| `MC_PANEL_SESSION_TTL_SECONDS` | `604800` | Время жизни сессии в секундах. Минимальное эффективное значение — 600. |
| `MC_PANEL_GITHUB_REPO` | `Vanillllla/mc-server-controller` | Репозиторий для updater API. |
| `MC_PANEL_VERSION` | `0.1.1` | Fallback-версия, если файл `VERSION` не удалось прочитать. |
| `MC_PANEL_UPDATE_COMMAND` | `/usr/bin/sudo /usr/local/sbin/mc-panel-update-dispatch` | Внешняя команда, которую вызывает updater API. |

---

### Базовое использование

#### Создать сервер из `.jar`

1. Войти как admin.
2. Открыть **Servers**.
3. Нажать **Add server**.
4. Выбрать **Create from jar**.
5. Заполнить:
   - ID сервера;
   - название;
   - `.jar` ядро;
   - версию Minecraft;
   - тип сервера;
   - Java runtime;
   - память Xms/Xmx;
   - EULA checkbox.
6. Создать сервер.
7. Активировать его при необходимости.
8. Запустить через dashboard.

#### Импортировать сервер из `.zip`

1. Открыть **Servers**.
2. Нажать **Add server**.
3. Выбрать **Import from zip**.
4. Загрузить `.zip` архив с готовой серверной папкой.
5. При необходимости указать `.jar` файл внутри архива.
6. Если `.jar` не указан, backend попробует выбрать подходящий автоматически.
7. Создать и активировать сервер.

#### Использовать консоль

1. Запустить активный сервер.
2. Открыть **Console**.
3. Смотреть live-логи.
4. Отправлять команды без `/`, например:

```text
say Hello from the web panel
time set day
list
stop
```

#### Редактировать `server.properties`

1. Остановить активный сервер.
2. Открыть **Properties**.
3. Использовать быстрые настройки или raw-редактор.
4. Сохранить изменения.
5. Снова запустить сервер.

Backend запрещает менять `server.properties`, пока сервер работает.

#### Управлять файлами

1. Открыть **Files**.
2. Перейти по директориям активного сервера.
3. Использовать upload/download/edit/rename/delete.
4. Через **Client mods** открыть или создать папку `client-mods`.
5. Скачать архив клиентских модов через dashboard.

---

### API overview

Основные routes:

```text
POST   /api/auth/login
POST   /api/auth/logout
GET    /api/auth/me
POST   /api/auth/admin/password
POST   /api/auth/invite-login
GET    /api/auth/invite
POST   /api/auth/invite
DELETE /api/auth/invite

GET    /api/servers
POST   /api/servers
POST   /api/servers/upload-core
POST   /api/servers/import-archive
GET    /api/servers/active
POST   /api/servers/{server_id}/activate
GET    /api/servers/{server_id}
PATCH  /api/servers/{server_id}
DELETE /api/servers/{server_id}

POST   /api/servers/active/start
POST   /api/servers/active/stop
POST   /api/servers/active/restart
POST   /api/servers/active/kill
GET    /api/servers/active/status
GET    /api/servers/active/work-data
GET    /api/servers/active/metrics
GET    /api/servers/active/logs/recent
POST   /api/servers/active/console/command
WS     /ws/servers/active/console

GET    /api/servers/active/properties
PUT    /api/servers/active/properties

GET    /api/servers/active/files
GET    /api/servers/active/files/text
PUT    /api/servers/active/files/text
POST   /api/servers/active/files/directories
POST   /api/servers/active/files/upload
GET    /api/servers/active/files/download
DELETE /api/servers/active/files
PATCH  /api/servers/active/files

GET    /api/servers/active/client-mods
POST   /api/servers/active/client-mods/ensure
GET    /api/servers/active/client-mods/archive

GET    /api/settings/public
GET    /api/settings/java-runtimes
POST   /api/settings/java-runtimes
POST   /api/settings/java-runtimes/default

GET    /api/updater/check
POST   /api/updater/apply
```

Документация FastAPI доступна после запуска приложения:

```text
/docs
```

---

### Security notes

Этот проект запускает реальные серверные процессы и меняет файлы на диске. Его нужно воспринимать как административный инструмент.

Рекомендации:

- поменять пароль администратора;
- использовать HTTPS в production;
- не выставлять панель в открытый интернет без дополнительной сетевой защиты;
- запускать приложение от отдельного OS user;
- хранить серверы внутри `MC_PANEL_HOME/servers`;
- не выдавать write-доступ ненадёжным пользователям;
- внимательно относиться к праву отправлять команды в консоль;
- держать update-команду ограниченной и проверяемой.

---

### Статус разработки и планы

Реализовано или частично реализовано:

- Web UI shell;
- CRUD серверных экземпляров;
- управление процессом;
- метрики;
- live-консоль;
- файловый менеджер;
- редактор `server.properties`;
- invite-доступ;
- настройки Java runtime;
- updater API.

Планируется / можно добавить дальше:

- полноценная Telegram bot integration;
- расширенное управление пользователями и ролями;
- audit log;
- localization editor;
- RCON management;
- backup management;
- более точные health checks сервера;
- deployment scripts;
- Docker/systemd examples;
- automated tests.

---

### Лицензия

Рекомендуемая лицензия: **MIT License**.

MIT хорошо подходит для этого проекта, потому что она:

- простая;
- permissive;
- привычная для Python/web-проектов;
- удобна для open-source;
- разрешает private forks и личные deployments.

Добавь в репозиторий файл `LICENSE` с текстом MIT License.
