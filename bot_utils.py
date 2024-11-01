from telebot import TeleBot, types
from bot_utils import *
import requests
from io import BytesIO


def list_commands():
    return [
        "/schedule_group",
        "/schedule_group_image",
        "/schedule_classroom",
        "/schedule_classroom_image",
        "/schedule_teacher",
        "/schedule_teacher_image"
    ]


def utils_ask_date(message, bot, type):
    # URL для получения списка дат
    url_date = 'http://aesotq1.duckdns.org:8000/list/date/'

    group = message.text
    try:
        # Выполняем запрос к серверу
        response = requests.get(url_date)
        response.raise_for_status()
        data = response.json()

        # Проверяем наличие "files" и берём даты
        if "files" in data:
            dates = data["files"][-3:]

            # Создаём клавиатуру для выбора даты
            keyboard = types.InlineKeyboardMarkup()
            for date_str in dates:
                keyboard.add(types.InlineKeyboardButton(text=date_str, callback_data=f"{type}|{group}|{date_str}"))

            bot.send_message(message.chat.id, "Выберите нужную дату:", reply_markup=keyboard)
        else:
            bot.send_message(message.chat.id, "Ошибка: данные о датах не найдены.")

    except requests.exceptions.RequestException as e:
        bot.send_message(message.chat.id, f"Ошибка при получении дат: {e}")


def utils_get_schedule_url(url):
    response = requests.get(url)
    response.raise_for_status()
    return response.json()

def utils_get_schedule_image(url,date):
    url_image = f'http://aesotq1.duckdns.org:8000/generate_schedule_image/?day={date}'
    json = utils_get_schedule_url(url)
    response_image = requests.post(url_image, json=json)
    response_image.raise_for_status()

    # Проверка и использование ответа
    if response_image.status_code == 200:
        print("Запрос успешно выполнен")
    else:
        print(f"Ошибка: {response_image.status_code}")
    # Преобразование ответа в изображение
    return BytesIO(response_image.content)
