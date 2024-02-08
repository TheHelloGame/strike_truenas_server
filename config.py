from dotenv import load_dotenv
import os

load_dotenv()

DB_URL = os.environ.get("DB_URL")
API_KEY = os.environ.get("API_KEY")
API_URL = os.environ.get("API_URL")
STORAGE = os.environ.get("STORAGE")
FATHER_DATASET = os.environ.get("FATHER_DATASET")
TRASH_DATASET = os.environ.get("TRASH_DATASET")
TIMEZONE = int(os.environ.get("TIMEZONE"))
LOGIN = os.environ.get("LOGIN")
PASS = os.environ.get("PASS")
SERVER_IP = os.environ.get("SERVER_IP")