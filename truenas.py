import aiohttp
import asyncio
from config import API_KEY, API_URL, FATHER_DATASET, TRASH_DATASET, STORAGE

headers = {
    'Authorization': f'Bearer {API_KEY}',
    'Content-Type': 'application/json',
}

async def check_response(response):
    if response.status != 200:
        try:
            error_message = await response.json()
        except aiohttp.ClientError:
            error_message = await response.text()
        raise Exception(f"Ошибка выполнения запроса с кодом: {response.status}. Подробности об ошибке: {error_message}")
    else:
        data = await response.json()
        return data

async def create_snapshot(name):
    url = f'{API_URL}/zfs/snapshot'
    body = {
        "dataset": f'{STORAGE}/{FATHER_DATASET}',
        "name": name,
    }
    async with aiohttp.ClientSession(headers=headers) as session:
        async with session.post(url, json=body, ssl=False) as response:
            data = await check_response(response)
            snapshot_name = data.get('snapshot_name')
            if snapshot_name != name:
                raise Exception(f"Неизвестная ошибка создания снапшота. Подробности об ошибке: {data}")
            else:
                return True

async def create_dataset(name):
    url = f'{API_URL}/zfs/snapshot/clone'
    body = {
        "snapshot": f'{STORAGE}/{FATHER_DATASET}@{name}',
        "dataset_dst": f'{STORAGE}/{name}'
    }
    async with aiohttp.ClientSession(headers=headers) as session:
        async with session.post(url, json=body, ssl=False) as response:
            data = await check_response(response)
            if data != True:
                raise Exception(f"Неизвестная ошибка создания датасета. Подробности об ошибке: {data}")
            return f'{STORAGE}/{name}'

async def create_target(name):
    url = f'{API_URL}/iscsi/target'
    body = {
        "name": name, 
        "groups": [
            {
                "portal": 1,
                "initiator": 2,
                "authmethod": "NONE",
            }
        ],
    }
    async with aiohttp.ClientSession(headers=headers) as session:
        async with session.post(url, json=body, ssl=False) as response:
            data = await check_response(response)
            target_id = data.get('id')
            if not target_id:
                raise Exception(f"Неизвестная ошибка создания таргета. Подробности об ошибке: {data}")
            return target_id

async def create_extent(name):
    url = f'{API_URL}/iscsi/extent'
    body = {
        "name": name, 
        "type": "DISK",
        "disk": f'zvol/{STORAGE}/{name}',
        "blocksize": 4096,
        "insecure_tpc": True,
        "rpm": "SSD",
        "ro": False,
        "enabled": True
    }
    async with aiohttp.ClientSession(headers=headers) as session:
        async with session.post(url, json=body, ssl=False) as response:
            data = await check_response(response)
            extent_id = data.get('id')
            if not extent_id:
                raise Exception(f"Неизвестная ошибка создания extents. Подробности об ошибке: {data}")
            return extent_id

async def create_targetextent(target_id, extent_id):
    url = f'{API_URL}/iscsi/targetextent'
    body = {
        "target": target_id,
        "lunid": 0,
        "extent": extent_id
    }
    async with aiohttp.ClientSession(headers=headers) as session:
        async with session.post(url, json=body, ssl=False) as response:
            data = await check_response(response)
            targetextent_id = data.get('id')
            if not targetextent_id:
                raise Exception(f"Неизвестная ошибка создания Associated Targets. Подробности об ошибке: {data}")
            return targetextent_id

async def del_target(target_id):
    url = f'{API_URL}/iscsi/target/id/{int(target_id)}'
    async with aiohttp.ClientSession(headers=headers) as session:
        async with session.delete(url, ssl=False) as response:
            data = await check_response(response)
            if data != True:
                raise Exception(f"Неизвестная ошибка удаления Таргета. Подробности об ошибке: {data}")
            return data

async def del_dataset(dataset_name):
    dataset_id = f'{STORAGE}%2F{dataset_name}'
    url = f'{API_URL}/pool/dataset/id/{dataset_id}'
    async with aiohttp.ClientSession(headers=headers) as session:
        async with session.delete(url, ssl=False) as response:
            if response.status == 422 and "does not exist" in await response.text():
                return True
            data = await check_response(response)
            if data != True:
                raise Exception(f"Неизвестная ошибка удаления датасета. Подробности об ошибке: {data}")
            else:
                return True

async def del_snapshot(snapshot_name):
    snapshot_id = f'{STORAGE}%2F{FATHER_DATASET}@{snapshot_name}'
    url = f'{API_URL}/zfs/snapshot/id/{snapshot_id}'
    async with aiohttp.ClientSession(headers=headers) as session:
        async with session.delete(url, ssl=False) as response:
            if response.status == 422 and "not found" in await response.text():
                return True
            data = await check_response(response)
            if data != True:
                raise Exception(f"Неизвестная ошибка удаления датасета. Подробности об ошибке: {data}")
            return data

async def superclient_extent(name, extent_id, superuser):
    url = f'{API_URL}/iscsi/extent/id/{extent_id}'
    if superuser == True:
        body = {
            "disk": f'zvol/{STORAGE}/{FATHER_DATASET}',
        }
    else: 
        body = {
            "disk": f'zvol/{STORAGE}/{name}',
        }    
    async with aiohttp.ClientSession(headers=headers) as session:
        async with session.put(url, json=body, ssl=False) as response:
            data = await check_response(response)
            return data

async def trash_extent(name, extent_id, trash):
    url = f'{API_URL}/iscsi/extent/id/{extent_id}'
    if trash == True:
        body = {
            "disk": f'zvol/{STORAGE}/{TRASH_DATASET}',
        }
    else: 
        body = {
            "disk": f'zvol/{STORAGE}/{name}',
        }    
    async with aiohttp.ClientSession(headers=headers) as session:
        async with session.put(url, json=body, ssl=False) as response:
            data = await check_response(response)
            return data