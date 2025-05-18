# app.py
from flask import Flask, jsonify, request
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user

# ─────────────────── Flask и расширения ─────────────────── #
app = Flask(__name__)
app.config['SECRET_KEY'] = 'changeme-secret-key'            # замени на надёжный!
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///data.db' # далее поменяем на PostgreSQL
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

CORS(app, supports_credentials=True)
db        = SQLAlchemy(app)
bcrypt    = Bcrypt(app)
login_mgr = LoginManager(app)

# ─────────────────── Модели ─────────────────── #
class User(db.Model, UserMixin):
    id            = db.Column(db.Integer, primary_key=True)
    email         = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    role          = db.Column(db.String(20), default='client')  # client | master | admin
    name          = db.Column(db.String(80))
    photo         = db.Column(db.String(255))
    specialty     = db.Column(db.String(80))

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "photo": self.photo,
            "specialty": self.specialty,
            "role": self.role
        }

# ─────────────────── Login-manager ─────────────────── #
@login_mgr.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# ─────────────────── Эндпоинты ─────────────────── #
# 1. Публичный список мастеров  (пока все user-ы с role='master')
@app.get("/api/masters")
def api_masters():
    masters = User.query.filter_by(role='master').all()
    return jsonify([m.to_dict() for m in masters])

# 2. Регистрация
@app.post("/api/register")
def api_register():
    data = request.get_json()
    if not data or not data.get("email") or not data.get("password"):
        return {"error": "missing fields"}, 400

    if User.query.filter_by(email=data["email"]).first():
        return {"error": "exists"}, 400

    pw_hash = bcrypt.generate_password_hash(data["password"]).decode("utf-8")
    user = User(
        email         = data["email"],
        password_hash = pw_hash,
        role          = data.get("role", "client"),
        name          = data.get("name", ""),
        photo         = data.get("photo", ""),
        specialty     = data.get("specialty", "")
    )
    db.session.add(user)
    db.session.commit()
    return {"msg": "registered"}, 201

# 3. Логин
@app.post("/api/login")
def api_login():
    data = request.get_json()
    user = User.query.filter_by(email=data.get("email")).first()
    if user and bcrypt.check_password_hash(user.password_hash, data.get("password")):
        login_user(user)
        return {"msg": "ok", "user": user.to_dict()}
    return {"error": "invalid"}, 401

# 4. Логаут
@app.post("/api/logout")
@login_required
def api_logout():
    logout_user()
    return {"msg": "logged out"}

# ─────────────────── Инициализация БД ─────────────────── #
def seed_demo_masters():
    """Заполняем таблицу тремя мастерами, если база пустая."""
    if User.query.filter_by(role='master').first():
        return

    demo = [
        dict(email="elena@demo",  password="pass", role="master",
             name="Elena Star",   specialty="Astrologer",
             photo="https://randomuser.me/api/portraits/women/44.jpg"),
        dict(email="maxim@demo",  password="pass", role="master",
             name="Maxim Aura",   specialty="Tarot Reader",
             photo="https://randomuser.me/api/portraits/men/45.jpg"),
        dict(email="natalie@demo",password="pass", role="master",
             name="Natalie Numbers", specialty="Numerologist",
             photo="https://randomuser.me/api/portraits/women/68.jpg"),
    ]

    for u in demo:
        pw_hash = bcrypt.generate_password_hash(u["password"]).decode("utf-8")
        # Оставляем только допустимые поля
        data = {k: v for k, v in u.items() if k not in ("password",)}
        data["password_hash"] = pw_hash
        db.session.add(User(**data))

    db.session.commit()


with app.app_context():
    db.create_all()
    seed_demo_masters()

# ─────────────────── Запуск локально ─────────────────── #
if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 5001))
    app.run(host="0.0.0.0", port=port, debug=True)
