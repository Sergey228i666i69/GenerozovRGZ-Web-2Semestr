import random
import re
from functools import wraps

from flask import Flask, jsonify, request, session, render_template
from werkzeug.security import generate_password_hash, check_password_hash

from config import Config
from models import db, User

# --------- Константы/валидация ----------
LOGIN_RE = re.compile(r"^[A-Za-z0-9!@#$%^&*()_\-+=\[\]{};:'\",.<>/?\\|`~]{3,50}$")
PASS_RE  = re.compile(r"^[A-Za-z0-9!@#$%^&*()_\-+=\[\]{};:'\",.<>/?\\|`~]{6,80}$")

SERVICE_TYPES = [
    "репетитор", "бухгалтер", "программист", "дизайнер", "юрист",
    "фотограф", "маркетолог", "психолог", "переводчик", "сантехник"
]

def validate_profile_fields(data):
    errors = []

    name = (data.get("name") or "").strip()
    service_type = (data.get("service_type") or "").strip()
    about = (data.get("about") or "").strip()

    exp = data.get("experience_years")
    price = data.get("price")

    if not name or len(name) < 2:
        errors.append("Имя должно быть не короче 2 символов.")

    if service_type not in SERVICE_TYPES:
        errors.append("Выбери вид услуги из списка.")

    try:
        exp = int(exp)
        if exp < 0 or exp > 80:
            errors.append("Стаж должен быть в диапазоне 0..80.")
    except Exception:
        errors.append("Стаж должен быть целым числом.")

    try:
        price = int(price)
        if price <= 0 or price > 10_000_000:
            errors.append("Цена должна быть положительным числом.")
    except Exception:
        errors.append("Цена должна быть целым числом.")

    if about and len(about) > 2000:
        errors.append("Поле 'О себе' слишком длинное (макс 2000 символов).")

    return errors, name, service_type, exp, price, about


# --------- Приложение ----------
app = Flask(__name__)
app.config.from_object(Config)

db.init_app(app)

# --------- Хелперы авторизации ----------
def current_user():
    uid = session.get("user_id")
    if not uid:
        return None
    return db.session.get(User, uid)

def login_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        user = current_user()
        if not user:
            return jsonify({"ok": False, "error": "Требуется авторизация."}), 401
        return fn(*args, **kwargs)
    return wrapper

def admin_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        user = current_user()
        if not user or not user.is_admin:
            return jsonify({"ok": False, "error": "Требуются права администратора."}), 403
        return fn(*args, **kwargs)
    return wrapper

# --------- Рендер страниц (фронт работает через REST) ----------
@app.get("/")
def page_index():
    return render_template("index.html")

@app.get("/profile")
def page_profile():
    return render_template("profile.html")

@app.get("/admin")
def page_admin():
    return render_template("admin.html")

@app.context_processor
def inject_student_info():
    return {
        "STUDENT_NAME": app.config["STUDENT_NAME"],
        "STUDENT_GROUP": app.config["STUDENT_GROUP"],
        "VARIANT": app.config["VARIANT"],
    }

# --------- API: AUTH ----------
@app.get("/api/auth/me")
def api_me():
    user = current_user()
    if not user:
        return jsonify({"ok": True, "user": None})
    return jsonify({"ok": True, "user": user.to_admin_dict() if user.is_admin else {
        **user.to_public_dict(),
        "login": user.login,
        "is_hidden": user.is_hidden,
        "is_admin": user.is_admin,
    }})

@app.post("/api/auth/register")
def api_register():
    data = request.get_json(force=True, silent=True) or {}
    login = (data.get("login") or "").strip()
    password = (data.get("password") or "").strip()

    if not LOGIN_RE.match(login):
        return jsonify({"ok": False, "error": "Логин: 3-50 символов, латиница/цифры/знаки."}), 400
    if not PASS_RE.match(password):
        return jsonify({"ok": False, "error": "Пароль: 6-80 символов, латиница/цифры/знаки."}), 400

    if User.query.filter_by(login=login).first():
        return jsonify({"ok": False, "error": "Такой логин уже занят."}), 400

    u = User(
        login=login,
        password_hash=generate_password_hash(password),  # соль внутри werkzeug
        is_admin=False,
        is_hidden=False
    )
    db.session.add(u)
    db.session.commit()

    session["user_id"] = u.id
    return jsonify({"ok": True, "message": "Регистрация успешна.", "user": {"login": u.login}})

@app.post("/api/auth/login")
def api_login():
    data = request.get_json(force=True, silent=True) or {}
    login = (data.get("login") or "").strip()
    password = (data.get("password") or "").strip()

    u = User.query.filter_by(login=login).first()
    if not u or not check_password_hash(u.password_hash, password):
        return jsonify({"ok": False, "error": "Неверный логин или пароль."}), 401

    session["user_id"] = u.id
    return jsonify({"ok": True, "message": "Вход выполнен."})

@app.post("/api/auth/logout")
def api_logout():
    session.pop("user_id", None)
    return jsonify({"ok": True, "message": "Вы вышли из аккаунта."})

# --------- API: Поиск профилей ----------
@app.get("/api/profiles")
def api_profiles():
    # фильтры
    name = (request.args.get("name") or "").strip().lower()
    service_type = (request.args.get("service_type") or "").strip()
    exp_min = request.args.get("exp_min")
    exp_max = request.args.get("exp_max")
    price_min = request.args.get("price_min")
    price_max = request.args.get("price_max")

    page = int(request.args.get("page", 1))
    per_page = 5

    q = User.query

    # скрытые не показываем никому, кроме админа и владельца (в списке — только админ)
    user = current_user()
    if not (user and user.is_admin):
        q = q.filter(User.is_hidden.is_(False))

    # заполненные анкеты (чтобы не светить пустые)
    q = q.filter(User.name.isnot(None), User.service_type.isnot(None), User.experience_years.isnot(None), User.price.isnot(None))

    if name:
        q = q.filter(User.name.ilike(f"%{name}%"))
    if service_type:
        q = q.filter(User.service_type == service_type)

    def to_int(x):
        try:
            return int(x)
        except Exception:
            return None

    emin = to_int(exp_min)
    emax = to_int(exp_max)
    pmin = to_int(price_min)
    pmax = to_int(price_max)

    if emin is not None:
        q = q.filter(User.experience_years >= emin)
    if emax is not None:
        q = q.filter(User.experience_years <= emax)
    if pmin is not None:
        q = q.filter(User.price >= pmin)
    if pmax is not None:
        q = q.filter(User.price <= pmax)

    q = q.order_by(User.updated_at.desc())

    pagination = q.paginate(page=page, per_page=per_page, error_out=False)
    items = [u.to_public_dict() for u in pagination.items]

    return jsonify({
        "ok": True,
        "items": items,
        "page": page,
        "per_page": per_page,
        "total": pagination.total,
        "has_next": pagination.has_next,
        "has_prev": pagination.has_prev
    })

# --------- API: Мой профиль ----------
@app.put("/api/me/profile")
@login_required
def api_update_my_profile():
    user = current_user()
    data = request.get_json(force=True, silent=True) or {}

    errors, name, service_type, exp, price, about = validate_profile_fields(data)
    if errors:
        return jsonify({"ok": False, "error": " ".join(errors)}), 400

    user.name = name
    user.service_type = service_type
    user.experience_years = exp
    user.price = price
    user.about = about or None

    db.session.commit()
    return jsonify({"ok": True, "message": "Анкета обновлена."})

@app.patch("/api/me/hide")
@login_required
def api_hide_my_profile():
    user = current_user()
    data = request.get_json(force=True, silent=True) or {}
    is_hidden = bool(data.get("is_hidden"))

    user.is_hidden = is_hidden
    db.session.commit()
    return jsonify({"ok": True, "message": "Готово.", "is_hidden": user.is_hidden})

@app.delete("/api/me")
@login_required
def api_delete_me():
    user = current_user()
    uid = user.id
    session.pop("user_id", None)

    db.session.delete(user)
    db.session.commit()
    return jsonify({"ok": True, "message": f"Аккаунт удалён (id={uid})."})

# --------- API: Админка ----------
@app.get("/api/admin/users")
@admin_required
def api_admin_users():
    page = int(request.args.get("page", 1))
    per_page = 10

    q = User.query.order_by(User.created_at.desc())
    pagination = q.paginate(page=page, per_page=per_page, error_out=False)

    return jsonify({
        "ok": True,
        "items": [u.to_admin_dict() for u in pagination.items],
        "page": page,
        "per_page": per_page,
        "total": pagination.total,
        "has_next": pagination.has_next,
        "has_prev": pagination.has_prev
    })

@app.put("/api/admin/users/<int:user_id>")
@admin_required
def api_admin_update_user(user_id: int):
    u = db.session.get(User, user_id)
    if not u:
        return jsonify({"ok": False, "error": "Пользователь не найден."}), 404

    data = request.get_json(force=True, silent=True) or {}

    # можно обновить анкету и флаги
    if "name" in data or "service_type" in data or "experience_years" in data or "price" in data or "about" in data:
        errors, name, service_type, exp, price, about = validate_profile_fields({
            "name": data.get("name", u.name),
            "service_type": data.get("service_type", u.service_type),
            "experience_years": data.get("experience_years", u.experience_years),
            "price": data.get("price", u.price),
            "about": data.get("about", u.about),
        })
        if errors:
            return jsonify({"ok": False, "error": " ".join(errors)}), 400
        u.name = name
        u.service_type = service_type
        u.experience_years = exp
        u.price = price
        u.about = about or None

    if "is_hidden" in data:
        u.is_hidden = bool(data["is_hidden"])

    # запретим разжаловать/удалить последнего админа случайно — оставим просто запрет на снятие флага у admin-логина
    if "is_admin" in data and u.login != "admin":
        u.is_admin = bool(data["is_admin"])

    db.session.commit()
    return jsonify({"ok": True, "message": "Обновлено.", "user": u.to_admin_dict()})

@app.delete("/api/admin/users/<int:user_id>")
@admin_required
def api_admin_delete_user(user_id: int):
    u = db.session.get(User, user_id)
    if not u:
        return jsonify({"ok": False, "error": "Пользователь не найден."}), 404
    if u.login == "admin":
        return jsonify({"ok": False, "error": "Нельзя удалить admin через панель."}), 400

    db.session.delete(u)
    db.session.commit()
    return jsonify({"ok": True, "message": "Пользователь удалён."})

# --------- CLI: инициализация и сиды (30+ пользователей) ----------
@app.cli.command("init-db")
def init_db():
    """Создать таблицы и заполнить демо-данными (admin + 30 users)."""
    db.drop_all()
    db.create_all()

    # admin
    admin = User(
        login="admin",
        password_hash=generate_password_hash("Admin123!"),
        is_admin=True,
        is_hidden=False,
        name="Администратор",
        service_type="программист",
        experience_years=10,
        price=5000,
        about="Админ сайта: управление анкетами пользователей."
    )
    db.session.add(admin)

    names = [
        "Алексей", "Мария", "Иван", "Екатерина", "Дмитрий", "Анна", "Сергей", "Ольга",
        "Никита", "Татьяна", "Павел", "Наталья", "Артём", "Юлия", "Владимир", "Ксения",
        "Михаил", "Алина", "Роман", "Виктория", "Григорий", "Дарья", "Егор", "Полина",
        "Константин", "София", "Андрей", "Елена", "Степан", "Ирина", "Максим", "Лидия"
    ]
    abouts = [
        "Работаю аккуратно и по договорённости, объясняю простым языком.",
        "Есть портфолио и отзывы, беру задачи разной сложности.",
        "Помогаю быстро и без лишней бюрократии.",
        "Подстраиваюсь под цель клиента, люблю понятные требования.",
        "Ориентируюсь на качество, сроки и прозрачную цену."
    ]

    # 30 пользователей
    for i in range(1, 31):
        login = f"user{i:02d}"
        u = User(
            login=login,
            password_hash=generate_password_hash("User123!"),
            is_admin=False,
            is_hidden=False,
            name=f"{random.choice(names)} {random.choice(['Иванов','Петров','Сидоров','Кузнецов','Смирнов','Фёдоров','Орлова','Васильева'])}",
            service_type=random.choice(SERVICE_TYPES),
            experience_years=random.randint(0, 25),
            price=random.choice([500, 800, 1000, 1500, 2000, 2500, 3000, 3500, 4000]),
            about=random.choice(abouts)
        )
        db.session.add(u)

    db.session.commit()
    print("OK: DB initialized. Admin: admin / Admin123! ; Users: user01..user30 / User123!")

if __name__ == "__main__":
    app.run(debug=True)
