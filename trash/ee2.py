import json
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

class ScheduleParser:
    def __init__(self):
        self.filename = "schedule123.xlsx"
        self.is_file_loaded = False
        self.base_url = 'https://ompec.ru/student/uchebnaya-deyatelnost/izmeneniya-v-raspisanii.php'

    def download_file(self, file_url):
        print("Загружаем таблицу...")
        response = requests.get(file_url, stream=True)
        response.raise_for_status()
        with open(self.filename, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        print("Таблица успешно загружена")
        self.is_file_loaded = True

    def get_download_link(self, driver):
        """Получает ссылку на файл через Selenium."""
        print("Открываем сайт...")
        driver.get(self.base_url)
        time.sleep(3)  # Ожидание загрузки страницы

        # Поиск JSON-ответа в DOM или анализ других элементов
        response_text = None
        for request in driver.requests:
            if "driveItem" in request.url:
                response_text = request.response.body.decode('utf-8')
                break

        if not response_text:
            raise Exception("Не удалось найти ссылку для скачивания файла")

        file_data = json.loads(response_text)
        file_url = file_data.get('openWith', {}).get('wac', {}).get('fileGetUrl')
        return file_url

    def start_parsing(self):
        """Запуск загрузки с использованием Selenium."""
        options = webdriver.ChromeOptions()
        options.add_argument("--headless")
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

        try:
            file_url = self.get_download_link(driver)
            if file_url:
                self.download_file(file_url)
            else:
                print("Не удалось получить ссылку для загрузки расписания")
        finally:
            driver.quit()


def main():
    ScheduleParser().start_parsing()


if __name__ == '__main__':
    main()
