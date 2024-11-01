from telebot import TeleBot, types
from bot_utils import *
import requests
from io import BytesIO

bot = TeleBot('6670908590:AAHOdqarDZRxv3kre35zyQjynQtEe_hSphc')

url_group_pg = 'http://aesotq1.duckdns.org:8000/edit_schedule/group_pg/?group=%D0%91%D0%9F1-111&subgroup=1&day=30.10.2024'

# URL для получения списка дат
url_date = 'http://aesotq1.duckdns.org:8000/list/date/'


@bot.message_handler(commands=['start'])
def main(message):
    text = ""
    for command in list_commands():
        text += command + "\n"
    bot.send_message(message.chat.id, text)


@bot.message_handler(commands=['schedule_group'])
def ask_edit(message):
    bot.send_message(message.chat.id, 'Введите название группы (например: БП2-112):')
    bot.register_next_step_handler(message, lambda msg: ask_date(msg, message_type="group_text"))


@bot.message_handler(commands=['schedule_group_image'])
def ask_edit(message):
    bot.send_message(message.chat.id, 'Введите название группы (например: БП2-112):')
    bot.register_next_step_handler(message, lambda msg: ask_date(msg, message_type="group_image"))


@bot.message_handler(commands=['schedule_classroom'])
def ask_edit(message):
    bot.send_message(message.chat.id, 'Введите номер кабинета (например: 547, РЦ-7):')
    bot.register_next_step_handler(message, lambda msg: ask_date(msg, message_type="classroom_text"))


@bot.message_handler(commands=['schedule_classroom_image'])
def ask_edit(message):
    bot.send_message(message.chat.id, 'Введите номер кабинета (например: 547, РЦ-7):')
    bot.register_next_step_handler(message, lambda msg: ask_date(msg, message_type="classroom_image"))


@bot.message_handler(commands=['schedule_teacher'])
def ask_edit(message):
    bot.send_message(message.chat.id, 'Введите Фамилию И.О. преподавателя (например: Иванов И.И.)')
    bot.register_next_step_handler(message, lambda msg: ask_date(msg, message_type="teacher_text"))


@bot.message_handler(commands=['schedule_teacher_image'])
def ask_edit(message):
    bot.send_message(message.chat.id, 'Введите Фамилию И.О. преподавателя (например: Иванов И.И.):')
    bot.register_next_step_handler(message, lambda msg: ask_date(msg, message_type="teacher_image"))


def ask_date(message, message_type):
    utils_ask_date(message, bot, message_type)


@bot.callback_query_handler(func=lambda call: True)
def send_schedule(call):
    if 'group_text' in call.data.split('|')[0]:
        message_type, group, date = call.data.split('|')
        url_group = f'http://aesotq1.duckdns.org:8000/edit_schedule/group/?group={group}&day={date}'

        try:
            # Разделение расписания по подгруппам
            schedule_subgroup_1 = f"Расписание для группы {group} (подгруппа 1) на {date}:\n\n"
            schedule_subgroup_2 = f"Расписание для группы {group} (подгруппа 2) на {date}:\n\n"

            for entry in utils_get_schedule_url(url_group)["results"]:
                lesson_text = (
                    f"{entry['lesson_number']} - {entry['subject']}\n"
                    f"Преподаватель: {entry['instructor']}\n"
                    f"Кабинет: {entry['classroom']}\n\n"
                )

                # Общая пара (подгруппа 0) добавляется в оба расписания
                if entry["subgroup"] == 0:
                    schedule_subgroup_1 += lesson_text
                    schedule_subgroup_2 += lesson_text
                elif entry["subgroup"] == 1:
                    schedule_subgroup_1 += lesson_text
                elif entry["subgroup"] == 2:
                    schedule_subgroup_2 += lesson_text

            # Отправляем расписание каждой подгруппе
            bot.send_message(call.message.chat.id, schedule_subgroup_1)
            bot.send_message(call.message.chat.id, schedule_subgroup_2)

        except requests.exceptions.RequestException as e:
            bot.send_message(call.message.chat.id, f"Ошибка при получении расписания: {e}")
    if 'group_image' in call.data.split('|')[0]:
        message_type, group, date = call.data.split('|')
        url_group = f'http://aesotq1.duckdns.org:8000/edit_schedule/group/?group={group}&day={date}'
        try:
            bot.send_photo(call.message.chat.id, utils_get_schedule_image(url_group, date), caption=f"Расписание для группы {group} на {date}")
        except requests.exceptions.RequestException as e:
            bot.send_message(call.message.chat.id, f"Ошибка при получении расписания: {e}")
    if 'classroom_text' in call.data.split('|')[0]:
        message_type, classroom, date = call.data.split('|')
        url_group = f'http://aesotq1.duckdns.org:8000/edit_schedule/classroom/?classroom={classroom}&day={date}'

        try:
            schedule = ""
            for entry in utils_get_schedule_url(url_group)["results"]:
                lesson_text = (
                    f"{entry['lesson_number']} - {entry['subject']}\n"
                    f"Преподаватель: {entry['instructor']}\n"
                    f"Группа: {entry['classroom']}\n\n"
                )
                schedule += lesson_text
            bot.send_message(call.message.chat.id, schedule)
        except requests.exceptions.RequestException as e:
            bot.send_message(call.message.chat.id, f"Ошибка при получении расписания: {e}")
    if 'classroom_image' in call.data.split('|')[0]:
        message_type, classroom, date = call.data.split('|')
        url_group = f'http://aesotq1.duckdns.org:8000/edit_schedule/classroom/?classroom={classroom}&day={date}'
        try:
            bot.send_photo(call.message.chat.id, utils_get_schedule_image(url_group, date),
                           caption=f"Расписание для кабинета {classroom} на {date}")
        except requests.exceptions.RequestException as e:
            bot.send_message(call.message.chat.id, f"Ошибка при получении расписания: {e}")
    if 'teacher_text' in call.data.split('|')[0]:
        message_type, instructor, date = call.data.split('|')
        url_group = f'http://aesotq1.duckdns.org:8000/edit_schedule/instructor/?instructor={instructor}&day={date}'

        try:
            schedule = ""
            for entry in utils_get_schedule_url(url_group)["results"]:
                lesson_text = (
                    f"{entry['lesson_number']} - {entry['subject']}\n"
                    f"Преподаватель: {entry['instructor']}\n"
                    f"Кабинет: {entry['classroom']}\n\n"
                )
                schedule += lesson_text
            bot.send_message(call.message.chat.id, schedule)
        except requests.exceptions.RequestException as e:
            bot.send_message(call.message.chat.id, f"Ошибка при получении расписания: {e}")
    if 'teacher_image' in call.data.split('|')[0]:
        message_type, instructor, date = call.data.split('|')
        url_group = f'http://aesotq1.duckdns.org:8000/edit_schedule/instructor/?instructor={instructor}&day={date}'
        try:
            bot.send_photo(call.message.chat.id, utils_get_schedule_image(url_group, date),
                           caption=f"Расписание для преподавателя {instructor} на {date}")
        except requests.exceptions.RequestException as e:
            bot.send_message(call.message.chat.id, f"Ошибка при получении расписания: {e}")

bot.polling(none_stop=True)
