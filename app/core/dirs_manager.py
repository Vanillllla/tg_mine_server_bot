import json
import shutil
from pathlib import Path

from app.core.paths import CONFIG_DIR, DOWNLOADS_DIR, SERVERS_DIR, config_path


class DirsManager:
    def __init__(self):
        SERVERS_DIR.mkdir(parents=True, exist_ok=True)
        DOWNLOADS_DIR.mkdir(parents=True, exist_ok=True)
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)

        cores_file = config_path("cores.json")
        settings_file = config_path("program_settings.json")

        if not cores_file.is_file():
            cores_file.write_text("{}", encoding="utf-8")
        if not settings_file.is_file():
            settings_file.write_text("{}", encoding="utf-8")

    @staticmethod
    def new_core_upload(core_name):
        cores_file = config_path("cores.json")
        with cores_file.open("r", encoding="utf-8") as file:
            cores = json.load(file)

        key = max((int(item) for item in cores.keys()), default=0) + 1
        source = DOWNLOADS_DIR / core_name
        target = DOWNLOADS_DIR / f"{key}_{core_name}"
        source.rename(target)

        cores[str(key)] = {
            "name": core_name,
            "xms": 256,
            "xmx": 2048,
            "core_name": "",
            "core_folder": "",
            "eula_accept": False,
            "jave_version": "",
            "java_path": "",
        }
        with cores_file.open("w", encoding="utf-8") as file:
            json.dump(cores, file, ensure_ascii=False, indent=4)

    @staticmethod
    def core_available(core_name: object):
        core_id = None
        try:
            cores_file = config_path("cores.json")
            with cores_file.open("r", encoding="utf-8") as file:
                cores = json.load(file)

            core_id = core_name.split("_")[0]
            core_info = cores[str(core_id)]
            if core_info["core_folder"] == "":
                server_dir = SERVERS_DIR / f"{core_id}_server_{core_info['name'][:-4]}"
                server_dir.mkdir(parents=True, exist_ok=True)
                shutil.move(
                    str(DOWNLOADS_DIR / f"{core_id}_{core_info['name']}"),
                    str(server_dir / f"{core_id}_{core_info['name']}"),
                )
                core_info["core_folder"] = str(server_dir)

            with cores_file.open("w", encoding="utf-8") as file:
                json.dump(cores, file, ensure_ascii=False, indent=4)
        except Exception as exc:
            print(exc)
            return exc
        return core_id

    @staticmethod
    def delete_core(core_id: str) -> bool:
        cores_file = config_path("cores.json")
        with cores_file.open("r", encoding="utf-8") as file:
            cores = json.load(file)

        core_id = str(core_id)

        if core_id not in cores:
            return False

        shutil.rmtree(cores[core_id]["core_folder"])

        del cores[core_id]
        with cores_file.open("w", encoding="utf-8") as file:
            json.dump(cores, file, ensure_ascii=False, indent=4)
        return True
