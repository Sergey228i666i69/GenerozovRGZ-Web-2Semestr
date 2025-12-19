from main import app
from models import User
from werkzeug.security import check_password_hash

with app.app_context():
    print("-" * 20)
    print("СПИСОК ПОЛЬЗОВАТЕЛЕЙ:")
    users = User.query.all()
    
    if not users:
        print("!!! В базе нет ни одного пользователя !!!")
        print("Вам нужно запустить init_db.py заново.")
    else:
        for u in users:
            print(f"ID: {u.id} | Логин: {u.login}")
            print(f"Хеш в базе: {u.password_hash}")
            
            # Пробуем проверить стандартный пароль
            try:
                is_valid = check_password_hash(u.password_hash, "Admin123!")
                print(f"Подходит ли пароль 'Admin123!': {is_valid}")
            except Exception as e:
                print(f"Ошибка проверки хеша: {e}")
    print("-" * 20)