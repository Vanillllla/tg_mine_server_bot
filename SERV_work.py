import subprocess
import os
from time import sleep

def serv(code):
    if code == 0:
        #os.startfile("C:/Users/Ivan/Documents/GitHub/tg_mine_server_bot/Server/start.bat")
        # subprocess.call("C:/Users/Ivan/Documents/GitHub/tg_mine_server_bot/Server/start.bat")

        # sv_sp = subprocess.Popen("cd server")  -Xmx12G -Xms4G -jar server/forge-1.12.2-14.23.5.2859.jar
        sv_sp = subprocess.Popen("java -Xmx12G -Xms4G -jar forge-1.12.2-14.23.5.2859.jar")
        print("server started")
        # except:
        #     print("Error start")


    if code == 2:
        # os.system("taskkill /im firefox.exe")
        try:
            sv_sp.terminate()
            print("server terminated")
        except:
            print("Error stop")
        # os.stopfile("C:/Users/Ivan/Documents/GitHub/tg_mine_server_bot/Server/start.bat")


serv(0)

sleep(20)