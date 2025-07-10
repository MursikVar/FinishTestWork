import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = "8067059095:AAGV64ZXCLRu3myGj81wSMYIaEVizSnGDDo"

DB_CONFIG = {
    'dbname': 'news_aggregator',
    'user': 'news_bot',
    'password': 'admin', 
    'host': 'localhost',
    'port': '5432'
}

