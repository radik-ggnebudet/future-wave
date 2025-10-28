"""
Database module для хранения данных регистраций
"""
import sqlite3
from datetime import datetime
from typing import Optional, Dict, List


class Database:
    def __init__(self, db_path: str = "registrations.db"):
        self.db_path = db_path
        self.init_db()

    def init_db(self):
        """Инициализация базы данных"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS registrations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER UNIQUE NOT NULL,
                full_name TEXT NOT NULL,
                birth_date TEXT NOT NULL,
                email TEXT NOT NULL,
                phone TEXT NOT NULL,
                university TEXT NOT NULL,
                course TEXT NOT NULL,
                consent_given BOOLEAN NOT NULL,
                consent_datetime TEXT NOT NULL,
                registration_datetime TEXT NOT NULL,
                telegram_username TEXT
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS admin_chats (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                chat_id INTEGER UNIQUE NOT NULL,
                added_datetime TEXT NOT NULL
            )
        """)

        conn.commit()
        conn.close()

    def save_registration(self, user_data: Dict) -> bool:
        """Сохранение регистрации пользователя"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute("""
                INSERT OR REPLACE INTO registrations 
                (user_id, full_name, birth_date, email, phone, university, course, 
                 consent_given, consent_datetime, registration_datetime, telegram_username)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                user_data['user_id'],
                user_data['full_name'],
                user_data['birth_date'],
                user_data['email'],
                user_data['phone'],
                user_data['university'],
                user_data['course'],
                user_data['consent_given'],
                user_data['consent_datetime'],
                user_data['registration_datetime'],
                user_data.get('telegram_username', '')
            ))

            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Error saving registration: {e}")
            return False

    def get_registration(self, user_id: int) -> Optional[Dict]:
        """Получение регистрации пользователя"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM registrations WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()

        conn.close()

        if row:
            return {
                'id': row[0],
                'user_id': row[1],
                'full_name': row[2],
                'birth_date': row[3],
                'email': row[4],
                'phone': row[5],
                'university': row[6],
                'course': row[7],
                'consent_given': row[8],
                'consent_datetime': row[9],
                'registration_datetime': row[10],
                'telegram_username': row[11]
            }
        return None

    def get_all_registrations(self) -> List[Dict]:
        """Получение всех регистраций"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM registrations ORDER BY registration_datetime DESC")
        rows = cursor.fetchall()

        conn.close()

        registrations = []
        for row in rows:
            registrations.append({
                'id': row[0],
                'user_id': row[1],
                'full_name': row[2],
                'birth_date': row[3],
                'email': row[4],
                'phone': row[5],
                'university': row[6],
                'course': row[7],
                'consent_given': row[8],
                'consent_datetime': row[9],
                'registration_datetime': row[10],
                'telegram_username': row[11]
            })

        return registrations

    def get_statistics(self) -> Dict:
        """Получение статистики регистраций"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM registrations")
        total = cursor.fetchone()[0]

        cursor.execute("SELECT university, COUNT(*) FROM registrations GROUP BY university")
        universities = cursor.fetchall()

        cursor.execute("SELECT course, COUNT(*) FROM registrations GROUP BY course")
        courses = cursor.fetchall()

        conn.close()

        return {
            'total': total,
            'by_university': dict(universities),
            'by_course': dict(courses)
        }

    def save_admin_chat(self, user_id: int, username: str, chat_id: int) -> bool:
        """Сохранение chat_id администратора"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute("""
                INSERT OR REPLACE INTO admin_chats 
                (user_id, username, chat_id, added_datetime)
                VALUES (?, ?, ?, ?)
            """, (user_id, username, chat_id, datetime.now().isoformat()))

            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Error saving admin chat: {e}")
            return False

    def get_admin_chats(self) -> List[int]:
        """Получение всех chat_id администраторов"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("SELECT chat_id FROM admin_chats")
        rows = cursor.fetchall()

        conn.close()

        return [row[0] for row in rows]

    def is_admin_registered(self, user_id: int) -> bool:
        """Проверка зарегистрирован ли админ"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM admin_chats WHERE user_id = ?", (user_id,))
        count = cursor.fetchone()[0]

        conn.close()

        return count > 0


