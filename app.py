from flask import Flask, jsonify, request
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_login import (
    LoginManager, UserMixin, login_user, logout_user, login_required, current_user
)
from werkzeug.utils import secure_filename
import uuid, os

app = Flask(__name__)
app.config.update(
    SECRET_KEY="changeme-secret-key",
    SQLALCHEMY_DATABASE_URI=os.getenv("DATABASE_URL", "sqlite:///data.db").replace(
        "postgres://", "postgresql+psycopg2://", 1
    ),
    SQLALCHEMY_TRACK_MODIFICATIONS=False,
    SESSION_COOKIE_SAMESITE="None",
    SESSION_COOKIE_SECURE=True
)

CORS(app, supports_credentials=True)
db      = SQLAlchemy(app)
bcrypt  = Bcrypt(app)
login_m = LoginManager(app)

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
        return {"id": self.id, "email": self.email, "name": self.name,
                "photo": self.photo, "specialty": self.specialty, "role": self.role}

@login_m.user_loader
def load_user(uid): return User.query.get(int(uid))

# ─── Upload ───────────────────────────────────────────────
UPLOAD_DIR = os.path.join(app.root_path, "static", "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)
ALLOWED = {"jpg","jpeg","png","gif","webp"}

@app.post("/api/upload")
@login_required
def api_upload():
    if "file" not in request.files:            return {"error":"no file"},400
    f=request.files["file"]; ext=f.filename.rsplit(".",1)[-1].lower()
    if ext not in ALLOWED:                     return {"error":"bad type"},400
    name=f"{uuid.uuid4().hex}.{ext}"
    f.save(os.path.join(UPLOAD_DIR,secure_filename(name)))
    return {"url":f"/static/uploads/{name}"},201

# ─── Публичный каталог ───────────────────────────────────
@app.get("/api/masters")
def api_masters():
    return jsonify([m.to_dict() for m in User.query.filter_by(role="master")])

# ─── Аутентификация ──────────────────────────────────────
@app.post("/api/register")
def api_register():
    d=request.get_json()
    if not d.get("email") or not d.get("password"): return {"error":"missing"},400
    if User.query.filter_by(email=d["email"]).first(): return {"error":"exists"},400
    user=User(email=d["email"],
              password_hash=bcrypt.generate_password_hash(d["password"]).decode(),
              role=d.get("role","client"),
              name=d.get("name",""), photo=d.get("photo",""), specialty=d.get("specialty",""))
    db.session.add(user); db.session.commit(); login_user(user)
    return {"msg":"registered","user":user.to_dict()},201

@app.post("/api/login")
def api_login():
    d=request.get_json()
    u=User.query.filter_by(email=d.get("email")).first()
    if u and bcrypt.check_password_hash(u.password_hash,d.get("password")):
        login_user(u); return {"msg":"ok","user":u.to_dict()}
    return {"error":"invalid"},401

@app.post("/api/logout")
@login_required
def api_logout(): logout_user(); return {"msg":"logged out"}

@app.get("/api/me")
def api_me():
    return (current_user.to_dict(),200) if current_user.is_authenticated else ({"user":None},200)

# ─── Обновление профиля (мастер) ─────────────────────────
@app.post("/api/update_profile")
@login_required
def api_update():
    if current_user.role!="master": return {"error":"forbidden"},403
    d=request.get_json()
    for field in ("name","specialty","photo"):
        if field in d: setattr(current_user, field, d[field])
    db.session.commit()
    return {"msg":"updated","user":current_user.to_dict()}

# ─── Демо-данные ──────────────────────────────────────────
def seed_demo():
    if User.query.filter_by(role="master").count()>=3: return
    demo=[("elena@demo","Elena Star","Astrologer","https://randomuser.me/api/portraits/women/44.jpg"),
          ("maxim@demo","Maxim Aura","Tarot Reader","https://randomuser.me/api/portraits/men/45.jpg"),
          ("natalie@demo","Natalie Numbers","Numerologist","https://randomuser.me/api/portraits/women/68.jpg")]
    for e,n,s,p in demo:
        if User.query.filter_by(email=e).first(): continue
        db.session.add(User(email=e,password_hash=bcrypt.generate_password_hash("pass").decode(),
                            role="master",name=n,photo=p,specialty=s))
    db.session.commit()

with app.app_context(): db.create_all(); seed_demo()

if __name__=="__main__":
    app.run(port=int(os.getenv("PORT",5000)),debug=True)
