# pip install pytest-playwright
# playwright install
from fastapi import HTTPException
import json
import pandas as pd
import requests
import os
from __editor_schedule__ import get_editor_schedule_by_date
import asyncio
from playwright.async_api import async_playwright, Response, Page


class ScheduleParser:
    def __init__(self):
        self.filename = "temp/editor_schedule.xlsx"
        self.is_file_loaded = False

    async def get_url(self, response: Response, page: Page):
        # Поиск url-ответа от OneDrive с фрагментом ссылки driveItem
        if "driveItem" in response.url:
            print("Загружаем таблицу...")
            try:
                # Вычленяем ссылку на файл из json-ответа и скачиваем его

                url = json.loads(await response.text())['openWith']['wac']['fileGetUrl']

                self.download_file(url)

                print("Таблица успешно загружена")
                self.is_file_loaded = True
                self.get_sheets_editor_schedule()
            except Exception as e:
                print(f"Ошибка при загрузке таблицы: {e}")

    def download_file(self, url):
        try:
            # Отправляем запрос для загрузки файла
            download_response = requests.get(url)
            download_response.raise_for_status()  # Проверка на ошибки при загрузке
            # Сохраняем файл на диск
            with open(self.filename, 'wb') as file:
                file.write(download_response.content)

            print("Таблица успешно загружена")
            self.is_file_loaded = True
            self.get_sheets_editor_schedule()  # Предполагается, что этот метод синхронный
        except Exception as e:
            print(f"Ошибка при загрузке таблицы: {e}")

    def get_sheets_editor_schedule(self):
        # Создание директории для временных файлов, если её нет
        os.makedirs('temp/xlsx', exist_ok=True)
        sheets = pd.read_excel(self.filename, sheet_name=None)

        # Цикл по каждому листу и сохранение в отдельный файл
        for sheet_name, data in sheets.items():
            output_file = f'temp/xlsx/{sheet_name}.xlsx'
            data.to_excel(output_file, index=False)
            print(f'Лист "{sheet_name}" сохранен в файл: {output_file}')
            get_editor_schedule_by_date("temp/schedule.json", output_file)

    async def start_parsing(self):
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            page.on("response", lambda response: asyncio.create_task(self.get_url(response, page)))

            print("Открываем сайт...")
            await page.goto('https://ompec.ru/student/uchebnaya-deyatelnost/izmeneniya-v-raspisanii.php')

            total_time = 0
            while not self.is_file_loaded:
                await asyncio.sleep(1)
                total_time += 1
                if total_time > 60:
                    raise HTTPException(status_code=408, detail="Не удалось загрузить файл: истекло время ожидания.")

            await browser.close()
