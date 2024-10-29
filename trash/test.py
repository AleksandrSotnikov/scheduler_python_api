import requests
import pandas as pd

# Ссылка на OneDrive файл
# url = "https://onedrive.live.com/embed?resid=9AABDDBE8027395E%21110&authkey=%21AF-oRXR4VEozERI&em=2&wdHideGridlines=True&wdHideHeaders=True&wdInConfigurator=True&wdInConfigurator=True&edesNext=false&resen=false"
# url = "http://onedrive.live.com/download?resid=9AABDDBE8027395E!110&authkey=%21AF-ORXR4VEOZERI&em=2"
# url = "https://onedrive.live.com/edit.aspx?resid=9AABDDBE8027395E!110&embed=1&redeem=aHR0cHM6Ly8xZHJ2Lm1zL3QvYy85QUFCRERCRTgwMjczOTVFL1VBUmVPU2VBdnQycklJQ2FiZ0FBQUFBQUFGLW9SWFI0VkVvekVSSQ&redeemstatus=true&authkey=!AF-oRXR4VEozERI"
# url = "http://onedrive.live.com/download?resid=9AABDDBE8027395E!110&authkey=!AF-oRXR4VEozERI&em=2"
# url = "https://euc-excel.officeapps.live.com/x/_layouts/XlFileHandler.aspx?WacUserType=WOPI&usid=0c27f2bc-97bf-4718-ba58-8985c3f8b161&NoAuth=1&waccluster=DE5"
# url = "https://onedrive.live.com/edit.aspx?resid=9AABDDBE8027395E!110&embed=3&redeem=aHR0cHM6Ly8xZHJ2Lm1zL3QvYy85QUFCRERCRTgwMjczOTVFL1VBUmVPU2VBdnQycklJQ2FiZ0FBQUFBQUFGLW9SWFI0VkVvekVSSQ&redeemstatus=true&authkey=!AF-oRXR4VEozERI"
# url = "https://res-1.cdn.office.net/files/odsp-web-prod_2024-10-11.010/"
url = "https://my.microsoftpersonalcontent.com/personal/9aabddbe8027395e/_layouts/15/download.aspx?UniqueId=8027395e-ddbe-20ab-809a-6e0000000000&Translate=false&tempauth=v1e.eyJzaXRlaWQiOiJkM2Y5YWY5Yy1mNDcwLTQ0ODktYmI4NS1hMWZiMWYwMmIxMjMiLCJhdWQiOiIwMDAwMDAwMy0wMDAwLTBmZjEtY2UwMC0wMDAwMDAwMDAwMDAvbXkubWljcm9zb2Z0cGVyc29uYWxjb250ZW50LmNvbUA5MTg4MDQwZC02YzY3LTRjNWItYjExMi0zNmEzMDRiNjZkYWQiLCJleHAiOiIxNzMwNDM0NTM5In0.52POWl1yRjxlDEXyIh9R7mRCHI7vlIsEl-ltbywoWkETKWZfCZYaMY-zh-LW5EJJJwGXcF0gI7OTM0wAas0DJdJjtJcrPYcdfbNcdFI6o12fSzmHiZyfeKx8mqcFKrom4owGwBBZZYD5jsw2O-eG3_GW0_WcieXhTCDVKaHR_n8vI2ZgyXpA0vac7hs1d7ojLZMhJBs8pn2-nwYUjxsZNQ_EWi1vJQqQp_SIG62halxbCEw2aZaA1S1_mJMIwCUNqDwYsXqy1CleNv-n0BA_07TE1tY208viDkP828Dl8dMSII-s57Km6C4z-gfYFw09RYUGqHimjRfKVJI48Sn3QKViAkO4bPBgay6h2Ndv0Jjuq7zaAnMZg-KgG-zv95pRwZ04livm0cCk8GUzDyTWSKEg17h2gXjYYuaMc1L3QSUlHnyF3nFSJJZy-XRpjeWAG5L_1BLqWOpVVOu8EmFhTC6RUhLZWlraHZ_bXMT2n-r4JWobskYkE4IzcKcL0avpvP75CE5SWNFhgM0PbXk0GQ.6eqFJh8GCs77Fk4Af5pCivMxz-lNn51uyhYVYpZvQI4"

# Отправляем запрос для загрузки файла
response = requests.get(url)

# Сохраняем файл на диск
with open('temp/file.xlsx', 'wb') as file:
    file.write(response.content)
    file.close()
# Замените 'your_file.xlsx' на имя вашего исходного Excel файла
file_path = 'file.xlsx'

# Чтение всех листов в словарь DataFrame'ов
sheets = pd.read_excel(file_path, sheet_name=None)

# Цикл по каждому листу
for sheet_name, data in sheets.items():
    # Сохранение каждого листа в отдельный Excel файл
    output_file = f'temp/{sheet_name}.xlsx'
    data.to_excel(output_file, index=False)
    print(f'Лист "{sheet_name}" сохранен в файл: {output_file}')




