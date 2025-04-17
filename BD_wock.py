import sqlite3

def in_bd(user_id):
    connection = sqlite3.connect('my_database.db')
    cursor = connection.cursor()
    cursor.execute('SELECT users_tg_id FROM Users WHERE users_tg_id = ?', (user_id,))
    results = cursor.fetchall()
    # print(results) #################################################################################
    if results:
        connection.commit()
        connection.close()
        return True
    else:
        connection.commit()
        connection.close()
        # print("New user") ##################################################################################
        return False

def add_user(user_id):
    connection = sqlite3.connect('my_database.db')
    cursor = connection.cursor()
    cursor.execute('INSERT INTO Users (users_tg_id) VALUES (?)', (str(user_id),))
    # print("reg gg!!!")
    # cursor.execute('SELECT * FROM Users ')
    # results = cursor.fetchall()
    # print(results)
    connection.commit()
    connection.close()












## Создаем подключение к базе данных (файл my_database.db будет создан)
#connection = sqlite3.connect('my_database.db')
#cur = connection.cursor()
#
#sq = sqlite3.connect('my_database.db')
#
## Создаем таблицу Users
## cursor.execute('''CREATE TABLE IF NOT EXISTS Users (id INTEGER PRIMARY KEY, users_tg_id INTEGER NOT NULL, name TEXT NOT NULL, staus INTEGER NOT NULL)''')
#
#
#cur.execute('INSERT INTO Users (users_tg_id, name, status) VALUES (?, ?, ?)', (879878899, 'newuser@e', 0))
#
#cur.execute('SELECT users_tg_id FROM Users')
#results = cur.fetchall()
#
#res = []
#
#for row in results:
#    res.append(str(row)[1:-2])
#print(res)
#
## Сохраняем изменения и закрываем соединение
#connection.commit()
#connection.close()