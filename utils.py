# utils.py
import aiofiles
import json
from typing import List, Dict
from datetime import datetime
from fastapi import HTTPException

from models.schemas import ScheduleRecord, ScheduleResponse


async def load_and_filter_schedule(file_path: str, filter_key: str, filter_value: str) -> List[dict]:
    """Загружает расписание из указанного JSON файла и фильтрует его по указанному ключу и значению.

    Аргументы:
    - file_path (str): Путь к файлу JSON с расписанием.
    - filter_key (str): Ключ, по которому будет производиться фильтрация (например, "group_name").
    - filter_value (str): Значение, по которому будет производиться фильтрация.

    Возвращает:
    - List[dict]: Отфильтрованный список записей расписания.

    Исключения:
    - HTTPException: Если файл не найден или произошла ошибка при загрузке.
    """
    try:
        async with aiofiles.open(file_path, "r", encoding="utf-8") as f:
            schedule = json.loads(await f.read())["results"]
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Файл расписания не найден")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка загрузки расписания: {str(e)}")

    return [record for record in schedule if record.get(filter_key) == filter_value]


async def get_filtered_schedule(day: str, filter_key: str, filter_value: str, schedule_type: str) -> ScheduleResponse:
    """Универсальная функция для получения и фильтрации расписания по указанным параметрам.

    Аргументы:
    - day (str): Дата в формате DD.MM.YYYY, по которой загружается расписание.
    - filter_key (str): Ключ для фильтрации расписания (например, "group_name").
    - filter_value (str): Значение для фильтрации расписания (например, "Группа A").
    - schedule_type (str): Тип расписания, определяющий путь к файлу ("add" или "remove").

    Возвращает:
    - ScheduleResponse: Объект с отфильтрованным списком записей.
    """
    validate_date_format(day)
    file_path = f"temp/json/{schedule_type}/{day}.json"
    filtered_schedule = await load_and_filter_schedule(file_path, filter_key, filter_value)
    return ScheduleResponse(results=[ScheduleRecord(**record) for record in filtered_schedule])


def validate_date_format(date_str: str):
    """Проверяет, что дата соответствует формату DD.MM.YYYY.

    Аргументы:
    - date_str (str): Дата в строковом формате (например, "24.10.2024").

    Исключения:
    - HTTPException: Если дата не соответствует формату DD.MM.YYYY.
    """
    try:
        datetime.strptime(date_str, "%d.%m.%Y")
    except ValueError:
        raise HTTPException(status_code=400, detail="Неверный формат даты. Используйте формат DD.MM.YYYY.")


def load_classrooms_from_file(file_path: str) -> List[str]:
    """Загружает уникальные кабинеты из указанного JSON-файла."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            schedule = json.load(f).get("results", [])
            classrooms = {record["classroom"] for record in schedule if "classroom" in record}
        return list(classrooms)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"File {file_path} not found")
    except json.JSONDecodeError:
        raise HTTPException(status_code=500, detail=f"Failed to parse JSON file: {file_path}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def load_subjects_from_file(file_path: str) -> List[str]:
    """Загружает уникальные предметы из указанного JSON-файла."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            schedule = json.load(f).get("results", [])
            subjects = {record["subject"] for record in schedule if "subject" in record}
        return list(subjects)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"File {file_path} not found")
    except json.JSONDecodeError:
        raise HTTPException(status_code=500, detail=f"Failed to parse JSON file: {file_path}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def load_instructors_from_file(file_path: str) -> List[str]:
    """Загружает уникальных преподавателей из указанного JSON-файла."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            schedule = json.load(f).get("results", [])
            instructors = {record["instructor"] for record in schedule if "instructor" in record}
        return list(instructors)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"File {file_path} not found")
    except json.JSONDecodeError:
        raise HTTPException(status_code=500, detail=f"Failed to parse JSON file: {file_path}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def load_groups_from_file(file_path: str) -> List[str]:
    """Загружает уникальные группы из указанного JSON-файла."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            schedule = json.load(f).get("results", [])
            groups = {record["group_name"] for record in schedule if "group_name" in record}
        return list(groups)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"File {file_path} not found")
    except json.JSONDecodeError:
        raise HTTPException(status_code=500, detail=f"Failed to parse JSON file: {file_path}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
