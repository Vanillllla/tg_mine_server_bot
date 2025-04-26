import sqlite3

def in_bd(user_id):
    connection = sqlite3.connect('my_database.db')
    cursor = connection.cursor()
    cursor.execute('SELECT users_tg_id FROM Users WHERE users_tg_id = ?', (user_id,))
    results = cursor.fetchall()
    if results:
        connection.commit()
        connection.close()
        return True
    else:
        connection.commit()
        connection.close()
        return False

def add_user(user_id):
    connection = sqlite3.connect('my_database.db')
    cursor = connection.cursor()
    cursor.execute('INSERT INTO Users (users_tg_id) VALUES (?)', (str(user_id),))
    connection.commit()
    connection.close()
