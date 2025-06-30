import os

cmd = "C:/Users/Ivan/AppData/Roaming/.minecraft/mods"

try:
    out_put = os.listdir(cmd)
    for i in range(len(out_put)):
        print(out_put[i])
except FileNotFoundError:
    print(f"Ошибка: папка {cmd} не найдена")
except PermissionError:
    print(f"Ошибка: нет доступа к папке {cmd}")
except Exception as e:
    print(f"Произошла ошибка: {e}")
