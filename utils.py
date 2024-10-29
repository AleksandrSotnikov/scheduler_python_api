# utils.py

import json
from typing import List, Dict
from datetime import datetime
from fastapi import HTTPException


def load_and_filter_schedule(file_path: str, filter_field: str, filter_value: str) -> List[Dict]:
    """Загружает и фильтрует расписание по указанному полю и значению."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            schedule = json.load(f).get("results", [])
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка загрузки расписания: {str(e)}")

    # Фильтрация расписания по заданному полю
    return [record for record in schedule if record.get(filter_field) == filter_value]


def validate_date_format(date_str: str):
    """Проверяет, что дата соответствует формату DD.MM.YYYY."""
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
