import requests
from telebot import TeleBot, types

bot = TeleBot('6670908590:AAHOdqarDZRxv3kre35zyQjynQtEe_hSphc')

url_group_pg = 'http://aesotq1.duckdns.org:8000/edit_schedule/group_pg/?group=%D0%91%D0%9F1-111&subgroup=1&day=30.10.2024'

# URL для получения списка дат
url_date = 'http://aesotq1.duckdns.org:8000/list/date/'


@bot.message_handler(commands=['start'])
def main(message):
    bot.send_message(message.chat.id, 'Привет, чем я могу помочь?')


@bot.message_handler(commands=['schedule_group'])
def ask_edit(message):
    bot.send_message(message.chat.id, 'Введите название группы (например БП1-110):')
    bot.register_next_step_handler(message, ask_date)


def ask_date(message):
    group = message.text

    try:
        # Выполняем запрос к серверу
        response = requests.get(url_date)
        response.raise_for_status()
        data = response.json()

        # Проверяем наличие "files" и берём даты
        if "files" in data:
            dates = sorted(data["files"], reverse=True)[:3]
            dates.sort()

            # Создаём клавиатуру для выбора даты
            keyboard = types.InlineKeyboardMarkup()
            for date_str in dates:
                keyboard.add(types.InlineKeyboardButton(text=date_str, callback_data=f"{group}|{date_str}"))

            bot.send_message(message.chat.id, "Выберите нужную дату:", reply_markup=keyboard)
        else:
            bot.send_message(message.chat.id, "Ошибка: данные о датах не найдены.")

    except requests.exceptions.RequestException as e:
        bot.send_message(message.chat.id, f"Ошибка при получении дат: {e}")


@bot.callback_query_handler(func=lambda call: True)
def send_schedule(call):
    group, date = call.data.split('|')
    url_group = f'http://aesotq1.duckdns.org:8000/edit_schedule/group/?group={group}&day={date}'

    try:
        # Запрос на получение детального расписания
        response = requests.get(url_group)
        response.raise_for_status()
        schedule_data = response.json()

        # Разделение расписания по подгруппам
        schedule_subgroup_1 = f"Расписание для группы {group} (подгруппа 1) на {date}:\n\n"
        schedule_subgroup_2 = f"Расписание для группы {group} (подгруппа 2) на {date}:\n\n"

        for entry in schedule_data["results"]:
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


bot.polling(none_stop=True)
