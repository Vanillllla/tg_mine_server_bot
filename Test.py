# # import telebot
# # from telebot import types
# #
# # bot = telebot.TeleBot('7563076857:AAHf5MdmVCDskWN9IL1tNz4eXuwawZ0alMg')
# #
# # @bot.message_handler(commands=['start'])
# # def start(message):
# #     main_menu(message)
# #
# # # Основное меню
# # def main_menu(message):
# #     markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
# #     btn1 = types.KeyboardButton("📂 Подменю")
# #     btn2 = types.KeyboardButton("❓ Помощь")
# #     markup.add(btn1, btn2)
# #     bot.send_message(message.chat.id, "Выбери пункт меню:", reply_markup=markup)
# #
# # # Обработка нажатий
# # @bot.message_handler(func=lambda message: True)
# # def handle_message(message):
# #     if message.text == "📂 Подменю":
# #         submenu(message)
# #     elif message.text == "🔙 Назад":
# #         main_menu(message)
# #     elif message.text == "❓ Помощь":
# #         bot.send_message(message.chat.id, "Это просто тестовое меню.")
# #     elif message.text == "🧪 Кнопка A":
# #         bot.send_message(message.chat.id, "Ты нажал кнопку A!")
# #     elif message.text == "⚙️ Кнопка B":
# #         bot.send_message(message.chat.id, "Ты нажал кнопку B!")
# #     else:
# #         bot.send_message(message.chat.id, "Не понял 🤔")
# #
# # # Подменю
# # def submenu(message):
# #     markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
# #     btn1 = types.KeyboardButton("🧪 Кнопка A")
# #     btn2 = types.KeyboardButton("⚙️ Кнопка B")
# #     btn_back = types.KeyboardButton("🔙 Назад")
# #     markup.add(btn1, btn2)
# #     markup.add(btn_back)
# #     bot.send_message(message.chat.id, "Это подменю. Выбери действие:", reply_markup=markup)
# #
# # bot.polling(none_stop=True, interval=0)
# #
#
# #
# # import telebot
# # from telebot import types
# #
# # bot = telebot.TeleBot("7563076857:AAHf5MdmVCDskWN9IL1tNz4eXuwawZ0alMg")
# #
# # # Хранилище состояний пользователей
# # user_state = {}
# #
# # STATE_MAIN_MENU = "main"
# # STATE_SUBMENU = "submenu"
# #
# #
# # @bot.message_handler(commands=['start'])
# # def start(message):
# #     user_state[message.chat.id] = STATE_MAIN_MENU
# #     main_menu(message)
# #
# #
# # # Главное меню
# # def main_menu(message):
# #     markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
# #     markup.add(types.KeyboardButton("📂 Подменю"), types.KeyboardButton("❓ Помощь"))
# #     bot.send_message(message.chat.id, "Главное меню. Выбери действие:", reply_markup=markup)
# #
# #
# # # Подменю
# # def submenu(message):
# #     markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
# #     markup.add(types.KeyboardButton("🧪 Кнопка A"), types.KeyboardButton("⚙️ Кнопка B"))
# #     markup.add(types.KeyboardButton("🔙 Назад"))
# #     bot.send_message(message.chat.id, "submenu", reply_markup=markup)
# #
# #     # Устанавливаем состояние
# #     user_state[message.from_user.id] = STATE_SUBMENU
# #
# #
# # # Обработка всех текстовых сообщений
# # @bot.message_handler(func=lambda message: True)
# # def handle_all_messages(message):
# #     state = user_state.get(message.chat.id, STATE_MAIN_MENU)
# #
# #     if state == STATE_MAIN_MENU:
# #         # Принимаем только кнопки в главном меню
# #         if message.text == "📂 Подменю":
# #             submenu(message)
# #         elif message.text == "❓ Помощь":
# #             bot.send_message(message.chat.id, "Это помощь по боту.")
# #         else:
# #             bot.send_message(message.chat.id, "В главном меню нельзя писать текстовые сообщения.")
# #
# #     elif state == STATE_SUBMENU:
# #         if message.text == "🔙 Назад":
# #             user_state[message.chat.id] = STATE_MAIN_MENU
# #             main_menu(message)
# #         elif message.text == "🧪 Кнопка A":
# #             bot.send_message(message.chat.id, "Ты нажал A!")
# #         elif message.text == "⚙️ Кнопка B":
# #             bot.send_message(message.chat.id, "Ты нажал B!")
# #         else:
# #             bot.send_message(message.chat.id, f"Ты написал: {message.text}")
# #
# #
# # bot.polling(none_stop=True, interval=0)
#
#
#
# import subprocess
# import threading
# import time
# import psutil
#
# class ServerManager:
#     def __init__(self, jar_file, cwd, xmx="12G", xms="4G"):
#         self.jar_file = jar_file
#         self.cwd = cwd
#         self.xmx = xmx
#         self.xms = xms
#         self.process = None
#         self.log_buffer = []
#         self._reader_thread = None
#         self._lock = threading.Lock()
#
#     def _read_output(self):
#         while self.process and self.process.stdout:
#             line = self.process.stdout.readline()
#             if line:
#                 with self._lock:
#                     self.log_buffer.append(line.strip())
#                     print(line.strip())  # Для вывода в терминал
#
#     def start(self):
#         if self.process is None:
#             self.process = subprocess.Popen(
#                 ["java", f"-Xmx{self.xmx}", f"-Xms{self.xms}", "-jar", self.jar_file, "nogui"],
#                 cwd=self.cwd,
#                 stdin=subprocess.PIPE,
#                 stdout=subprocess.PIPE,
#                 stderr=subprocess.STDOUT,
#                 text=True,
#                 bufsize=1
#             )
#             self._reader_thread = threading.Thread(target=self._read_output, daemon=True)
#             self._reader_thread.start()
#             print("✅ Сервер запущен.")
#         else:
#             print("⚠️ Сервер уже запущен.")
#
#     def stop(self):
#         if self.process:
#             try:
#                 parent = psutil.Process(self.process.pid)
#                 children = parent.children(recursive=True)
#                 for child in children:
#                     child.terminate()
#                 psutil.wait_procs(children, timeout=5)
#                 parent.terminate()
#                 parent.wait(5)
#                 print("🛑 Сервер остановлен.")
#             except Exception as e:
#                 print(f"❌ Ошибка при остановке: {e}")
#             self.process = None
#         else:
#             print("⚠️ Сервер не запущен.")
#
#     def send_command(self, command):
#         if self.process is None or self.process.stdin is None:
#             print("⚠️ Сервер не запущен или stdin недоступен.")
#             return
#
#         try:
#             with self._lock:
#                 old_log_len = len(self.log_buffer)
#
#             self.process.stdin.write(command + "\n")
#             self.process.stdin.flush()
#             print(f"✅ Команда отправлена: {command}")
#
#             time.sleep(1.5)
#
#             with self._lock:
#                 new_logs = self.log_buffer[old_log_len:]
#
#             if new_logs:
#                 print("📨 Ответ сервера:")
#                 for line in new_logs:
#                     print(line)
#             else:
#                 print("🔇 Сервер не вернул новых строк.")
#
#         except Exception as e:
#             print(f"❌ Ошибка при отправке команды: {e}")
#
#
#
#
#
#



print(''.join(str(i) for i in range(1,10))+'0'*10)



















#
