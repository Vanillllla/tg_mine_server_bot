from BD_wock import in_bd

def log(message):
    if in_bd(message.from_user.id) == False:
        return 1
    else:
        return 0

def registration(message):
    if str(message.text) == "Go_V_Maincraft":
        return 1
    else:
        return 0
