# strike_turenas_server
Сервер для управления Truenas и клиентами в сети

Установка службы в widnows:
nssm install dataset_ui C:\dataset_ui\venv\Scripts\python.exe main.py  
nssm set dataset_ui AppDirectory C:\dataset_ui
nssm set dataset_ui Description dataset_ui
nssm start dataset_ui

