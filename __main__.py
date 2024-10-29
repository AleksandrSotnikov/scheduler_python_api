import json
from datetime import datetime
from fastapi import FastAPI, UploadFile, File, HTTPException
from models.schemas import UploadResponse, ScheduleQuery, ScheduleResponse, ScheduleRecord
from services.file_operations import save_file, parse_schedule, load_schedule
import os
from utils import load_and_filter_schedule, validate_date_format, load_classrooms_from_file, load_instructors_from_file, load_groups_from_file
from models.schemas import UploadResponse, DownloadResponse
from services.file_operations import save_file, parse_schedule, start_schedule_parsing

app = FastAPI()


@app.post("/upload_schedule/", response_model=UploadResponse, status_code=201)
async def upload_schedule(file: UploadFile = File(...)):
    """Загружает расписание, парсит и сохраняет его в JSON формате.

    - **file**: Загружаемый Excel-файл расписания.
    - **returns**: Сообщение о статусе загрузки и путь к выходному файлу JSON.
    """
    # Сохранение загруженного файла
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


@app.get("/download_editor_schedules/", response_model=DownloadResponse, status_code=200)
async def download_editor_schedules():
    """Асинхронно загружает и парсит расписание.

    - **returns**: Сообщение о завершении загрузки расписания.
    """
    try:
        await start_schedule_parsing()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка при загрузке расписания: {str(e)}")

    return DownloadResponse(message="Загрузка расписания завершена успешно.")


from fastapi import Query


@app.get("/schedule_main_group/", response_model=ScheduleResponse, status_code=200)
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


@app.get("/schedule_edit_group/", response_model=ScheduleResponse, status_code=200)
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
    try:
        datetime.strptime(day, "%d.%m.%Y")
    except ValueError:
        raise HTTPException(status_code=400, detail="Неверный формат даты. Используйте формат DD.MM.YYYY.")

    try:
        with open(f"temp/json/edit/{day}.json", "r", encoding="utf-8") as f:
            schedule = json.load(f)["results"]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка загрузки расписания: {str(e)}")

    # Фильтрация по группе
    filtered_schedule = [
        record for record in schedule if record["group_name"] == group
    ]

    return ScheduleResponse(results=[ScheduleRecord(**record) for record in filtered_schedule])


@app.get("/schedule_edit_group_pg/", response_model=ScheduleResponse, status_code=200)
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
    try:
        datetime.strptime(day, "%d.%m.%Y")
    except ValueError:
        raise HTTPException(status_code=400, detail="Неверный формат даты. Используйте формат DD.MM.YYYY.")

    try:
        with open(f"temp/json/edit/{day}.json", "r", encoding="utf-8") as f:
            schedule = json.load(f)["results"]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка загрузки расписания: {str(e)}")

    # Фильтрация по группе и подгруппе
    filtered_schedule = [
        record for record in schedule
        if record["group_name"] == group and
           (record["subgroup"] == subgroup or record["subgroup"] == 0)
    ]

    return ScheduleResponse(results=[ScheduleRecord(**record) for record in filtered_schedule])


@app.get("/schedule_remove_group/", response_model=ScheduleResponse, status_code=200)
async def get_schedule_remove_group(
    group: str = Query(..., examples={"example": {"summary": "Название группы", "value": "Группа A"}}),
    day: str = Query(..., examples={"example": {"summary": "Дата в формате DD.MM.YYYY", "value": "24.10.2024"}})
):
    """Возвращает удалённое расписание для указанной группы на конкретную дату."""
    validate_date_format(day)
    file_path = f"temp/json/remove/{day}.json"
    filtered_schedule = load_and_filter_schedule(file_path, "group_name", group)
    return ScheduleResponse(results=[ScheduleRecord(**record) for record in filtered_schedule])


@app.get("/schedule_add_group/", response_model=ScheduleResponse, status_code=200)
async def get_schedule_add_group(
    group: str = Query(..., examples={"example": {"summary": "Название группы", "value": "Группа A"}}),
    day: str = Query(..., examples={"example": {"summary": "Дата в формате DD.MM.YYYY", "value": "24.10.2024"}})
):
    """Возвращает добавленное расписание для указанной группы на конкретную дату."""
    validate_date_format(day)
    file_path = f"temp/json/add/{day}.json"
    filtered_schedule = load_and_filter_schedule(file_path, "group_name", group)
    return ScheduleResponse(results=[ScheduleRecord(**record) for record in filtered_schedule])


@app.get("/schedule_main_instructor/", response_model=ScheduleResponse, status_code=200)
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


@app.get("/schedule_edit_instructor/", response_model=ScheduleResponse, status_code=200)
async def get_schedule_edit_instructor(
        instructor: str = Query(..., examples={"example": {"summary": "ФИО преподавателя", "value": "Иванов И.И."}}),
        day: str = Query(..., examples={"example": {"summary": "Дата в формате DD.MM.YYYY", "value": "24.10.2024"}})
):
    """Возвращает отредактированное расписание для указанного преподавателя на конкретную дату.

    - **instructor**: ФИО преподавателя.
    - **day**: Дата в формате DD.MM.YYYY.
    """
    try:
        datetime.strptime(day, "%d.%m.%Y")
    except ValueError:
        raise HTTPException(status_code=400, detail="Неверный формат даты. Используйте формат DD.MM.YYYY.")

    try:
        with open(f"temp/json/edit/{day}.json", "r", encoding="utf-8") as f:
            schedule = json.load(f)["results"]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка загрузки расписания: {str(e)}")

    filtered_schedule = [record for record in schedule if record["instructor"] == instructor]
    return ScheduleResponse(results=[ScheduleRecord(**record) for record in filtered_schedule])


@app.get("/schedule_remove_instructor/", response_model=ScheduleResponse, status_code=200)
async def get_schedule_remove_instructor(
    instructor: str = Query(..., examples={"example": {"summary": "ФИО преподавателя", "value": "Иванов И.И."}}),
    day: str = Query(..., examples={"example": {"summary": "Дата в формате DD.MM.YYYY", "value": "24.10.2024"}})
):
    """Возвращает удалённое расписание для указанного преподавателя на конкретную дату."""
    validate_date_format(day)
    file_path = f"temp/json/remove/{day}.json"
    filtered_schedule = load_and_filter_schedule(file_path, "instructor", instructor)
    return ScheduleResponse(results=[ScheduleRecord(**record) for record in filtered_schedule])


@app.get("/schedule_add_instructor/", response_model=ScheduleResponse, status_code=200)
async def get_schedule_add_instructor(
    instructor: str = Query(..., examples={"example": {"summary": "ФИО преподавателя", "value": "Иванов И.И."}}),
    day: str = Query(..., examples={"example": {"summary": "Дата в формате DD.MM.YYYY", "value": "24.10.2024"}})
):
    """Возвращает добавленное расписание для указанного преподавателя на конкретную дату."""
    validate_date_format(day)
    file_path = f"temp/json/add/{day}.json"
    filtered_schedule = load_and_filter_schedule(file_path, "instructor", instructor)
    return ScheduleResponse(results=[ScheduleRecord(**record) for record in filtered_schedule])




@app.get("/schedule_main_classroom/", response_model=ScheduleResponse, status_code=200)
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


@app.get("/schedule_edit_classroom/", response_model=ScheduleResponse, status_code=200)
async def get_schedule_edit_classroom(
        classroom: str = Query(..., examples={"example": {"summary": "Название аудитории", "value": "101"}}),
        day: str = Query(..., examples={"example": {"summary": "Дата в формате DD.MM.YYYY", "value": "24.10.2024"}})
):
    """Возвращает отредактированное расписание для указанной аудитории на конкретную дату.

    - **classroom**: Название аудитории.
    - **day**: Дата в формате DD.MM.YYYY.
    """
    try:
        datetime.strptime(day, "%d.%m.%Y")
    except ValueError:
        raise HTTPException(status_code=400, detail="Неверный формат даты. Используйте формат DD.MM.YYYY.")

    try:
        with open(f"temp/json/edit/{day}.json", "r", encoding="utf-8") as f:
            schedule = json.load(f)["results"]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка загрузки расписания: {str(e)}")

    filtered_schedule = [record for record in schedule if record["classroom"] == classroom]
    return ScheduleResponse(results=[ScheduleRecord(**record) for record in filtered_schedule])


@app.get("/schedule_add_classroom/", response_model=ScheduleResponse, status_code=200)
async def get_schedule_add_classroom(
    classroom: str = Query(..., examples={"example": {"summary": "Название аудитории", "value": "101"}}),
    day: str = Query(..., examples={"example": {"summary": "Дата в формате DD.MM.YYYY", "value": "24.10.2024"}})
):
    """Возвращает добавленное расписание для указанной аудитории на конкретную дату."""
    validate_date_format(day)
    file_path = f"temp/json/add/{day}.json"
    filtered_schedule = load_and_filter_schedule(file_path, "classroom", classroom)
    return ScheduleResponse(results=[ScheduleRecord(**record) for record in filtered_schedule])


@app.get("/schedule_remove_classroom/", response_model=ScheduleResponse, status_code=200)
async def get_schedule_remove_classroom(
    classroom: str = Query(..., examples={"example": {"summary": "Название аудитории", "value": "101"}}),
    day: str = Query(..., examples={"example": {"summary": "Дата в формате DD.MM.YYYY", "value": "24.10.2024"}})
):
    """Возвращает удалённое расписание для указанной аудитории на конкретную дату."""
    validate_date_format(day)
    file_path = f"temp/json/remove/{day}.json"
    filtered_schedule = load_and_filter_schedule(file_path, "classroom", classroom)
    return ScheduleResponse(results=[ScheduleRecord(**record) for record in filtered_schedule])



@app.post("/clear_temp/")
async def clear_temp_files(admin: str):
    if admin == "yes":
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


@app.get("/list_date/")
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

    return {"files": file_list}



@app.get("/list_classroom/")
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


@app.get("/list_instructor/")
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


@app.get("/list_group/")
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


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
