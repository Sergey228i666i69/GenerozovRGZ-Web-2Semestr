from main import app, init_db

with app.app_context():
    init_db()
