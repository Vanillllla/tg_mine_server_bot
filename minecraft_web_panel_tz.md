# Техническое задание
# Web-панель управления Minecraft-серверами с Telegram-ботом

## 1. Общая идея проекта

Разработать web-приложение для управления несколькими Minecraft-серверами, размещёнными на Linux VM внутри Proxmox.

Проект должен заменить старую архитектуру:

```text
Windows GUI + Telegram Bot + ServerSystem + Pipe Connector
```

на новую архитектуру:

```text
Web GUI + Telegram Bot
        ↓
единый Backend API
        ↓
Minecraft Server Manager
        ↓
несколько Minecraft Server Instances
```

Главная особенность проекта: система должна хранить **несколько полноценных папок Minecraft-серверов**, а администратор должен иметь возможность **одной кнопкой выбрать активный сервер**, который будет запускаться, настраиваться и обслуживаться через сайт и Telegram-бота.

Старый проект `tg_mine_server_bot` использовать как основу для переноса логики управления сервером, Telegram-бота, локализации, работы с ядрами и настроек GUI.

---

## 2. Цели проекта

### 2.1. Основная цель

Создать удобную web-панель, через которую можно:

- управлять несколькими Minecraft-серверами;
- выбирать активный сервер;
- запускать, останавливать и перезапускать активный сервер;
- пользоваться полноценной web-консолью;
- редактировать `server.properties`;
- управлять файлами сервера;
- загружать ядра, моды, конфиги и миры;
- управлять Telegram-ботом;
- управлять пользователями и правами;
- смотреть нагрузку на VM и Java-процесс;
- локализовать сайт и бота.

### 2.2. Второстепенные цели

- переиспользовать рабочие части старого проекта;
- отказаться от Windows/PyQt-зависимости;
- подготовить систему для запуска в Linux VM;
- сделать архитектуру расширяемой под несколько серверов;
- обеспечить безопасность файлового менеджера и консоли;
- подготовить основу для будущей хостинг-панели.

---

## 3. Целевая платформа

### 3.1. Серверная среда

```text
Гипервизор: Proxmox
Гостевая система: Debian / Ubuntu Server
Тип установки: VM
Рабочий пользователь: minecraft или mc-panel
Запуск backend: systemd service или Docker Compose
Reverse proxy: Nginx / Caddy
HTTPS: обязательно при доступе из интернета
```

### 3.2. Клиентская среда

- Desktop browser;
- Mobile browser;
- Telegram-клиент.

---

## 4. Рекомендуемый стек

### 4.1. Backend

```text
Python 3.12+
FastAPI
Uvicorn
WebSocket
SQLAlchemy
SQLite для MVP
PostgreSQL для будущей версии
psutil
aiofiles
python-multipart
Pillow
aiogram 3.x
```

### 4.2. Frontend

```text
Vue 3 + TypeScript
Pinia
Vue Router
Tailwind CSS
Vite
vue-i18n или собственный i18n-клиент
```

Допустимая альтернатива:

```text
React + TypeScript + Zustand/Redux + Tailwind CSS
```

### 4.3. Хранение данных

Для MVP:

```text
SQLite
JSON-конфиги
локальная файловая структура /srv/mc-panel
```

Для будущей промышленной версии:

```text
PostgreSQL
миграции через Alembic
секреты через отдельное хранилище
```

---

## 5. Архитектура проекта

### 5.1. Общая схема

```text
Browser Web GUI
       ↓ HTTP / WebSocket
FastAPI Backend
       ↓
Service Layer
       ├─ ServerInstanceService
       ├─ MinecraftServerManager
       ├─ ServerPropertiesService
       ├─ FileManagerService
       ├─ RconService
       ├─ MetricsService
       ├─ TelegramBotService
       ├─ LocalizationService
       ├─ PermissionService
       └─ AuditLogService
       ↓
Minecraft Server Instances
       ├─ Forge 1.12.2 HBM
       ├─ Vanilla 1.20.1
       └─ Test Server
```

### 5.2. Принцип единого центра управления

Web GUI и Telegram-бот не должны независимо управлять Minecraft-сервером.

Правильная схема:

```text
Web GUI ───────┐
               ├── Backend API / Service Layer ── MinecraftServerManager
Telegram Bot ──┘
```

Неправильная схема:

```text
Web GUI ────── Minecraft process
Telegram Bot ─ Minecraft process
```

Причина: иначе появится рассинхронизация состояния, конфликт команд, неправильный активный сервер и разная система прав.

---

## 6. Модель нескольких серверов

### 6.1. Основное понятие

В проекте должен использоваться термин:

```text
Server Instance
```

`Server Instance` — это полноценная папка Minecraft-сервера.

Пример:

```text
/srv/mc-panel/servers/forge_1_12_2_hbm/
├─ server.properties
├─ eula.txt
├─ mods/
├─ config/
├─ world/
├─ logs/
├─ server-icon.png
└─ forge-1.12.2-14.23.5.2859.jar
```

### 6.2. Отличие от старого `core`

В старом проекте использовалось понятие `core`, но оно смешивало:

- jar-файл ядра;
- папку сервера;
- настройки запуска.

В новом проекте нужно разделить:

```text
Server Instance — папка сервера;
Core/Jar — исполняемый jar-файл внутри папки сервера;
Launch Settings — настройки запуска конкретного сервера.
```

---

## 7. Файловая структура на сервере

Рекомендуемая структура:

```text
/srv/mc-panel/
├─ app/
│  └─ backend/frontend files
│
├─ config/
│  ├─ panel.json
│  ├─ servers.json
│  ├─ secrets.json
│  └─ permissions.json
│
├─ data/
│  ├─ panel.db
│  └─ audit.log
│
├─ uploads/
│  ├─ cores/
│  ├─ worlds/
│  └─ temp/
│
├─ backups/
│  ├─ properties/
│  ├─ worlds/
│  └─ icons/
│
└─ servers/
   ├─ forge_1_12_2_hbm/
   ├─ vanilla_1_20_1/
   └─ test_server/
```

---

## 8. Конфигурация серверов

### 8.1. `servers.json`

Для MVP можно использовать JSON:

```json
{
  "forge_1_12_2_hbm": {
    "display_name": "Forge 1.12.2 HBM",
    "server_dir": "/srv/mc-panel/servers/forge_1_12_2_hbm",
    "jar_file": "forge-1.12.2-14.23.5.2859.jar",
    "minecraft_version": "1.12.2",
    "server_type": "forge",
    "java_path": "/usr/lib/jvm/java-8-openjdk-amd64/bin/java",
    "xms_mb": 2048,
    "xmx_mb": 6144,
    "jvm_args": [
      "-Dfile.encoding=UTF-8",
      "-XX:+UseG1GC"
    ],
    "server_args": [
      "nogui"
    ],
    "eula_accept": true,
    "auto_restart": false,
    "startup_timeout": 180,
    "created_at": "2026-05-14T00:00:00"
  }
}
```

### 8.2. `panel.json`

```json
{
  "panel": {
    "language": "ru",
    "theme": "dark",
    "debug_mode": false
  },
  "server": {
    "active_server_id": "forge_1_12_2_hbm",
    "use_last_active_server": true,
    "shutdown_if_empty_minutes": 5
  },
  "telegram": {
    "autostart": true,
    "token_secret_id": "telegram_bot_token"
  }
}
```

---

## 9. Роли и права

### 9.1. Базовые роли

```text
Owner
Admin
Moderator
Viewer
```

### 9.2. Права

```text
servers.view
servers.create
servers.import
servers.activate
servers.delete
servers.edit_launch_settings

server.start
server.stop
server.restart
server.kill
server.view_status
server.view_metrics

console.view
console.send_command
console.send_dangerous_command

files.view
files.upload
files.download
files.edit
files.delete
files.rename
files.manage_world
files.manage_mods
files.upload_core

properties.view
properties.quick_edit
properties.raw_edit

rcon.view
rcon.manage
rcon.regenerate_password

telegram.view
telegram.start
telegram.stop
telegram.edit_token

users.view
users.manage
roles.manage

localization.view
localization.edit

audit.view
```

### 9.3. Особо опасные права

```text
servers.delete
files.delete
files.upload_core
console.send_dangerous_command
properties.raw_edit
rcon.manage
telegram.edit_token
roles.manage
```

Эти права должны быть только у `Owner` или у специально назначенных админов.

---

## 10. Основные страницы Web GUI

### 10.1. Dashboard

Главная страница должна показывать:

- активный сервер;
- статус: `OFF / STARTING / RUNNING / STOPPING / ERROR`;
- версия Minecraft;
- тип сервера: `Forge / Vanilla / Paper / Spigot / Custom`;
- uptime;
- online игроков;
- TPS;
- CPU системы;
- RAM системы;
- RAM Java-процесса;
- PID процесса;
- последние строки логов;
- кнопки `Start / Stop / Restart / Kill`.

### 10.2. Servers / Instances

Страница списка серверов.

Функции:

- показать все серверные папки;
- показать активный сервер;
- сделать сервер активным;
- создать новый сервер;
- импортировать готовую папку сервера;
- загрузить новое ядро;
- удалить сервер;
- открыть настройки запуска;
- открыть файловый менеджер конкретного сервера.

Пример интерфейса:

```text
Forge 1.12.2 HBM     [Активен]          [Настроить] [Файлы] [Удалить]
Vanilla 1.20.1       [Сделать активным] [Настроить] [Файлы] [Удалить]
Test Server          [Сделать активным] [Настроить] [Файлы] [Удалить]
```

Правило:

```text
Нельзя переключать активный сервер, если текущий сервер запущен.
```

### 10.3. Console

Полноценная web-консоль активного сервера.

Функции:

- live-вывод stdout/stderr;
- отправка команд в stdin или RCON;
- история последних строк;
- автоскролл;
- фильтр `INFO/WARN/ERROR`;
- очистка локального экрана;
- отображение команды пользователя как `> command`;
- запрет команд по правам;
- отдельное предупреждение для опасных команд.

WebSocket:

```text
WS /ws/servers/active/console
```

### 10.4. Quick Server Properties

Быстрый редактор избранных параметров `server.properties`.

Разделы:

```text
Основное:
- motd
- server-port
- max-players
- online-mode
- gamemode
- difficulty
- pvp

Производительность:
- view-distance
- simulation-distance
- entity-broadcast-range-percentage

Мир:
- level-name
- level-seed
- generate-structures
- allow-nether

Мобы:
- spawn-monsters
- spawn-animals
- spawn-npcs

Администрирование:
- enable-command-block
- white-list
- enforce-whitelist

RCON:
- enable-rcon
- rcon.port
- rcon.password
- broadcast-rcon-to-ops

Query:
- enable-query
- query.port
```

### 10.5. Raw `server.properties` Editor

Отдельный режим полного редактирования файла.

Функции:

- открыть весь `server.properties` как текст;
- подсветить `key=value`;
- сохранить;
- сделать backup перед сохранением;
- показать diff перед сохранением;
- предупредить об опасных ключах.

Перед сохранением обязательно создавать backup:

```text
/srv/mc-panel/backups/properties/forge_1_12_2_hbm/server.properties.2026-05-14_23-30-00.bak
```

### 10.6. Launch Settings

Настройки запуска конкретного Server Instance.

Поля:

- `display_name`;
- `server_dir`;
- `jar_file`;
- `minecraft_version`;
- `server_type`;
- `java_path`;
- `xms_mb`;
- `xmx_mb`;
- `jvm_args`;
- `server_args`;
- `eula_accept`;
- `auto_restart`;
- `startup_timeout`.

Проверки:

- `jar_file` существует внутри `server_dir`;
- `java_path` существует или используется `java` из `PATH`;
- `xmx_mb >= xms_mb`;
- `xms_mb >= 64`;
- `xmx_mb` не больше допустимой RAM VM;
- `eula_accept=true` перед запуском;
- `server_dir` не выходит за разрешённый root.

### 10.7. File Manager

Файловый менеджер активного сервера.

Функции:

- открыть папку;
- просмотреть список файлов;
- скачать файл;
- загрузить файл;
- удалить файл;
- переименовать файл;
- создать папку;
- редактировать текстовый файл;
- распаковать архив;
- загрузить jar;
- загрузить моды;
- загрузить конфиги;
- загрузить мир;
- скачать мир архивом.

Ограничения безопасности:

- нельзя выйти выше `server_dir`;
- нельзя читать `/etc`, `/root`, `/home` и другие системные пути;
- нельзя использовать `../../`;
- нельзя редактировать бинарные файлы как текст;
- лимит размера загрузки;
- подтверждение удаления `world/`, `mods/`, `config/`;
- backup перед заменой важных файлов.

### 10.8. Mods / Plugins

Поверх файлового менеджера сделать удобную страницу.

Для Forge:

```text
mods/
config/
```

Для Bukkit/Paper/Spigot:

```text
plugins/
```

Функции:

- список модов/плагинов;
- загрузить jar;
- отключить мод переименованием `.jar` → `.jar.disabled`;
- включить обратно;
- удалить;
- скачать;
- посмотреть дату изменения и размер.

### 10.9. World Manager

Функции:

- показать текущий world;
- скачать world архивом;
- загрузить новый world;
- сделать backup мира;
- восстановить backup;
- удалить world;
- переименовать world;
- изменить `level-name` в `server.properties`.

Удаление мира должно требовать подтверждения.

### 10.10. Server Icon

Иконка сервера — файл:

```text
server-icon.png
```

Функции:

- показать текущую иконку;
- загрузить новую;
- проверить PNG;
- проверить/привести размер к 64x64;
- сделать backup старой иконки;
- удалить иконку.

Требования:

- только PNG;
- рекомендуемый размер 64x64;
- лимит размера файла;
- хранение строго в корне `server_dir`.

### 10.11. Telegram Bot Settings

Функции:

- показать статус Telegram-бота;
- запустить бота;
- остановить бота;
- перезапустить бота;
- изменить токен;
- проверить токен;
- настроить автозапуск;
- список разрешённых Telegram-пользователей;
- связать Telegram ID с web-пользователем;
- выбрать язык пользователя.

### 10.12. Users and Permissions

Функции:

- список пользователей;
- создать пользователя;
- изменить пароль;
- назначить роль;
- включить/отключить пользователя;
- связать с Telegram ID;
- настроить индивидуальные права;
- посмотреть активные сессии;
- завершить сессию.

### 10.13. Localization Settings

Функции:

- список доступных языков;
- выбор языка сайта;
- выбор языка Telegram-бота для пользователя;
- просмотр ключей локализации;
- проверка отсутствующих переводов;
- добавление нового языка через JSON-файл.

### 10.14. Audit Log

Лог действий пользователей.

Записывать:

- вход в систему;
- запуск сервера;
- остановку сервера;
- смену активного сервера;
- отправку консольной команды;
- изменение `server.properties`;
- загрузку файла;
- удаление файла;
- изменение токена Telegram-бота;
- изменение прав пользователей.

---

## 11. Backend-сервисы

### 11.1. `ServerInstanceService`

Отвечает за список серверов.

Методы:

```python
list_servers()
get_server(server_id)
create_server(data)
import_server_folder(path)
upload_core(file)
activate_server(server_id)
get_active_server()
update_server(server_id, data)
delete_server(server_id, delete_files=False)
```

### 11.2. `MinecraftServerManager`

Отвечает за запуск активного сервера.

Методы:

```python
start()
stop()
restart()
kill()
is_running()
send_stdin_command(command)
get_status()
get_work_data()
get_recent_logs()
```

При запуске использовать настройки активного сервера:

```text
java_path
-Dfile.encoding=UTF-8
-Xms
-Xmx
jvm_args
-jar jar_file
server_args
cwd=server_dir
```

### 11.3. `LogBuffer`

Функции:

- хранить последние N строк логов;
- отдавать recent logs;
- рассылать новые строки через WebSocket;
- разделять stdout/stderr;
- сохранять важные ошибки запуска.

### 11.4. `RconService`

Функции:

- читать RCON-настройки из `server.properties`;
- включать RCON;
- отключать RCON;
- генерировать пароль;
- отправлять RCON-команды;
- нормализовать многострочный ответ;
- скрывать пароль в UI.

### 11.5. `ServerPropertiesService`

Функции:

- читать `server.properties`;
- парсить `key=value`;
- сохранять изменения;
- сохранять комментарии;
- делать backup;
- отдавать quick settings;
- сохранять quick settings;
- raw read/write.

### 11.6. `FileManagerService`

Методы:

```python
list_dir(server_id, path)
read_text(server_id, path)
write_text(server_id, path, content)
upload_file(server_id, path, file)
download_file(server_id, path)
delete_path(server_id, path)
rename_path(server_id, path, new_name)
create_dir(server_id, path)
extract_archive(server_id, path)
```

Обязательная защита:

```python
resolved = (server_root / user_path).resolve()

if not resolved.is_relative_to(server_root.resolve()):
    raise PermissionError("unsafe_path")
```

### 11.7. `ServerIconService`

Методы:

```python
get_icon(server_id)
upload_icon(server_id, file)
delete_icon(server_id)
backup_icon(server_id)
```

### 11.8. `MetricsService`

Собирать:

```text
system:
- cpu_percent
- ram_used_gb
- ram_total_gb
- ram_percent
- disk_used_gb
- disk_total_gb
- disk_percent

server process:
- pid
- cpu_percent
- ram_rss_mb
- ram_rss_gb
- ram_percent_of_system
- ram_percent_of_xmx

minecraft:
- online_players
- max_players
- version
- tps
```

### 11.9. `TelegramBotService`

Функции:

- запуск Telegram-бота;
- остановка Telegram-бота;
- перезапуск;
- проверка статуса;
- чтение токена;
- обновление токена;
- связь Telegram-пользователя с web-пользователем.

### 11.10. `LocalizationService`

Функции:

- загружать JSON-файлы локализации;
- отдавать список языков;
- получать текст по ключу;
- отдавать переводы frontend;
- использовать те же переводы в Telegram-боте;
- проверять отсутствующие ключи.

---

## 12. Локализация

### 12.1. Принцип

Должен быть один общий источник переводов:

```text
backend/app/locales/ru.json
backend/app/locales/en.json
```

Используют:

- backend;
- frontend;
- Telegram-бот.

### 12.2. Структура JSON

```json
{
  "meta": {
    "code": "ru",
    "name": "Русский",
    "flag": "🇷🇺"
  },
  "common": {
    "save": "Сохранить",
    "cancel": "Отмена",
    "delete": "Удалить",
    "edit": "Изменить",
    "back": "Назад",
    "loading": "Загрузка..."
  },
  "pages": {
    "dashboard": "Панель управления",
    "servers": "Серверы",
    "console": "Консоль",
    "files": "Файлы",
    "properties": "server.properties",
    "launch_settings": "Настройки запуска",
    "telegram": "Telegram-бот",
    "users": "Пользователи",
    "audit": "Журнал действий"
  },
  "server": {
    "start": "Запустить сервер",
    "stop": "Остановить сервер",
    "restart": "Перезапустить сервер",
    "kill": "Принудительно завершить",
    "status_on": "Сервер включён",
    "status_off": "Сервер выключен",
    "status_starting": "Сервер запускается",
    "status_error": "Ошибка сервера"
  },
  "console": {
    "title": "Консоль сервера",
    "placeholder": "Введите команду сервера...",
    "send": "Отправить",
    "clear": "Очистить экран"
  },
  "bot_buttons": {
    "start_server": "🚀 Запустить сервер",
    "stop_server": "🛑 Остановить сервер",
    "workload": "📊 Нагрузка сервера",
    "online": "👥 Онлайн",
    "console": "📟 Консоль сервера",
    "settings": "⚙️ Настройки"
  },
  "errors": {
    "permission_denied": "Недостаточно прав.",
    "unsafe_path": "Недопустимый путь.",
    "server_not_running": "Сервер выключен.",
    "active_server_not_selected": "Активный сервер не выбран.",
    "file_not_found": "Файл не найден."
  }
}
```

---

## 13. Telegram-бот

### 13.1. Назначение

Telegram-бот является дополнительным интерфейсом управления.

Функции:

- запуск активного сервера;
- остановка активного сервера;
- перезапуск;
- просмотр статуса;
- просмотр нагрузки;
- просмотр онлайна;
- отправка RCON-команд;
- режим консоли;
- выбор языка;
- выбор активного сервера для админа;
- уведомления о запуске/падении/остановке.

### 13.2. Состояние пользователя

Нельзя хранить один глобальный `profile_info` на весь бот.

Нужно:

- получать профиль из БД по `tg_id`;
- хранить язык пользователя;
- хранить роль;
- проверять права перед каждым действием.

### 13.3. Меню Telegram-бота

Меню должно строиться динамически:

- по роли пользователя;
- по языку пользователя;
- по состоянию активного сервера;
- по доступным permissions.

---

## 14. API

### 14.1. Auth

```text
POST /api/auth/login
POST /api/auth/logout
GET  /api/auth/me
POST /api/auth/change-password
```

### 14.2. Servers

```text
GET    /api/servers
POST   /api/servers
GET    /api/servers/active
POST   /api/servers/{server_id}/activate
GET    /api/servers/{server_id}
PATCH  /api/servers/{server_id}
DELETE /api/servers/{server_id}
```

### 14.3. Server control

```text
POST /api/servers/active/start
POST /api/servers/active/stop
POST /api/servers/active/restart
POST /api/servers/active/kill
GET  /api/servers/active/status
GET  /api/servers/active/work-data
GET  /api/servers/active/metrics
```

### 14.4. Console

```text
GET  /api/servers/active/logs/recent
POST /api/servers/active/console/command
WS   /ws/servers/active/console
```

### 14.5. Properties

```text
GET  /api/servers/{server_id}/properties/quick
PUT  /api/servers/{server_id}/properties/quick

GET  /api/servers/{server_id}/properties/raw
PUT  /api/servers/{server_id}/properties/raw

POST /api/servers/{server_id}/properties/backup
```

### 14.6. RCON

```text
GET  /api/servers/{server_id}/rcon/status
POST /api/servers/{server_id}/rcon/enable
POST /api/servers/{server_id}/rcon/disable
POST /api/servers/{server_id}/rcon/regenerate-password
POST /api/servers/{server_id}/rcon/command
```

### 14.7. Files

```text
GET    /api/servers/{server_id}/files/list?path=/
GET    /api/servers/{server_id}/files/download?path=/mods/mod.jar
POST   /api/servers/{server_id}/files/upload
GET    /api/servers/{server_id}/files/read-text?path=/config/file.cfg
PUT    /api/servers/{server_id}/files/write-text
DELETE /api/servers/{server_id}/files/delete
PATCH  /api/servers/{server_id}/files/rename
POST   /api/servers/{server_id}/files/mkdir
POST   /api/servers/{server_id}/files/extract
```

### 14.8. Server icon

```text
GET    /api/servers/{server_id}/icon
PUT    /api/servers/{server_id}/icon
DELETE /api/servers/{server_id}/icon
```

### 14.9. Telegram

```text
GET  /api/telegram/status
POST /api/telegram/start
POST /api/telegram/stop
POST /api/telegram/restart
PUT  /api/telegram/token
POST /api/telegram/test-token
GET  /api/telegram/accounts
POST /api/telegram/accounts/link
```

### 14.10. Localization

```text
GET /api/localization/languages
GET /api/localization/{language_code}
```

### 14.11. Users

```text
GET    /api/users
POST   /api/users
GET    /api/users/{id}
PATCH  /api/users/{id}
DELETE /api/users/{id}

GET    /api/roles
POST   /api/roles
PATCH  /api/roles/{id}
DELETE /api/roles/{id}
```

---

## 15. WebSocket-протокол консоли

### 15.1. Сообщение от backend к frontend

```json
{
  "type": "log",
  "stream": "stdout",
  "server_id": "forge_1_12_2_hbm",
  "timestamp": "2026-05-14T23:00:00",
  "line": "[Server thread/INFO]: Done (12.345s)! For help, type \"help\""
}
```

### 15.2. Сообщение от frontend к backend

```json
{
  "type": "command",
  "command": "list"
}
```

### 15.3. Ошибка

```json
{
  "type": "error",
  "code": "permission_denied",
  "message": "Недостаточно прав."
}
```

---

## 16. Состояния сервера

Сервер должен иметь состояния:

```text
OFF
STARTING
RUNNING
STOPPING
ERROR
UNKNOWN
```

### 16.1. STARTING

При запуске:

- установить состояние `STARTING`;
- сохранить `start_time`;
- очистить `start_error`;
- начать читать `stdout/stderr`;
- ждать признака успешного запуска;
- при успехе установить `RUNNING`;
- при ошибке установить `ERROR`.

### 16.2. Признаки успешного запуска

Использовать несколько способов:

- строка `Done (...)! For help, type "help"`;
- успешный Minecraft status ping на `server-port`;
- процесс жив и порт принимает соединение.

### 16.3. Ошибка запуска

При ошибке сохранить:

- `start_error`;
- `exit_code`;
- последние 10-50 строк логов;
- `launch_time`.

---

## 17. Быстрый авто-редактор `server.properties`

### 17.1. Назначение

Сделать backend-сервис и CLI-команду для быстрого изменения избранных параметров.

Примеры CLI:

```bash
mc-panel props set active difficulty hard
mc-panel props set active view-distance 8
mc-panel props set active simulation-distance 6
mc-panel props set active online-mode true
mc-panel props rcon enable active
mc-panel props motd active "Forge HBM Server"
```

### 17.2. Поддерживаемые поля

```text
difficulty
view-distance
simulation-distance
online-mode
gamemode
max-players
motd
pvp
enable-command-block
spawn-monsters
spawn-animals
spawn-npcs
allow-nether
generate-structures
white-list
enforce-whitelist
enable-rcon
rcon.port
rcon.password
broadcast-rcon-to-ops
```

### 17.3. Валидация

```text
difficulty: peaceful/easy/normal/hard или 0/1/2/3
view-distance: 2–32
simulation-distance: 2–32
server-port: 1–65535
max-players: 1–100000
online-mode: bool
enable-rcon: bool
motd: string
```

### 17.4. Версионная совместимость

`simulation-distance` есть не во всех версиях Minecraft.

Поведение:

- если ключ существует — редактировать;
- если ключа нет — показать предупреждение;
- дать кнопку “добавить параметр”;
- не считать отсутствие ключа ошибкой.

---

## 18. Безопасность

### 18.1. Запуск не от root

Backend не должен запускаться от `root`.

Рекомендуемый пользователь:

```bash
minecraft
```

### 18.2. Ограничение файлового менеджера

Файловый менеджер должен работать только внутри:

```text
/srv/mc-panel/servers/{server_id}
```

Запрещено:

```text
../../
/etc
/root
/home
/proc
/sys
/dev
```

### 18.3. Секреты

К секретам относятся:

- Telegram bot token;
- RCON password;
- session secret;
- JWT secret.

Требования:

- не показывать полностью;
- не писать в логи;
- не отправлять на frontend без маски;
- хранить отдельно от публичных настроек.

### 18.4. Консольные команды

Опасные команды:

```text
stop
op
deop
save-off
reload
ban
pardon
whitelist
difficulty
gamemode
```

Для них должна быть отдельная permission или подтверждение.

### 18.5. Загрузка `.jar`

Загрузка `.jar` — это фактически разрешение выполнить код на сервере.

Доступ:

```text
только Owner/Admin с files.upload_core или servers.create
```

---

## 19. База данных

### 19.1. Таблица `users`

```sql
id INTEGER PRIMARY KEY
username TEXT UNIQUE
password_hash TEXT
language TEXT DEFAULT 'ru'
role_id INTEGER
is_active BOOLEAN
created_at DATETIME
updated_at DATETIME
```

### 19.2. Таблица `telegram_accounts`

```sql
id INTEGER PRIMARY KEY
user_id INTEGER
tg_id INTEGER UNIQUE
tg_username TEXT
language TEXT
is_allowed BOOLEAN
created_at DATETIME
```

### 19.3. Таблица `roles`

```sql
id INTEGER PRIMARY KEY
name TEXT UNIQUE
description TEXT
```

### 19.4. Таблица `permissions`

```sql
id INTEGER PRIMARY KEY
key TEXT UNIQUE
description TEXT
```

### 19.5. Таблица `role_permissions`

```sql
role_id INTEGER
permission_id INTEGER
```

### 19.6. Таблица `audit_log`

```sql
id INTEGER PRIMARY KEY
user_id INTEGER
action TEXT
target_type TEXT
target_id TEXT
details_json TEXT
ip_address TEXT
created_at DATETIME
```

---

## 20. Перенос старого проекта

### 20.1. Перенести почти напрямую

| Старый компонент | Новый компонент |
|---|---|
| `ServerSystem` | `MinecraftServerManager`, `RconService`, `MetricsService` |
| `PropertiesCustomizer` | `ServerPropertiesService` |
| `Locales` | `LocalizationService` |
| `telegram_bot.py` | `bot/telegram_bot.py`, но без Pipe |
| `keyboards.py` | `bot/keyboards.py` |
| `server_settings_window.py` | `QuickPropertiesPage` + backend validation |
| `upload_window.py` | `CoreUploadPage` |
| `cores_list_window.py` | `ServersPage` |
| `settings_window.py` | `PanelSettingsPage`, `TelegramSettingsPage` |

### 20.2. Не переносить напрямую

- PyQt UI-файлы;
- `ProcessConnector` как центральную архитектуру;
- Windows-пути;
- глобальный `profile_info` Telegram-бота;
- жёстко заданный RCON-пароль;
- старую модель `Users` без ролей.

---

## 21. Нефункциональные требования

### 21.1. Производительность

- Dashboard обновляется каждые 1–5 секунд.
- Логи идут через WebSocket без перезагрузки страницы.
- Последние 3000–10000 строк логов хранятся в памяти.
- Метрики процесса не должны сильно нагружать VM.

### 21.2. Надёжность

- backend должен корректно переживать падение Minecraft-процесса;
- состояние процесса должно восстанавливаться после перезапуска backend;
- при stop сначала отправлять `stop` в stdin/RCON;
- затем `terminate`;
- затем `kill` как крайний вариант.

### 21.3. Расширяемость

Архитектура должна позволять в будущем:

- запускать несколько серверов одновременно;
- добавить Docker-контейнеры для серверов;
- добавить backup scheduler;
- добавить магазин модов/плагинов;
- добавить полноценную хостинг-панель.

---

## 22. Этапы разработки

### Этап 1 — Backend core

- создать FastAPI-проект;
- реализовать `ServerInstanceService`;
- реализовать `servers.json`;
- реализовать `active_server_id`;
- перенести запуск/остановку из `ServerSystem`;
- сделать `status/work-data`;
- сделать чтение логов.

Результат:

```text
сервер можно выбрать и запустить через API.
```

### Этап 2 — Web Dashboard + Console

- создать Vue frontend;
- Dashboard;
- `Start/Stop/Restart`;
- status;
- metrics;
- WebSocket console;
- send command.

Результат:

```text
Minecraft-сервер управляется через браузер.
```

### Этап 3 — Multi-server manager

- список серверов;
- создать сервер;
- загрузить jar;
- импортировать папку;
- сделать активным;
- удалить сервер;
- настройки запуска.

Результат:

```text
можно одной кнопкой переключать активный сервер.
```

### Этап 4 — Quick server.properties editor

- quick settings;
- raw editor;
- backup;
- RCON enable;
- generate RCON password;
- MOTD;
- `server-icon.png`.

Результат:

```text
основные настройки сервера редактируются через сайт.
```

### Этап 5 — File Manager

- просмотр файлов;
- upload/download;
- edit text;
- rename/delete;
- mods/config/world;
- ограничения безопасности.

Результат:

```text
админ может управлять папкой сервера через сайт.
```

### Этап 6 — Users and permissions

- login;
- users;
- roles;
- permissions;
- audit log;
- защита API.

Результат:

```text
панель становится многопользовательской.
```

### Этап 7 — Telegram Bot

- перенести aiogram-бота;
- подключить к backend-сервисам;
- роли и права;
- выбор активного сервера;
- локализация;
- команды статуса/запуска/консоли.

Результат:

```text
Telegram-бот управляет тем же активным сервером, что и сайт.
```

### Этап 8 — Deployment

- systemd unit;
- nginx reverse proxy;
- HTTPS;
- отдельный Linux-пользователь;
- автозапуск backend;
- автозапуск Telegram-бота по настройке;
- документация установки.

---

## 23. Критерии приёмки MVP

MVP считается готовым, если выполнено:

1. Backend запускается на Linux VM.
2. Можно создать минимум два Server Instance.
3. Можно выбрать активный сервер.
4. Нельзя переключить активный сервер, пока он запущен.
5. Кнопка Start запускает выбранный активный сервер.
6. Кнопка Stop корректно останавливает сервер.
7. Web-консоль показывает live-логи.
8. Через web-консоль можно отправить команду.
9. Dashboard показывает статус, uptime, online, CPU/RAM.
10. Quick editor редактирует основные `server.properties`.
11. RCON можно включить автоматически.
12. MOTD можно изменить через сайт.
13. `server-icon.png` можно загрузить через сайт.
14. Файловый менеджер не позволяет выйти за папку сервера.
15. Есть хотя бы Owner/Admin user.
16. Есть русская локализация сайта и бота.
17. Telegram-бот может запустить/остановить активный сервер.

---

## 24. Итоговая формулировка проекта

Разрабатываемая система — это **web-панель управления несколькими Minecraft Server Instances**, работающая на Linux VM внутри Proxmox.

Основной сценарий:

1. Админ загружает или импортирует несколько серверных папок.
2. Каждая папка регистрируется как отдельный Server Instance.
3. Админ выбирает активный сервер одной кнопкой.
4. Dashboard, Console, File Manager, Properties Editor и Telegram-бот работают с активным сервером.
5. Активный сервер можно запустить, остановить, настроить и обслуживать через сайт или Telegram.

Главная архитектурная идея:

```text
Web GUI + Telegram Bot
        ↓
единый Backend
        ↓
активный Minecraft Server Instance
```

Старый проект использовать как источник уже готовой логики, но не переносить старую PyQt/Pipe-архитектуру напрямую.
