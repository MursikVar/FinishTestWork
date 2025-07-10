import psycopg2
from psycopg2 import OperationalError
from config import DB_CONFIG

class Database:
    def __init__(self):
        self.connection = None
        self.cursor = None
        
        if not DB_CONFIG.get('password'):
            print("Внимание: пароль для БД не указан в конфигурации!")
        
        try:
            self.connection = psycopg2.connect(
                dbname=DB_CONFIG['dbname'],
                user=DB_CONFIG['user'],
                password=DB_CONFIG['password'],
                host=DB_CONFIG['host'],
                port=DB_CONFIG['port']
            )
            self.cursor = self.connection.cursor()
            print("Успешное подключение к PostgreSQL")
        except OperationalError as e:
            print(f"Ошибка подключения к PostgreSQL: {e}")
        except KeyError as e:
            print(f"Отсутствует ключ в конфигурации БД: {e}")
        except Exception as e:
            print(f"Неизвестная ошибка при подключении: {e}")

    def execute(self, query, params=None, commit=False):
        if not self.connection:
            print("Нет подключения к БД. Запрос не выполнен.")
            return None
            
        try:
            self.cursor.execute(query, params or ())
            if commit:
                self.connection.commit()
            return self.cursor
        except Exception as e:
            print(f"Ошибка выполнения SQL-запроса: {e}")
            if commit:
                self.connection.rollback()
            return None

    def fetch_one(self, query, params=None):
        if not self.connection:
            return None
        try:
            self.cursor.execute(query, params or ())
            return self.cursor.fetchone()
        except Exception as e:
            print(f"Ошибка при получении данных: {e}")
            return None

    def fetch_all(self, query, params=None):
        if not self.connection:
            return []
        try:
            self.cursor.execute(query, params or ())
            return self.cursor.fetchall()
        except Exception as e:
            print(f"Ошибка при получении данных: {e}")
            return []

    def close(self):
        """Явное закрытие соединения с базой данных"""
        try:
            if self.cursor:
                self.cursor.close()
            if self.connection:
                self.connection.close()
                print("Соединение с PostgreSQL закрыто")
        except Exception as e:
            print(f"Ошибка при закрытии соединения: {e}")
        finally:
            self.cursor = None
            self.connection = None