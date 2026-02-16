from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import sqlite3, os

# ---------------- DB PATH ----------------
DB_PATH = os.environ.get("DB_PATH") or os.path.join(os.getcwd(), "database.db")

# ---------------- FastAPI ----------------
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------- Models ----------------
class User(BaseModel):
    email: str
    password: str

class PointAdd(BaseModel):
    email: str
    amount: int

class AdminAdjust(BaseModel):
    email: str
    points: int
    kickboard: int

class KickboardAction(BaseModel):
    email: str

# ---------------- DB Init ----------------
def init_db():
    try:
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
    except Exception as e:
        print("DB Init Error:", e)
    finally:
        conn.close()

init_db()

# ---------------- Auth ----------------
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
        return {"success": True}
    except sqlite3.IntegrityError:
        return {"success": False, "message": "이미 존재하는 사용자입니다."}
    except Exception as e:
        print("Signup Error:", e)
        return {"success": False, "message": "서버 에러 발생"}
    finally:
        conn.close()

@app.post("/login")
def login(user: User):
    try:
        if user.email == "admin@gmail.com" and user.password == "admin":
            return {"success": True, "role": "admin"}

        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("SELECT password FROM users WHERE email=?", (user.email,))
        row = c.fetchone()
        if row and row[0] == user.password:
            return {"success": True, "role": "user"}
        return {"success": False, "message": "로그인 실패"}
    except Exception as e:
        print("Login Error:", e)
        return {"success": False, "message": "서버 에러 발생"}
    finally:
        conn.close()

# ---------------- User ----------------
@app.get("/me/{email}")
def get_user(email: str):
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("SELECT email, points, kickboard FROM users WHERE email = ?", (email,))
        row = c.fetchone()
        if row:
            return {
                "email": row[0],
                "points": row[1] or 0,
                "kickboard": row[2] or 0
            }
        return {"email": email, "points": 0, "kickboard": 0}
    except Exception as e:
        print("Get User Error:", e)
        return {"email": email, "points": 0, "kickboard": 0, "message": "서버 에러 발생"}
    finally:
        conn.close()

# ---------------- Points ----------------
@app.post("/points/add")
def add_points(data: PointAdd):
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("SELECT points FROM users WHERE email = ?", (data.email,))
        row = c.fetchone()
        if not row:
            return {"success": False, "message": "존재하지 않는 사용자입니다."}

        new_points = (row[0] or 0) + int(data.amount)
        c.execute("UPDATE users SET points = ? WHERE email = ?", (new_points, data.email))
        conn.commit()
        return {"success": True, "points": new_points}
    except Exception as e:
        print("Add Points Error:", e)
        return {"success": False, "message": "서버 에러 발생"}
    finally:
        conn.close()

# ---------------- Kickboard ----------------
@app.post("/kickboard/buy")
def buy_kickboard(data: KickboardAction):
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("SELECT points, kickboard FROM users WHERE email = ?", (data.email,))
        row = c.fetchone()
        if not row:
            return {"success": False, "message": "존재하지 않는 사용자입니다."}

        points = row[0] or 0
        kickboard = row[1] or 0
        cost = 1000

        if points < cost:
            return {"success": False, "message": "포인트가 부족합니다."}
        if kickboard == 1:
            return {"success": False, "message": "이미 킥보드를 구매했습니다."}

        new_points = points - cost
        c.execute("UPDATE users SET points = ?, kickboard = ? WHERE email = ?", (new_points, 1, data.email))
        conn.commit()
        return {"success": True, "points": new_points, "kickboard": 1, "message": "킥보드가 구매되었습니다."}
    except Exception as e:
        print("Buy Kickboard Error:", e)
        return {"success": False, "message": "서버 에러 발생"}
    finally:
        conn.close()

@app.post("/kickboard/return")
def return_kickboard(data: KickboardAction):
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("SELECT points, kickboard FROM users WHERE email = ?", (data.email,))
        row = c.fetchone()
        if not row:
            return {"success": False, "message": "존재하지 않는 사용자입니다."}

        points = row[0] or 0
        kickboard = row[1] or 0
        if kickboard == 0:
            return {"success": False, "message": "킥보드를 구매하지 않았습니다."}

        c.execute("UPDATE users SET kickboard = ? WHERE email = ?", (0, data.email))
        conn.commit()
        return {"success": True, "points": points, "kickboard": 0, "message": "킥보드가 반납되었습니다."}
    except Exception as e:
        print("Return Kickboard Error:", e)
        return {"success": False, "message": "서버 에러 발생"}
    finally:
        conn.close()

# ---------------- Admin ----------------
@app.get("/admin/users")
def admin_users():
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("SELECT email, points, kickboard FROM users")
        rows = c.fetchall()
        return [{"email": r[0], "points": r[1] or 0, "kickboard": r[2] or 0} for r in rows]
    except Exception as e:
        print("Admin Users Error:", e)
        return []
    finally:
        conn.close()

@app.post("/admin/adjust")
def admin_adjust(data: AdminAdjust):
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute(
            "UPDATE users SET points = ?, kickboard = ? WHERE email = ?",
            (data.points, data.kickboard, data.email)
        )
        conn.commit()
        return {"success": True}
    except Exception as e:
        print("Admin Adjust Error:", e)
        return {"success": False, "message": "서버 에러 발생"}
    finally:
        conn.close()

@app.post("/admin/delete")
def admin_delete(data: KickboardAction):
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("DELETE FROM users WHERE email = ?", (data.email,))
        conn.commit()
        return {"success": True}
    except Exception as e:
        print("Admin Delete Error:", e)
        return {"success": False, "message": "서버 에러 발생"}
    finally:
        conn.close()
