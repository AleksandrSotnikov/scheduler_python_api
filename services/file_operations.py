import os
from fastapi import UploadFile
from __main_shedule__ import create_main_shedule
from __download_editor_schedule__ import ScheduleParser
import json
from typing import List


async def save_file(file: UploadFile, directory: str = "temp") -> str:
    """Сохраняет файл и возвращает его путь."""
    os.makedirs(directory, exist_ok=True)
    file_location = os.path.join(directory, file.filename)
    with open(file_location, "wb+") as file_object:
        file_object.write(file.file.read())
    return file_location


def parse_schedule(file_location: str, output_json: str) -> str:
    """Парсит Excel-файл в JSON, используя `create_main_shedule`."""
    create_main_shedule(file_location, output_json)
    return output_json


async def start_schedule_parsing():
    """Асинхронно запускает парсер расписания."""
    parser = ScheduleParser()
    await parser.start_parsing()


def load_schedule(file_path: str) -> List[dict]:
    """Загружает расписание из JSON-файла."""
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f).get("results", [])
