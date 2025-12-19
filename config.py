import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev_secret_key")

    DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///service_market.db")
    SQLALCHEMY_DATABASE_URI = DATABASE_URL
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    STUDENT_NAME = os.getenv("STUDENT_NAME", "ФИО не задано")
    STUDENT_GROUP = os.getenv("STUDENT_GROUP", "Группа не задана")
    VARIANT = os.getenv("VARIANT", "??")
