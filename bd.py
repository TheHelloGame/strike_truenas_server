from sqlalchemy import Table, create_engine,Text
from config import DB_URL, TIMEZONE
from pydantic import BaseModel
from sqlalchemy.orm import Session,sessionmaker
from sqlalchemy import MetaData, Column, Integer, String, TIMESTAMP, insert, select, Boolean
from datetime import datetime, timedelta
from fastapi import Depends
metadata= MetaData()

engine = create_engine(url=DB_URL,echo=False)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
client = Table(
    'client',
    metadata,
    Column("name",String, primary_key=True),
    Column("ip",String,unique=True, nullable=False),
    Column("extent_id",Integer,unique=True, nullable=False),
    Column("time_update",TIMESTAMP, default=datetime.utcnow),
    Column("superuser",Boolean, default=False),
    Column("power",Boolean, default=False),
    Column("mac",Integer)
)


metadata.create_all(bind=engine)

def set_default_power():
    session = SessionLocal()
    try:
        # Обновляем значение поля power для всех записей в таблице client
        session.execute(client.update().values(power=False))
        session.commit()
    except Exception as e:
        print(f"Ошибка при обновлении значений поля power: {e}")
        session.rollback()
    finally:
        session.close()


def get_db_session():
    db_seession = SessionLocal()
    try:
        yield db_seession
    finally:
        db_seession.close()
        
def add_client(name, ip, extent_id, db_session):
    try:
        stmt = insert(client).values(name=name, ip=ip, extent_id=extent_id)
        db_session.execute(stmt)
    except Exception as err:
        raise Exception(f"Ошибка записи в БД. Подробности об ошибке: {err}")

def get_client(name,db_session):
    try:
        stmt = select(client).where(client.c.name == name)
        results = db_session.execute(stmt).mappings().first()
    except Exception as err:
        raise Exception(f"Ошибка поиска в БД. Подробности об ошибке: {err}")
    return results

def get_client_by_ip(ip,db_session):
    try:
        stmt = select(client).where(client.c.ip == ip)
        results = db_session.execute(stmt).mappings().first()
    except Exception as err:
        raise Exception(f"Ошибка поиска в БД. Подробности об ошибке: {err}")
    return results


def del_client(name,db_session):
    try:
        stmt = client.delete().where(client.c.name == name)
        results = db_session.execute(stmt)
    except Exception as err:
        raise Exception(f"Ошибка удаления из БД. Подробности об ошибке: {err}")
    return results

def get_all_client(db_session):
    try:
        stmt = select(client)
        results = db_session.execute(stmt).mappings().all()
        timezone_results = []
        for result in results:
            result_dict = dict(result)
            result_dict['time_update'] = result_dict['time_update'] + timedelta(hours=TIMEZONE)
            timezone_results.append(result_dict)
    except Exception as err:
        raise Exception(f"Ошибка поиска в БД. Подробности об ошибке: {err}")
    return timezone_results

def update_dataset_time(name,db_session):
    try:
        stmt = (
            client.update()
            .where(client.c.name == name)
            .values(time_update=datetime.utcnow())
        )
        results = db_session.execute(stmt)
    except Exception as err:
        raise Exception(f"Ошибка обновления времени в БД. Подробности об ошибке: {err}")
    return results

def get_all_superuser(db_session):
    try:
        stmt = select(client).where(client.c.superuser == True)
        results = db_session.execute(stmt).mappings().first()
    except Exception as err:
        raise Exception(f"Ошибка поиска в БД. Подробности об ошибке: {err}")
    return results

def update_superuser(name, superuser, db_seession):
    try:
        stmt = (
            client.update()
            .where(client.c.name == name)
            .values(superuser=superuser)
        )
        results = db_seession.execute(stmt)
    except Exception as err:
        raise Exception(f"Ошибка обновления времени в БД. Подробности об ошибке: {err}")
    return results

def power_status(ip, status, db_session, mac = None):
    try:
        # Поиск клиента по IP-адресу
        client_record = get_client_by_ip(ip, db_session)
        
        if client_record:
            # Формирование значений для обновления
            update_values = {'power': status}
            if mac is not None:
                update_values['mac'] = mac
            
            # Обновление значений в базе данных
            stmt = (
                client.update()
                .where(client.c.ip == ip)
                .values(**update_values)
            )
            db_session.execute(stmt)
            
            return True
    except Exception as err:
        print(err)
    