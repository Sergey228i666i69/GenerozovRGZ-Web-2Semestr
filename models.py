from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)

    login = db.Column(db.String(50), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)

    name = db.Column(db.String(120), nullable=True)
    service_type = db.Column(db.String(80), nullable=True, index=True)
    experience_years = db.Column(db.Integer, nullable=True, index=True)   # стаж (лет)
    price = db.Column(db.Integer, nullable=True, index=True)              # цена (руб)
    about = db.Column(db.Text, nullable=True)

    is_hidden = db.Column(db.Boolean, default=False, nullable=False, index=True)
    is_admin = db.Column(db.Boolean, default=False, nullable=False, index=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    def to_public_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "service_type": self.service_type,
            "experience_years": self.experience_years,
            "price": self.price,
            "about": self.about,
        }

    def to_admin_dict(self):
        d = self.to_public_dict()
        d.update({
            "login": self.login,
            "is_hidden": self.is_hidden,
            "is_admin": self.is_admin,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        })
        return d
