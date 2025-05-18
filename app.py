from flask import Flask, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)              # разрешаем запросы с фронта

# ↓ Пока жёстко забитый список мастеров
masters = [
    {
        "id": 1,
        "name": "Elena Star",
        "specialty": "Astrologer",
        "photo": "https://randomuser.me/api/portraits/women/44.jpg"
    },
    {
        "id": 2,
        "name": "Maxim Aura",
        "specialty": "Tarot Reader",
        "photo": "https://randomuser.me/api/portraits/men/45.jpg"
    },
    {
        "id": 3,
        "name": "Natalie Numbers",
        "specialty": "Numerologist",
        "photo": "https://randomuser.me/api/portraits/women/68.jpg"
    }
]

@app.route("/api/masters")
def get_masters():
    return jsonify(masters)

if __name__ == "__main__":
    app.run(debug=True)
