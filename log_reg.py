
from BD_wock import in_bd, add_user




def log(message):
    if in_bd(message.from_user.id) == False:
        return 1
    else:
        return 0





def registration(message):
    if str(message.text) == "123":
        return 1
    else:
        return 0















