import json
import os
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Optional, List
import uvicorn
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from fastapi import FastAPI, HTTPException, Query
from fastapi import UploadFile, File

from models.schemas import ScheduleResponse, ScheduleRecord
from models.schemas import UploadResponse, DownloadResponse
from services.file_operations import load_schedule
from services.file_operations import save_file, parse_schedule, start_schedule_parsing
from utils import validate_date_format, load_classrooms_from_file, load_instructors_from_file, \
    load_groups_from_file, get_filtered_schedule, load_subjects_from_file

from fastapi import FastAPI, Response
from pydantic import BaseModel
from typing import List
from PIL import Image, ImageDraw, ImageFont
import io

# Инициализируем FastAPI с помощью lifespan
scheduler = AsyncIOScheduler()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Настройка и запуск планировщика при старте приложения
    scheduler.add_job(download_editor_schedules, IntervalTrigger(minutes=10))
    scheduler.start()
    print("Планировщик запущен и выполняется каждые 10 минут.")

    # Продолжаем выполнение приложения
    yield

    # Остановка планировщика при завершении работы приложения
    scheduler.shutdown()
    print("Планировщик остановлен.")


app = FastAPI(lifespan=lifespan)


@app.post("/generate_schedule_image/")
async def generate_schedule_image(schedule: ScheduleResponse, day: str):
    # Параметры изображения и шрифт
    img_width, img_height = 800, 100 + 300
    background_color = (255, 255, 255)
    text_color = (0, 0, 0)
    line_color = (200, 200, 200)

    try:
        font = ImageFont.truetype("fonts/Zekton.ttf", 16)  # Замените на путь к шрифту, поддерживающему кириллицу
    except IOError:
        raise HTTPException(status_code=500, detail="Шрифт не найден. Убедитесь, что DejaVuSans.ttf доступен.")

    # Создание изображения и таблицы
    img = Image.new("RGB", (img_width, img_height), background_color)
    draw = ImageDraw.Draw(img)
    padding_up = 10  # Отступ сверху
    padding_left = 20
    # Заголовок
    title_text = f"Расписание занятий на {day}"
    draw.text((img_width // 2 - len(title_text) * 4, 20), title_text, fill=text_color, font=font, align="center")
    try:
        logo = Image.open("images/ompec_ico.jpg")
        logo_width, logo_height = 90, 90  # Размеры логотипа
        logo = logo.resize((logo_width, logo_height))  # Масштабируем логотип
        img.paste(logo, (img_width - logo_width - 20, 10))  # Позиция логотипа (справа сверху)
    except IOError:
        raise HTTPException(status_code=500, detail="Изображение логотипа не найдено. Проверьте путь.")
    # Настройки для табличного отображения
    y_offset = 60  # начальная высота для таблицы
    col_positions = {
        "left": padding_left,
        "center": img_width // 3,
        "right": img_width // 2 + padding_left
    }
    row_height = 40
    cell_padding = 10

    y_offset += row_height

    draw.text((20, 100), "1 пара, 8:00-9:35", fill=text_color, font=font, align="center")
    draw.text((20, 150), "2 пара, 9:45-11:20", fill=text_color, font=font, align="center")
    draw.text((20, 200), "3 пара, 11:55-13:30", fill=text_color, font=font, align="center")
    draw.text((20, 250), "4 пара, 13:45-15:20", fill=text_color, font=font, align="center")
    draw.text((20, 300), "5 пара, 15:40-17:15", fill=text_color, font=font, align="center")
    draw.text((20, 350), "6 пара, 17:25-19:00", fill=text_color, font=font, align="center")
    draw.line([(170, 100), (170, 400)], fill=line_color)
    draw.line([(20, 100), (780, 100)], fill=line_color)
    draw.line([(20, 150), (780, 150)], fill=line_color)
    draw.line([(20, 200), (780, 200)], fill=line_color)
    draw.line([(20, 250), (780, 250)], fill=line_color)
    draw.line([(20, 300), (780, 300)], fill=line_color)
    draw.line([(20, 350), (780, 350)], fill=line_color)

    # Заполнение таблицы данными расписания
    for record in schedule.results:
        print(record)
        if record.subgroup == 0:
            x_pos = col_positions["center"]
        elif record.subgroup == 1:
            x_pos = col_positions["left"]
            draw.line([(img_width // 2, y_offset), (img_width // 2, y_offset + row_height)])
        else:
            x_pos = col_positions["right"]
            draw.line([(img_width // 2, y_offset), (img_width // 2, y_offset + row_height)])

        row_text = (f"{record.group_name}({record.subgroup}) - Ауд. {record.classroom}\n"
                    f"{record.subject}, {record.instructor}")
    #subject_text = f"{record.subject}, {record.instructor}"

        draw.text((x_pos, record.lesson_number * row_height + 20), row_text, fill=text_color, font=font, align="center")
    #draw.text((x_pos, record.lesson_number * row_height + row_height // 2 + 20), subject_text, fill=text_color, font=font,
    #             align="center")
    #draw.line([(padding_up, record.lesson_number * row_height + 60), (img_width - padding_up, record.lesson_number * row_height + 60)], fill=line_color)

    # Конвертация изображения в байты
    img_byte_array = io.BytesIO()
    img.save(img_byte_array, format="PNG")
    img_byte_array = img_byte_array.getvalue()

    return Response(content=img_byte_array, media_type="image/png")


@app.post("/main_schedule/upload/", response_model=UploadResponse, status_code=201)
async def upload_schedule(file: UploadFile = File(...), admin: str = ""):
    """Загружает расписание, парсит и сохраняет его в JSON формате.

    - **file**: Загружаемый Excel-файл расписания.
    - **returns**: Сообщение о статусе загрузки и путь к выходному файлу JSON.
    """
    # Сохранение загруженного файла
    if admin == "yesorno":
        try:
            file_location = await save_file(file)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Ошибка сохранения файла: {str(e)}")

        # Парсинг в JSON
        output_json = "temp/schedule.json"
        try:
            parse_schedule(file_location, output_json)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Ошибка при парсинге файла: {str(e)}")

        return UploadResponse(message="Файл загружен и обработан.", output_file=output_json)


@app.get("/main_schedule/group/", response_model=ScheduleResponse, status_code=200)
async def get_schedule_main_group(
        group: str = Query(..., examples={"example": {"summary": "Название группы", "value": "Группа A"}}),
        day_of_week: int = Query(..., examples={"example": {"summary": "День недели", "value": 1}}, ge=1, le=7),
        week_number: int = Query(..., examples={"example": {"summary": "Номер недели", "value": 1}}, ge=1, le=2)
):
    """Возвращает расписание для указанной группы на день недели и номер недели.

    - **group**: Название группы (например, "Группа A").
    - **day_of_week**: Номер дня недели (1-7).
    - **week_number**: Номер недели (1-2).
    - **returns**: Отфильтрованное расписание.
    """
    try:
        schedule = load_schedule("temp/schedule.json")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка загрузки расписания: {str(e)}")

    # Фильтрация по группе, дню недели и номеру недели
    filtered_schedule = [
        record for record in schedule
        if record["group_name"] == group and
           record["day_of_week"] == day_of_week and
           record["week_number"] == week_number
    ]

    # Возвращаем отфильтрованные записи в формате `ScheduleRecord`
    return ScheduleResponse(results=[ScheduleRecord(**record) for record in filtered_schedule])


@app.get("/main_schedule/instructor/", response_model=ScheduleResponse, status_code=200)
async def get_schedule_main_instructor(
        instructor: str = Query(..., examples={"example": {"summary": "ФИО преподавателя", "value": "Иванов И.И."}}),
        day_of_week: int = Query(..., examples={"example": {"summary": "Номер дня недели", "value": 1}}, ge=1, le=7),
        week_number: int = Query(..., examples={"example": {"summary": "Номер недели", "value": 1}}, ge=1, le=2)
):
    """Возвращает основное расписание для указанного преподавателя, дня недели и номера недели.

    - **instructor**: ФИО преподавателя.
    - **day_of_week**: Номер дня недели (1–7).
    - **week_number**: Номер недели (1–2).
    """
    try:
        with open("temp/schedule.json", "r", encoding="utf-8") as f:
            schedule = json.load(f)["results"]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка загрузки расписания: {str(e)}")

    filtered_schedule = [
        record for record in schedule
        if record["instructor"] == instructor and
           record["day_of_week"] == day_of_week and
           record["week_number"] == week_number
    ]
    return ScheduleResponse(results=[ScheduleRecord(**record) for record in filtered_schedule])


@app.get("/main_schedule/classroom/", response_model=ScheduleResponse, status_code=200)
async def get_schedule_main_classroom(
        classroom: str = Query(..., examples={"example": {"summary": "Название аудитории", "value": "101"}}),
        day_of_week: int = Query(..., examples={"example": {"summary": "Номер дня недели", "value": 1}}, ge=1, le=7),
        week_number: int = Query(..., examples={"example": {"summary": "Номер недели", "value": 1}}, ge=1, le=2)
):
    """Возвращает основное расписание для указанной аудитории, дня недели и номера недели.

    - **classroom**: Название аудитории.
    - **day_of_week**: Номер дня недели (1–7).
    - **week_number**: Номер недели (1–2).
    """
    try:
        with open("temp/schedule.json", "r", encoding="utf-8") as f:
            schedule = json.load(f)["results"]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка загрузки расписания: {str(e)}")

    filtered_schedule = [
        record for record in schedule
        if record["classroom"] == classroom and
           record["day_of_week"] == day_of_week and
           record["week_number"] == week_number
    ]
    return ScheduleResponse(results=[ScheduleRecord(**record) for record in filtered_schedule])


@app.get("/edit_schedule/download/", response_model=DownloadResponse, status_code=200)
async def download_editor_schedules():
    """Асинхронно загружает и парсит расписание.

    - **returns**: Сообщение о завершении загрузки расписания.
    """
    try:
        await start_schedule_parsing()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка при загрузке расписания: {str(e)}")

    return DownloadResponse(message="Загрузка расписания завершена успешно.")


@app.get("/edit_schedule/group/", response_model=ScheduleResponse, status_code=200)
async def get_schedule_edit_group(
        group: str = Query(..., examples={"example": {"summary": "Название группы", "value": "Группа A"}}),
        day: str = Query(..., examples={"example": {"summary": "Дата в формате DD.MM.YYYY", "value": "24.10.2024"}})
):
    """Возвращает отредактированное расписание для указанной группы на конкретную дату.

    - **group**: Название группы, для которой нужно получить расписание.
    - **day**: Дата в формате DD.MM.YYYY.
    - **returns**: Отфильтрованное расписание.
    """
    # Проверка корректности формата даты
    validate_date_format(day)
    try:
        with open(f"temp/json/edit/{day}.json", "r", encoding="utf-8") as f:
            schedule = json.load(f)["results"]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка загрузки расписания: {str(e)}")

    # Фильтрация по группе
    filtered_schedule = sorted(
        (record for record in schedule if record["group_name"] == group),
        key=lambda record: record["lesson_number"]
    )

    return ScheduleResponse(results=[ScheduleRecord(**record) for record in filtered_schedule])


@app.get("/edit_schedule/group_pg/", response_model=ScheduleResponse, status_code=200)
async def get_schedule_edit_group_pg(
        group: str = Query(..., examples={"example": {"summary": "Название группы", "value": "Группа A"}}),
        subgroup: int = Query(..., examples={"example": {"summary": "Номер подгруппы", "value": 1}}, ge=0, le=2),
        day: str = Query(..., examples={"example": {"summary": "Дата в формате DD.MM.YYYY", "value": "24.10.2024"}})
):
    """Возвращает расписание для указанной группы и подгруппы на конкретную дату.

    - **group**: Название группы.
    - **subgroup**: Номер подгруппы (0 - все, 1 - подгруппа 1, 2 - подгруппа 2).
    - **day**: Дата в формате DD.MM.YYYY.
    - **returns**: Отфильтрованное расписание.
    """
    # Проверка формата даты
    validate_date_format(day)

    try:
        with open(f"temp/json/edit/{day}.json", "r", encoding="utf-8") as f:
            schedule = json.load(f)["results"]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка загрузки расписания: {str(e)}")

    # Фильтрация по группе и подгруппе
    filtered_schedule = sorted(
        (record for record in schedule if record["group_name"] == group and
         (record["subgroup"] == subgroup or record["subgroup"] == 0)),
        key=lambda record: record["lesson_number"]
    )

    return ScheduleResponse(results=[ScheduleRecord(**record) for record in filtered_schedule])


@app.get("/edit_schedule/instructor/", response_model=ScheduleResponse, status_code=200)
async def get_schedule_edit_instructor(
        instructor: str = Query(..., examples={"example": {"summary": "ФИО преподавателя", "value": "Иванов И.И."}}),
        day: str = Query(..., examples={"example": {"summary": "Дата в формате DD.MM.YYYY", "value": "24.10.2024"}})
):
    """Возвращает отредактированное расписание для указанного преподавателя на конкретную дату.

    - **instructor**: ФИО преподавателя.
    - **day**: Дата в формате DD.MM.YYYY.
    """
    validate_date_format(day)

    try:
        with open(f"temp/json/edit/{day}.json", "r", encoding="utf-8") as f:
            schedule = json.load(f)["results"]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка загрузки расписания: {str(e)}")

    filtered_schedule = sorted(
        (record for record in schedule if record["instructor"] == instructor),
        key=lambda record: record["lesson_number"]
    )
    return ScheduleResponse(results=[ScheduleRecord(**record) for record in filtered_schedule])


@app.get("/edit_schedule/classroom/", response_model=ScheduleResponse, status_code=200)
async def get_schedule_edit_classroom(
        classroom: str = Query(..., examples={"example": {"summary": "Название аудитории", "value": "101"}}),
        day: str = Query(..., examples={"example": {"summary": "Дата в формате DD.MM.YYYY", "value": "24.10.2024"}})
):
    """Возвращает отредактированное расписание для указанной аудитории на конкретную дату.

    - **classroom**: Название аудитории.
    - **day**: Дата в формате DD.MM.YYYY.
    """
    validate_date_format(day)

    try:
        with open(f"temp/json/edit/{day}.json", "r", encoding="utf-8") as f:
            schedule = json.load(f)["results"]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка загрузки расписания: {str(e)}")

    filtered_schedule = sorted(
        (record for record in schedule if record["classroom"] == classroom),
        key=lambda record: record["lesson_number"]
    )
    return ScheduleResponse(results=[ScheduleRecord(**record) for record in filtered_schedule])


@app.get("/remove_schedule/group/", response_model=ScheduleResponse, status_code=200)
async def get_schedule_remove_group(
        group: str = Query(..., examples={"example": {"summary": "Название группы", "value": "Группа A"}}),
        day: str = Query(..., examples={"example": {"summary": "Дата в формате DD.MM.YYYY", "value": "24.10.2024"}})
):
    """Возвращает удалённое расписание для указанной группы на конкретную дату.

    Параметры:
    - **group** (str): Название группы, для которой нужно получить расписание.
    - **day** (str): Дата в формате DD.MM.YYYY.

    Возвращает:
    - ScheduleResponse: Отфильтрованное расписание для указанной группы.
    """
    return await get_filtered_schedule(day, "group_name", group, "remove")


@app.get("/remove_schedule/instructor/", response_model=ScheduleResponse, status_code=200)
async def get_schedule_remove_instructor(
        instructor: str = Query(..., examples={"example": {"summary": "ФИО преподавателя", "value": "Иванов И.И."}}),
        day: str = Query(..., examples={"example": {"summary": "Дата в формате DD.MM.YYYY", "value": "24.10.2024"}})
):
    """Возвращает удалённое расписание для указанного преподавателя на конкретную дату.

    Параметры:
    - **instructor** (str): ФИО преподавателя, для которого нужно получить расписание.
    - **day** (str): Дата в формате DD.MM.YYYY.

    Возвращает:
    - ScheduleResponse: Отфильтрованное расписание для указанного преподавателя.
    """
    return await get_filtered_schedule(day, "instructor", instructor, "remove")


@app.get("/remove_schedule/classroom/", response_model=ScheduleResponse, status_code=200)
async def get_schedule_remove_classroom(
        classroom: str = Query(..., examples={"example": {"summary": "Название аудитории", "value": "101"}}),
        day: str = Query(..., examples={"example": {"summary": "Дата в формате DD.MM.YYYY", "value": "24.10.2024"}})
):
    """Возвращает удалённое расписание для указанной аудитории на конкретную дату.

    Параметры:
    - **classroom** (str): Название аудитории, для которой нужно получить расписание.
    - **day** (str): Дата в формате DD.MM.YYYY.

    Возвращает:
    - ScheduleResponse: Отфильтрованное расписание для указанной аудитории.
    """
    return await get_filtered_schedule(day, "classroom", classroom, "remove")


@app.get("/add_schedule/group/", response_model=ScheduleResponse, status_code=200)
async def get_schedule_add_group(
        group: str = Query(..., examples={"example": {"summary": "Название группы", "value": "Группа A"}}),
        day: str = Query(..., examples={"example": {"summary": "Дата в формате DD.MM.YYYY", "value": "24.10.2024"}})
):
    """Возвращает добавленное расписание для указанной группы на конкретную дату.

    - **group**: Название группы (например, "Группа A").
    - **day**: Дата в формате DD.MM.YYYY (например, "24.10.2024").
    - **returns**: Отфильтрованное расписание для указанной группы.
    """
    return await get_filtered_schedule(day, "group_name", group, "add")


@app.get("/add_schedule/instructor/", response_model=ScheduleResponse, status_code=200)
async def get_schedule_add_instructor(
        instructor: str = Query(..., examples={"example": {"summary": "ФИО преподавателя", "value": "Иванов И.И."}}),
        day: str = Query(..., examples={"example": {"summary": "Дата в формате DD.MM.YYYY", "value": "24.10.2024"}})
):
    """Возвращает добавленное расписание для указанного преподавателя на конкретную дату.

    - **instructor**: ФИО преподавателя (например, "Иванов И.И.").
    - **day**: Дата в формате DD.MM.YYYY (например, "24.10.2024").
    - **returns**: Отфильтрованное расписание для указанного преподавателя.
    """
    return await get_filtered_schedule(day, "instructor", instructor, "add")


@app.get("/add_schedule/classroom/", response_model=ScheduleResponse, status_code=200)
async def get_schedule_add_classroom(
        classroom: str = Query(..., examples={"example": {"summary": "Название аудитории", "value": "101"}}),
        day: str = Query(..., examples={"example": {"summary": "Дата в формате DD.MM.YYYY", "value": "24.10.2024"}})
):
    """Возвращает добавленное расписание для указанной аудитории на конкретную дату.

    - **classroom**: Название аудитории (например, "101").
    - **day**: Дата в формате DD.MM.YYYY (например, "24.10.2024").
    - **returns**: Отфильтрованное расписание для указанной аудитории.
    """
    return await get_filtered_schedule(day, "classroom", classroom, "add")


@app.post("/clear_temp/")
async def clear_temp_files(admin: str):
    if admin == "yesorno":
        temp_dir = "temp"
        for file in os.listdir(temp_dir):
            file_path = os.path.join(temp_dir, file)
            try:
                if os.path.isfile(file_path):
                    os.unlink(file_path)
            except Exception as e:
                return {"message": f"Ошибка при удалении: {str(e)}"}

        return {"message": "Временные файлы очищены."}
    else:
        return {"message": "Отказ"}


@app.get("/list/date/")
async def get_date_list():
    """
    Возвращает список доступных файлов с расписанием (даты) в директории `temp/json/edit`.
    Каждое имя файла возвращается без расширения `.json`.
    """
    directory = 'temp/json/edit'

    # Проверка, существует ли директория
    if not os.path.exists(directory):
        raise HTTPException(status_code=404, detail="Directory not found")

    # Получаем список файлов без расширения .json
    try:
        file_list = [
            os.path.splitext(file)[0] for file in os.listdir(directory) if file.endswith('.json')
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading directory: {str(e)}")

    # Проверка на случай пустой директории
    if not file_list:
        return {"files": "No files found in directory"}
    try:
        date_format = "%d.%m.%Y"  # Укажите формат вашей даты в именах файлов
        date_list = sorted(
            [datetime.strptime(file, date_format) for file in file_list]  # Сортировка по возрастанию
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Error parsing dates: {str(e)}")
    sorted_dates = [date.strftime(date_format) for date in date_list]

    return {"files": sorted_dates}


@app.get("/list/classroom/")
async def get_list_classroom():
    """Возвращает список уникальных кабинетов из основного файла и последних трёх файлов."""
    all_classrooms = set()

    # 1. Загружаем кабинеты из основного файла `schedule.json`
    main_file = "temp/schedule.json"
    all_classrooms.update(load_classrooms_from_file(main_file))

    # 2. Загружаем последние три файла из папки `temp/json/edit`
    edit_directory = "temp/json/edit"
    if not os.path.exists(edit_directory):
        raise HTTPException(status_code=404, detail="Edit directory not found")

    try:
        # Получаем список файлов и сортируем по дате, извлекая последние три
        json_files = sorted(
            (f for f in os.listdir(edit_directory) if f.endswith(".json")),
            reverse=True
        )[:3]

        # Загружаем кабинеты из каждого из последних трех файлов
        for json_file in json_files:
            file_path = os.path.join(edit_directory, json_file)
            all_classrooms.update(load_classrooms_from_file(file_path))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    # Возвращаем уникальные кабинеты в виде списка
    return {"classrooms": list(all_classrooms)}


@app.get("/list/subject/")
async def get_list_classroom():
    """Возвращает список уникальных кабинетов из основного файла и последних трёх файлов."""
    all_subjects = set()

    # 1. Загружаем кабинеты из основного файла `schedule.json`
    main_file = "temp/schedule.json"
    all_subjects.update(load_subjects_from_file(main_file))

    # 2. Загружаем последние три файла из папки `temp/json/edit`
    edit_directory = "temp/json/edit"
    if not os.path.exists(edit_directory):
        raise HTTPException(status_code=404, detail="Edit directory not found")

    try:
        # Получаем список файлов и сортируем по дате, извлекая последние три
        json_files = sorted(
            (f for f in os.listdir(edit_directory) if f.endswith(".json")),
            reverse=True
        )[:3]

        # Загружаем кабинеты из каждого из последних трех файлов
        for json_file in json_files:
            file_path = os.path.join(edit_directory, json_file)
            all_subjects.update(load_subjects_from_file(file_path))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    # Возвращаем уникальные кабинеты в виде списка
    return {"subjects": list(all_subjects)}


@app.get("/list/instructor/")
async def get_list_instructor():
    """Возвращает список уникальных преподавателей из основного файла и последних трёх файлов."""
    all_instructors = set()

    # 1. Загружаем преподавателей из основного файла `schedule.json`
    main_file = "temp/schedule.json"
    all_instructors.update(load_instructors_from_file(main_file))

    # 2. Загружаем последние три файла из папки `temp/json/edit`
    edit_directory = "temp/json/edit"
    if not os.path.exists(edit_directory):
        raise HTTPException(status_code=404, detail="Edit directory not found")

    try:
        # Получаем список файлов и сортируем по дате, извлекая последние три
        json_files = sorted(
            (f for f in os.listdir(edit_directory) if f.endswith(".json")),
            reverse=True
        )[:3]

        # Загружаем преподавателей из каждого из последних трех файлов
        for json_file in json_files:
            file_path = os.path.join(edit_directory, json_file)
            all_instructors.update(load_instructors_from_file(file_path))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    # Возвращаем уникальных преподавателей в виде списка
    return {"instructors": list(all_instructors)}


@app.get("/list/group/")
async def get_list_group():
    """Возвращает список уникальных групп из основного файла и последних трёх файлов."""
    all_groups = set()

    # 1. Загружаем группы из основного файла `schedule.json`
    main_file = "temp/schedule.json"
    all_groups.update(load_groups_from_file(main_file))

    # 2. Загружаем последние три файла из папки `temp/json/edit`
    edit_directory = "temp/json/edit"
    if not os.path.exists(edit_directory):
        raise HTTPException(status_code=404, detail="Edit directory not found")

    try:
        # Получаем список файлов и сортируем по дате, извлекая последние три
        json_files = sorted(
            (f for f in os.listdir(edit_directory) if f.endswith(".json")),
            reverse=True
        )[:3]

        # Загружаем группы из каждого из последних трех файлов
        for json_file in json_files:
            file_path = os.path.join(edit_directory, json_file)
            all_groups.update(load_groups_from_file(file_path))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    # Возвращаем уникальные группы в виде списка
    return {"groups": list(all_groups)}


data_folder = "temp/json/edit"


def load_schedule_data_counter(file_path: str) -> List[dict]:
    """Загружает данные расписания из файла JSON."""
    try:
        with open(file_path, "r", encoding="utf-8") as file:
            return json.load(file)["results"]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка чтения файла {file_path}: {str(e)}")


def filter_schedule_data_counter(schedule_data: List[dict], group_name: Optional[str], subgroup: Optional[int],
                                 subject: Optional[str], instructor: Optional[str]) -> List[dict]:
    """Фильтрует данные расписания по заданным параметрам."""
    return [
        record for record in schedule_data
        if (group_name is None or record["group_name"] == group_name) and
           (subgroup is None or record["subgroup"] == subgroup) and
           (subject is None or record["subject"] == subject) and
           (instructor is None or record["instructor"] == instructor)
    ]


@app.get("/pair/count/")
async def count_classes(
        group_name: Optional[str] = Query(None,
                                          examples={"example": {"summary": "Название группы", "value": "ТЭМ-52"}}),
        subgroup: Optional[int] = Query(None, ge=0, le=2,
                                        examples={"example": {"summary": "Номер подгруппы", "value": 0}}),
        subject: Optional[str] = Query(None, examples={
            "example": {"summary": "Название предмета", "value": "Испыт.модел.элем.сист.автом."}}),
        instructor: Optional[str] = Query(None, examples={
            "example": {"summary": "ФИО преподавателя", "value": "Фёдоров К.А."}})
):
    """Возвращает количество проведенных пар по заданным параметрам."""
    if not os.path.exists(data_folder):
        raise HTTPException(status_code=404, detail="Данные не найдены")

    total_count = 0

    for filename in os.listdir(data_folder):
        if filename.endswith(".json"):
            file_path = os.path.join(data_folder, filename)
            schedule_data = load_schedule_data_counter(file_path)
            filtered_data = filter_schedule_data_counter(schedule_data, group_name, subgroup, subject, instructor)
            total_count += len(filtered_data)

    return {"total_classes": total_count}


@app.get("/pair/dates/")
async def get_class_dates(
        group_name: Optional[str] = Query(None,
                                          examples={"example": {"summary": "Название группы", "value": "ТЭМ-52"}}),
        subgroup: Optional[int] = Query(None, ge=0, le=2,
                                        examples={"example": {"summary": "Номер подгруппы", "value": 0}}),
        subject: Optional[str] = Query(None, examples={
            "example": {"summary": "Название предмета", "value": "Испыт.модел.элем.сист.автом."}}),
        instructor: Optional[str] = Query(None, examples={
            "example": {"summary": "ФИО преподавателя", "value": "Фёдоров К.А."}})
):
    """Возвращает список всех вхождений дат, когда проводились пары по заданным параметрам."""
    if not os.path.exists(data_folder):
        raise HTTPException(status_code=404, detail="Данные не найдены")

    class_dates = []  # Используем список для хранения всех вхождений дат

    for filename in os.listdir(data_folder):
        if filename.endswith(".json"):
            try:
                date_str = filename.split(".")[0] + "." + filename.split(".")[1] + "." + filename.split(".")[
                    2]  # Извлекаем дату из названия файла
                datetime.strptime(date_str, "%d.%m.%Y")  # Проверка корректности формата
            except ValueError:
                raise HTTPException(status_code=500, detail=f"Некорректный формат даты в файле {filename}")

            file_path = os.path.join(data_folder, filename)
            schedule_data = load_schedule_data_counter(file_path)
            filtered_data = filter_schedule_data_counter(schedule_data, group_name, subgroup, subject, instructor)

            if filtered_data:
                class_dates.extend(
                    [date_str] * len(filtered_data))  # Добавляем дату столько раз, сколько соответствующих пар

    return {"class_dates": class_dates}  # Возвращаем список всех вхождений


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
