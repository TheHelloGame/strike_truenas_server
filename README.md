# strike_turenas_server
Сервер для управления Truenas и клиентами в сети

Установка службы в Windows:
```
nssm install dataset_ui C:\dataset_ui\venv\Scripts\python.exe main.py
nssm set dataset_ui AppDirectory C:\dataset_ui
nssm set dataset_ui Description dataset_ui
nssm start dataset_ui
```

Файл .env:
```
#Путь к базе
DB_URL = "sqlite:///db.db"
#Апи ключ ля truenas
API_KEY = ""
#Адрес апи для truenas
API_URL = "http://192.168.88.10/api/v2.0/"
#Имя пула
STORAGE = "storage"
#Родительский DATASET
FATHER_DATASET = "ideal"
#DATASET для переключения
TRASH_DATASET = "trash"
#Часовой пояс для вывода
TIMEZONE = 3
#Логин для админки
LOGIN = "Admin"
#Пароль для админки
PASS = "Admin"
#Ип сервера, для обхода проверки
SERVER_IP="127.0.0.1"


```
