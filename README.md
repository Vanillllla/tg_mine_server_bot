[![Python](https://img.shields.io/badge/Python-3.13%2B-green)](https://www.python.org/downloads/)

# Minecraft Server Telegram Bot

Desktop app for managing a local Minecraft server and controlling it from Telegram.

## Project Structure

```text
app/
  core/         # shared paths and filesystem helpers
  gui/          # PyQt windows, dialogs, themes
  services/     # Telegram bot and Minecraft server control
config/         # JSON configuration files
resources/
  assets/icons/ # application icons
  ui/           # Qt Designer .ui files
downloads_cores/
Servers/
main.py
```

## Run

```bash
python main.py
```
