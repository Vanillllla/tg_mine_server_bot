import json
import os
import shutil
from pathlib import Path  # Python 3.4+

class DirsManager:
    def __init__(self):
        if not os.path.isdir('Servers') :
            Path('Servers').mkdir(parents=True, exist_ok=True)
        if not os.path.isfile('cores.json') :
            with open('cores.json', 'w', encoding='utf-8') as f:
                json.dump({}, f, ensure_ascii=False, indent=4)
        if not os.path.isfile('program_settings.json') :
            with open('program_settings.json', 'w', encoding='utf-8') as f:
                json.dump({}, f, ensure_ascii=False, indent=4)
        # if not os.path.isfile('cores_list.json') :
        #     with open('cores_list.json', 'w', encoding='utf-8') as f:
        #         json.dump({}, f, ensure_ascii=False, indent=4)
        if not os.path.isdir('downloads_cores') :
            Path('downloads_cores').mkdir(parents=True, exist_ok=True)

    @staticmethod
    def new_core_upload(core_name):
        with open('cores.json', 'r', encoding='utf-8') as f:
            cores = json.load(f)

        if len(cores) : key = (max([int(i) for i in cores.keys()]) + 1)
        else: key = 1
        print(key)
        Path("downloads_cores/" + core_name).rename("downloads_cores/" + str(key) + "_" + core_name)

        cores[str(key)] = {
            "name": core_name,
            "xms": 256,
            "xmx": 2048,
            "core_name": "",
            "core_folder": "",
            "eula_accept": False,
            "jave_version": "",
            "java_path": ""
        }
        with open('cores.json', 'w', encoding='utf-8') as f:
            json.dump(cores, f, ensure_ascii=False, indent=4)


    @staticmethod
    def core_available(core_name: object) :
        try:
            with open('cores.json', 'r', encoding='utf-8') as f:
                cores = json.load(f)
            core_id = core_name.split('_')[0]
            print(core_id, core_name)
            if cores[str(core_id)]["core_folder"] == "":
                Path(f"./Servers/{core_id}_server_{cores[f'{core_id}']['name'][:-4]}/").mkdir(parents=True, exist_ok=True)
                shutil.move(f"./downloads_cores/{core_id}_{cores[f'{core_id}']['name']}", f"./Servers/{core_id}_server_{cores[f'{core_id}']['name'][:-4]}/{core_id}_{cores[f'{core_id}']['name']}" )
                cores[str(core_id)]["core_folder"] = f"./Servers/{core_id}_server_{cores[f'{core_id}']['name'][:-4]}"
            with open('cores.json', 'w', encoding='utf-8') as f:
                json.dump(cores, f, ensure_ascii=False, indent=4)
        except Exception as e:
            print(e)
        finally:
            return core_id or e

# if __name__ == '__main__':
#     manager = DirsManager()
