from database import Database

def test_db_connection():
    print("Тестирование подключения к PostgreSQL...")
    db = Database()
    
    try:
        # Проверка версии PostgreSQL
        result = db.fetch_one("SELECT version();")
        if result:
            print("Успех! Версия PostgreSQL:", result[0])
        else:
            print("Не удалось получить данные")
            
        # Проверка существования таблицы users
        result = db.fetch_one("SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'users');")
        if result:
            print("Таблица users существует:", result[0])
        else:
            print("Не удалось проверить таблицу users")
            
    except Exception as e:
        print("Ошибка при тестировании:", e)
    finally:
        db.close()

if __name__ == "__main__":
    test_db_connection()