# app.py
from flask import Flask, jsonify, request
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_login import (
    LoginManager, UserMixin, login_user, logout_user, login_required
)
from werkzeug.utils import secure_filename
import uuid, os

# ────────── базовая конфигурация ──────────
app = Flask(__name__)
app.config["SECRET_KEY"] = "changeme-secret-key"
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///data.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
CORS(app, supports_credentials=True)

db     = SQLAlchemy(app)
bcrypt = Bcrypt(app)
login_mgr = LoginManager(app)


# ────────── модель ──────────
class User(db.Model, UserMixin):
    __tablename__ = "users" 
    id            = db.Column(db.Integer, primary_key=True)
    email         = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    role          = db.Column(db.String(20), default="client")   # client | master | admin
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

@login_mgr.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# ────────── загрузка фото ──────────
UPLOAD_DIR = os.path.join(app.root_path, "static", "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)
ALLOWED = {"jpg", "jpeg", "png", "gif", "webp"}

@app.post("/api/upload")
def api_upload():
    if "file" not in request.files:
        return {"error": "no file"}, 400
    f = request.files["file"]
    ext = f.filename.rsplit(".", 1)[-1].lower()
    if ext not in ALLOWED:
        return {"error": "bad type"}, 400
    filename = f"{uuid.uuid4().hex}.{ext}"
    path = os.path.join(UPLOAD_DIR, secure_filename(filename))
    f.save(path)
    return {"url": f"/static/uploads/{filename}"}, 201

# ────────── публичные мастера ──────────
@app.get("/api/masters")
def api_masters():
    masters = User.query.filter_by(role="master").all()
    return jsonify([m.to_dict() for m in masters])

# ────────── регистрация ──────────
@app.post("/api/register")
def api_register():
    data = request.get_json()
    if not data.get("email") or not data.get("password"):
        return {"error": "missing fields"}, 400
    if User.query.filter_by(email=data["email"]).first():
        return {"error": "exists"}, 400
    pw_hash = bcrypt.generate_password_hash(data["password"]).decode("utf-8")
    user = User(
        email=data["email"],
        password_hash=pw_hash,
        role=data.get("role", "client"),
        name=data.get("name", ""),
        photo=data.get("photo", ""),
        specialty=data.get("specialty", "")
    )
    db.session.add(user)
    db.session.commit()
    return {"msg": "registered"}, 201

# ────────── логин / логаут ──────────
@app.post("/api/login")
def api_login():
    data = request.get_json()
    user = User.query.filter_by(email=data.get("email"))._
