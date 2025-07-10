import os
from dotenv import load_dotenv

# Загрузка переменных из .env (если файл существует)
load_dotenv()

# Прямое указание токена бота
BOT_TOKEN = "8067059095:AAGV64ZXCLRu3myGj81wSMYIaEVizSnGDDo"

# Прямое указание параметров БД
DB_CONFIG = {
    'dbname': 'news_aggregator',
    'user': 'news_bot',
    'password': 'admin',  # Ваш пароль
    'host': 'localhost',
    'port': '5432'
}

