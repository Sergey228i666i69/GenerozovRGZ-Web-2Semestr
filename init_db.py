from main import app, db, init_db
from models import User
# Если у вас есть отдельная модель для специалистов, импортируйте её:
# from models import Specialist 
from werkzeug.security import generate_password_hash

with app.app_context():
    # 1. Создаем пустые таблицы
    init_db() 
    
    # 2. Проверяем, пустая ли база, чтобы не дублировать данные
    if not User.query.first():
        print("База данных пуста. Заполняем тестовыми данными...")

        # Создаем тестового пользователя
        # ВАЖНО: Проверьте в models.py, какие точно поля у модели User
        test_user = User(
            login="test_user",
            # Пароль обязательно нужно хешировать, так как main.py использует check_password_hash
            password_hash=generate_password_hash("password123") 
        )
        db.session.add(test_user)

        # Если специалисты хранятся в отдельной таблице, добавьте одного:
        # test_spec = Specialist(
        #     name="Иван Иванов",
        #     about="Ремонт любой сложности",
        #     price=500
        # )
        # db.session.add(test_spec)

        # Сохраняем изменения
        db.session.commit()
        print("Данные успешно добавлены!")
    else:
        print("База данных уже содержит данные.")