from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import sqlite3, os

DB_PATH = os.path.join(os.path.dirname(__file__), "database.db")

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------- Models ----------
class User(BaseModel):
    email: str
    password: str

class PointAdd(BaseModel):
    email: str
    amount: int

# 🔧 관리자용
class AdminAdjust(BaseModel):
    email: str
    points: int

# ---------- DB ----------
def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE,
            password TEXT,
            points INTEGER DEFAULT 0,
            kickboard INTEGER DEFAULT 0
        )
    """)
    conn.commit()
    conn.close()

init_db()

# ---------- Auth ----------
@app.post("/signup")
def signup(user: User):
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute(
            "INSERT INTO users (email, password) VALUES (?, ?)",
            (user.email, user.password)
        )
        conn.commit()
        conn.close()
        return {"success": True}
    except:
        return {"success": False}

@app.post("/login")
def login(user: User):
    if user.email == "admin@gmail.com" and user.password == "admin":
        return {"success": True, "role": "admin"}

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT password FROM users WHERE email=?", (user.email,))
    row = c.fetchone()
    conn.close()

    if row and row[0] == user.password:
        return {"success": True, "role": "user"}

    return {"success": False}

# ---------- User ----------
@app.get("/me/{email}")
def get_user(email: str):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT email, points, kickboard FROM users WHERE email = ?", (email,))
    row = c.fetchone()
    conn.close()

    if row:
        return {
            "email": row[0],
            "points": row[1] or 0,
            "kickboard": row[2] or 0
        }
    return {"email": email, "points": 0, "kickboard": 0}
# ---------- Points ----------
@app.post("/points/add")
def add_points(data: dict):
    email = data['email']
    amount = data['amount']

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # 먼저 레코드 존재 확인
    c.execute("SELECT points FROM users WHERE email = ?", (email,))
    row = c.fetchone()
    if not row:
        conn.close()
        return {"success": False, "message": "존재하지 않는 사용자입니다"}

    # 포인트 업데이트
    new_points = row[0] + amount
    c.execute("UPDATE users SET points = ? WHERE email = ?", (new_points, email))
    conn.commit()
    conn.close()

    return {"success": True, "points": new_points}


# ---------- 킥보드 구매 ----------
@app.post("/kickboard/buy")
def buy_kickboard(data: dict):
    email = data['email']
    cost = 1000

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # 레코드 존재 확인
    c.execute("SELECT points, kickboard FROM users WHERE email = ?", (email,))
    row = c.fetchone()
    if not row:
        conn.close()
        return {"success": False, "message": "존재하지 않는 사용자입니다"}

    current_points = row[0]
    kickboard = row[1]
    if current_points < cost:
        conn.close()
        return {"success": False, "message": "포인트가 부족합니다"}
    
    if kickboard == 1:
        conn.close()
        return {"success": False, "message": "이미 킥보드를 구매했습니다"}
    new_points = current_points - cost
    kickboard = 1  # 킥보드 구매 표시
    c.execute("UPDATE users SET points = ?, kickboard = ? WHERE email = ?", (new_points, kickboard, email))
    conn.commit()
    conn.close()

    return {"success": True, "points": new_points, "kickboard": 1, "message": "킥보드가 구매되었습니다."}

@app.post("/kickboard/return")
def return_kickboard(data: dict):
    email = data['email']

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # 레코드 존재 확인
    c.execute("SELECT points,kickboard FROM users WHERE email = ?", (email,))
    row = c.fetchone()
    if not row:
        conn.close()
        return {"success": False, "message": "존재하지 않는 사용자입니다."}

    points = row[0]
    kickboard = row[1]
    if kickboard == 0:
        conn.close()
        return {"success": False, "message": "킥보드를 구매하지 않았습니다."}

    kickboard = 0  # 킥보드 반납 표시
    c.execute("UPDATE users SET kickboard = ? WHERE email = ?", (kickboard, email))
    conn.commit()
    conn.close()

    return {
    "success": True,
    "points": points,
    "kickboard": 0,
    "message": "킥보드가 반납되었습니다."
}


# ---------- 🛠 관리자 ----------
@app.get("/admin/users")
def admin_users():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT email, points, kickboard FROM users")
    users = c.fetchall()
    conn.close()

    return [
        {
            "email": u[0],
            "points": u[1],
            "kickboard": u[2]
        } for u in users
    ]

@app.post("/admin/adjust")
def admin_adjust(data: AdminAdjust):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        UPDATE users
        SET points=?, kickboard=?
        WHERE email=?
    """, (data.points, data.kickboard, data.email))
    conn.commit()
    conn.close()
    return {"success": True}

@app.post("/admin/delete")
def admin_delete(data: dict):
    email = data['email']
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("DELETE FROM users WHERE email=?", (email,))
    conn.commit()
    conn.close()
    return {"success": True}
