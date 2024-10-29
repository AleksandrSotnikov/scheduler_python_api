import pandas as pd
import json
import re
from datetime import datetime


def load_excel_data(path):
    """Чтение данных из Excel файла."""
    return pd.read_excel(path)


def extract_date_info(file_path, date_info_str):
    """Извлекает дату, день недели и номер недели из данных файла и строки."""
    date_match = re.search(r'(\d{2}\.\d{2}\.\d{4})', file_path)
    day_of_week_match = re.search(r'\((.*?)\)', date_info_str)
    week_number_match = re.search(r'Неделя (\d+)', date_info_str)

    file_date = datetime.strptime(date_match.group(), '%d.%m.%Y').date() if date_match else None
    if file_date is None:
        raise ValueError("Не удалось извлечь дату из имени файла")

    days_mapping = {
        "понедельник": 1, "вторник": 2, "среда": 3,
        "четверг": 4, "пятница": 5, "суббота": 6, "воскресенье": 7
    }
    day_of_week_str = day_of_week_match.group(1).lower() if day_of_week_match else None
    day_of_week = days_mapping.get(day_of_week_str, None)
    week_number = int(week_number_match.group(1)) if week_number_match else None

    return file_date, day_of_week, week_number


def load_main_schedule(path):
    """Загружает основное расписание из JSON файла."""
    with open(path, 'r', encoding='utf-8') as file:
        return json.load(file)["results"]


def clean_and_convert(value, default=0):
    """Очищает строку от лишних пробелов и преобразует к целому числу."""
    if pd.isna(value):
        return default
    try:
        cleaned_value = str(value).replace("\xa0", "").strip()
        return int(cleaned_value) if cleaned_value.isdigit() else default
    except ValueError:
        return default


def create_schedule_entries(row, week_number, day_of_week):
    """Создает записи для обновления и удаления на основе строки из Excel."""
    entryAdd = {
        "week_number": week_number,
        "day_of_week": day_of_week,
        "group_name": row.iloc[0].strip() if not pd.isna(row.iloc[0]) else "",
        "lesson_number": clean_and_convert(row.iloc[1]),
        "subgroup": clean_and_convert(row.iloc[6]),
        "subject": row.iloc[7].strip() if not pd.isna(row.iloc[7]) else "",
        "instructor": row.iloc[8].strip() if not pd.isna(row.iloc[8]) else "",
        "classroom": str(row.iloc[9]).strip() if not pd.isna(row.iloc[9]) else ""
    }

    entryDelete = {
        "week_number": week_number,
        "day_of_week": day_of_week,
        "group_name": row.iloc[0].strip() if not pd.isna(row.iloc[0]) else "",
        "lesson_number": clean_and_convert(row.iloc[1]),
        "subgroup": clean_and_convert(row.iloc[2]),
        "subject": row.iloc[3].strip() if not pd.isna(row.iloc[3]) else "",
        "instructor": row.iloc[4].strip() if not pd.isna(row.iloc[4]) else "",
        "classroom": str(row.iloc[5]).strip() if not pd.isna(row.iloc[5]) else ""
    }
    return entryAdd, entryDelete


def update_schedule(filtered_schedule, deleted_schedule, updated_schedule):
    """Удаляет из расписания записи, присутствующие в deleted_schedule, и добавляет записи из updated_schedule."""
    filtered_schedule = [
        record for record in filtered_schedule
        if not any(
            record['group_name'] == del_record['group_name'] and
            record['lesson_number'] == del_record['lesson_number'] and
            record['subgroup'] == del_record['subgroup'] and
            record['subject'] == del_record['subject']
            for del_record in deleted_schedule
        )
    ]
    filtered_schedule.extend(updated_schedule)

    return filtered_schedule


def save_schedule_to_json(schedule, path):
    """Сохраняет расписание в JSON файл."""
    with open(path, 'w', encoding='utf-8') as file:
        json.dump(schedule, file, ensure_ascii=False, indent=4)


# Основной код
def get_editor_schedule_by_date(main_schedule_json_path, new_excel_path):
    # main_schedule_json_path = 'schedule.json'
    # new_excel_path = 'temp/28.10.2024.xlsx'
    excel_data = load_excel_data(new_excel_path)
    date_info_str = excel_data.iloc[0, 0]
    file_date, day_of_week, week_number = extract_date_info(new_excel_path, date_info_str)

    main_schedule = load_main_schedule(main_schedule_json_path)
    excel_data = excel_data[4:]

    updated_schedule = {"results": []}
    deleted_schedule = {"results": []}

    for _, row in excel_data.iterrows():
        entryAdd, entryDelete = create_schedule_entries(row, week_number, day_of_week)

        # Добавляем только те записи, где subject не пустой
        if entryAdd["subject"]:
            updated_schedule["results"].append(entryAdd)

        deleted_schedule["results"].append(entryDelete)

    filtered_schedule = {
        "results": [
            record for record in main_schedule
            if record["day_of_week"] == day_of_week and record["week_number"] == week_number
        ]
    }

    final_schedule = update_schedule(filtered_schedule["results"], deleted_schedule["results"],
                                     updated_schedule["results"])
    output_json_path = f'temp/json/edit/{datetime.strptime(str(file_date), "%Y-%m-%d").strftime("%d.%m.%Y")}.json'
    output_json_add_path = f'temp/json/add/{datetime.strptime(str(file_date), "%Y-%m-%d").strftime("%d.%m.%Y")}.json'
    output_json_remove_path = f'temp/json/remove/{datetime.strptime(str(file_date), "%Y-%m-%d").strftime("%d.%m.%Y")}.json'
    save_schedule_to_json({"results": final_schedule}, output_json_path)
    save_schedule_to_json({"results": updated_schedule["results"]}, output_json_add_path)
    save_schedule_to_json({"results": deleted_schedule["results"]}, output_json_remove_path)
    print(f"Обновленное расписание сохранено в файл: {output_json_path}")
    print(f"Обновленное добавленное расписание сохранено в файл: {output_json_add_path}")
    print(f"Обновленное удаленное расписание сохранено в файл: {output_json_remove_path}")
