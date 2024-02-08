from fastapi import FastAPI, Request, HTTPException, Depends, WebSocket, WebSocketDisconnect, status
import re
from sqlalchemy import select
from sqlalchemy.orm import Session
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from truenas import create_snapshot,create_dataset, create_target, create_extent, create_targetextent, del_dataset, del_target,del_snapshot , superclient_extent, trash_extent
from bd import client, add_client,get_all_client, get_client,del_client, update_dataset_time,get_db_session,get_client_by_ip, update_superuser,get_all_superuser,power_status,set_default_power
from ping3 import ping
from config import FATHER_DATASET, LOGIN, PASS, SERVER_IP
import uvicorn
from wakeonlan import send_magic_packet
import logging
from logging.handlers import RotatingFileHandler
import os


import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


# Создаем логгер
logger = logging.getLogger(__name__)
logger.setLevel(logging.ERROR)  # Устанавливаем уровень логирования на ERROR

# Создаем обработчик для записи в файлы
handler = RotatingFileHandler('error.log', maxBytes=5*1024*1024, backupCount=5)  # Максимальный размер файла 5 Мб, максимальное количество файлов - 5
handler.setLevel(logging.ERROR)  # Устанавливаем уровень логирования на ERROR

# Создаем форматтер для логгера
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)

# Добавляем обработчик к логгеру
logger.addHandler(handler)

templates = Jinja2Templates(directory="templates")

app = FastAPI(title="Strike Arena")
app.mount("/static", StaticFiles(directory="static"), name="static")

active_websockets = {}

security = HTTPBasic()

def authenticate_user(credentials: HTTPBasicCredentials = Depends(security)):
    correct_username = LOGIN
    correct_password = PASS

    if credentials.username != correct_username or credentials.password != correct_password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Basic"},
        )
    return True

@app.get("/login", include_in_schema=False)
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.get("/logout")
async def logout(request: Request, response: JSONResponse, credentials: HTTPBasicCredentials = Depends(security)):
    response.delete_cookie("Authorization")
    raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Logged out",
            headers={"WWW-Authenticate": "Basic"},
    )

@app.post("/authenticate")
async def authenticate_user_route(credentials: HTTPBasicCredentials = Depends(security)):
    if authenticate_user(credentials):
        return {"message": "Successfully authenticated"}

@app.get("/")
async def read_root(request: Request, authenticated: bool = Depends(authenticate_user)):
    return templates.TemplateResponse("index.html", {"request": request})

def check_valid_name(name: str,db_session) -> bool:
    pattern = re.compile(r'^[a-zA-Z][a-zA-Z0-9_-]*$')
    if not bool(pattern.match(name)):
        raise Exception('Допустими только английские буквы, цифры и знаки: "-","_" ')
    if name.lower() == FATHER_DATASET.lower():
        raise Exception('Имя соотвествует родительскому датасету')
    client = get_client(name, db_session)
    if client != None:
        raise Exception('Не уникальное имя')
    
security = HTTPBasic()

def authenticate_user(credentials: HTTPBasicCredentials = Depends(security)):
    correct_username = "your_username"
    correct_password = "your_password"

    if credentials.username != correct_username or credentials.password != correct_password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Basic"},
        )
    return True
    
    
def check_valid_ip(ip: str, db_session: Session) -> None:
    ip_pattern = re.compile(r'^(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$')
    if not bool(ip_pattern.match(ip)):
        raise Exception('Неверный формат IP')
    if get_client_by_ip(ip, db_session) is not None:
        raise Exception('Не уникальный IP')
    
def check_ip_availability(ip: str) -> bool:
    result = ping(ip)
    if ip == SERVER_IP:
        return True
    if result is not None and result is not False:
        raise Exception('Компьютер в сети')  # IP-адрес доступен
    else:
        return True  # IP-адрес недоступен
    
def check_superuser(name: str,db_session):
    client = get_client(name, db_session)
    if client.get("superuser") == True:
        raise Exception("Включен суперклиент")
        
def check_all_superuser( db_seession):
    client = get_all_superuser(db_seession)
    if client != None:
        raise Exception("Включен суперклиент на другом ПК")
    
@app.get("/client")
async def get(db_session: Session = Depends(get_db_session)):
    try:
        data = get_all_client(db_session)
        return({"STATUS": "OK", "DATA":data})
    except Exception as err:
        logger.error(err)


@app.post("/client")
async def create_client(name: str, ip:str, db_session: Session = Depends(get_db_session)):
    try:
        status = {}
        check_valid_name(name, db_session)
        check_valid_ip(ip,db_session)
        status["snapshot"] = await create_snapshot(name)
        status["dataset"] = await create_dataset(name)
        status['target_id'] = await create_target(name)
        status['extent_id'] = await create_extent(name)
        status['targetextent_id'] = await create_targetextent(status['target_id'],status['extent_id'])
        add_client(name,ip,status['extent_id'], db_session)
        db_session.commit()
        return({"STATUS": "OK", "DATA":status})
    except Exception as err:
        if status.get("dataset", False):
            await del_dataset(name)  
        if status.get("snapshot", False):
            await del_snapshot(name)
        db_session.rollback()
        logger.error(err)
        return({"STATUS": "ERROR", "DATA": f'{err}'})
    
    
@app.delete("/client/{name}")
async def delete_client(name: str,db_session: Session = Depends(get_db_session)):
    try:
        status = {}
        check_superuser(name,db_session)
        client = get_client(name, db_session)
        check_ip_availability(client["ip"])
        if client["ip"] == SERVER_IP:
            os.system('net stop MSiSCSI')
        status["dataset"] = await del_dataset(name)
        status["snapshot"] = await del_snapshot(name)
        del_client(name,db_session)
        db_session.commit()
        if client["ip"] == SERVER_IP:
            os.system('net start MSiSCSI')
        return({"STATUS": "OK", "DATA":status})
    except Exception as err:
        db_session.rollback()
        logger.error(err)
        return({"STATUS": "ERROR", "DATA": f'{err}'})
    
@app.get("/update_dataset/{name}")    
async def update_dataset(name:str, db_session: Session = Depends(get_db_session)):
    try:
        client = get_client(name, db_session)
        check_superuser(name,db_session)
        check_ip_availability(client["ip"])
        if client["ip"] == SERVER_IP:
            os.system('net stop MSiSCSI')
        status = {}
        status["dataset_trash_on"] = await trash_extent(name, client["extent_id"], True)
        status["dataset_del"] = await del_dataset(name)
        status["snapshot_del"] = await del_snapshot(name)
        status["snapshot_new"] = await create_snapshot(name)
        status["dataset_new"] = await create_dataset(name)
        status["dataset_trash_off"] = await trash_extent(name, client["extent_id"], False)
        update_dataset_time(name,db_session)
        db_session.commit()
        if client["ip"] == SERVER_IP:
            os.system('net start MSiSCSI')
        return({"STATUS": "OK", "DATA":status})
    except Exception as err:
        db_session.rollback()
        logger.error(err)
        return({"STATUS": "ERROR", "DATA": f'{err}'})
    

@app.post("/superuser")
async def create_client(name: str, superuser: bool, db_session: Session = Depends(get_db_session)):
    try:
        
        status = {}
        if superuser == True:
            check_all_superuser(db_session)
        client = get_client(name, db_session)
        check_ip_availability(client["ip"])
        if client["ip"] == SERVER_IP:
            os.system('net stop MSiSCSI')
        status['superclient'] = await superclient_extent(name, client["extent_id"], superuser)
        update_superuser(name, superuser, db_session)
        db_session.commit()
        if client["ip"] == SERVER_IP:
            os.system('net start MSiSCSI')
        return({"STATUS": "OK", "DATA":status})
    except Exception as err:
        db_session.rollback()
        logger.error(err)
        return({"STATUS": "ERROR", "DATA": f'{err}'})



@app.get("/reboot/{name}")
async def reboot(name: str, db_session: Session = Depends(get_db_session)):
    try:
        client = get_client(name, db_session)
        client_ip = client["ip"]
        type = "cmd"
        command = 'shutdown /r /f /t 0'
        # Get the WebSocket instance for the specified client_id
        ws = active_websockets.get(client_ip)
        if ws:
            # Send a message to the WebSocket
            data = {"type" : type,
                    "command" : command                
            }
            await ws.send_json(data)
            return {"STATUS": "OK", "DATA": f"Отправлена команда на перезагрузку {name}"}
        else:
            return {"STATUS": "ERROR", "DATA": f"{name} не в сети"}
        
    except Exception as err:
        logger.error(err)
        return {"STATUS": "ERROR", "DATA": f"{err}"}
    
@app.get("/shutdown/{name}")
async def shutdown(name: str, db_session: Session = Depends(get_db_session)):
    try:
        client = get_client(name, db_session)
        client_ip = client["ip"]
        type = "cmd"
        command = 'shutdown /s /f /t 0'
        # Get the WebSocket instance for the specified client_id
        ws = active_websockets.get(client_ip)
        if ws:
            # Send a message to the WebSocket
            data = {"type" : type,
                    "command" : command                
            }
            await ws.send_json(data)
            return {"STATUS": "OK", "DATA": f"Отправлена команда на выключение {name}"}
        else:
            return {"STATUS": "ERROR", "DATA": f"{name} не в сети"}
        
    except Exception as err:
        logger.error(err)
        return {"STATUS": "ERROR", "DATA": f"{err}"}

@app.get("/poweron/{name}")
async def poweron(name: str, db_session: Session = Depends(get_db_session)):
    try:
        client = get_client(name, db_session)
        if not client["mac"]:
            return {"STATUS": "ERROR", "DATA": f"{name} не найден MAC адресс"}
        mac = client["mac"].replace(":", ".")
        
        # Send WoL packet using the wakeonlan library
        test = send_magic_packet(mac)
        return {"STATUS": "OK", "DATA": f"Wake-on-LAN packet sent to {name}"}
    except Exception as err:
        return {"STATUS": "ERROR", "DATA": f"{err}"}
    
@app.get("/cmd")
async def cmd(name: str,type: str, command: str, command_log: bool = False, db_session: Session = Depends(get_db_session)):
    try:
        client = get_client(name, db_session)
        client_ip = client["ip"]
        # Get the WebSocket instance for the specified client_id
        ws = active_websockets.get(client_ip)
        if ws:
            # Send a message to the WebSocket
            data = {"type" : type,
                    "command" : command,
                    "log": command_log              
            }
            await ws.send_json(data)
            return {"STATUS": "OK", "DATA": f"Отправлена команда на {name}"}
        else:
            return {"STATUS": "ERROR", "DATA": f"{name} не в сети"}
        
    except Exception as err:
        logger.error(err)
        return {"STATUS": "ERROR", "DATA": f"{err}"}
    
@app.websocket("/ws/{client_ip}")
async def websocket_endpoint(websocket: WebSocket, client_ip: str, db_session: Session = Depends(get_db_session)):
    await websocket.accept()
    active_websockets[client_ip] = websocket
    
    try:
        while True:
            data = await websocket.receive_json()
            print(f"подключен клиент {client_ip}")
            if data:
                if "mac" in data:
                    power_status(client_ip, True, db_session, data["mac"])
                    db_session.commit()
                elif "log" in data:
                    logger.error(f"Ответ от {client_ip}:{data['log']}")
            else:
                power_status(client_ip, True, db_session)
                db_session.commit()
            
    except WebSocketDisconnect:
        pass
    except OSError:
        pass
    except Exception as err:
        print(f"отключен клиент {client_ip}")
        power_status(client_ip, False, db_session)
        db_session.commit()
        logger.error(err)
    finally:
        del active_websockets[client_ip]
        print(f"отключен клиент {client_ip}")
        power_status(client_ip, False, db_session)
        db_session.commit()
        

    
if __name__ == "__main__":
    set_default_power()
    uvicorn.run("main:app", host="0.0.0.0", port=8000, ws_ping_interval=3, ws_ping_timeout=3)

    
