import sqlite3
from datetime import datetime, timedelta
from typing import List, Optional, Tuple

class Database:
    def __init__(self, db_name: str = "reminder_bot.db"):
        self.db_name = db_name
        self.init_db()

    def init_db(self):
        """Создание таблиц в базе данных"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                description TEXT,
                event_date TEXT NOT NULL,
                event_type TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS reminders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_id INTEGER NOT NULL,
                remind_date TEXT NOT NULL,
                sent INTEGER DEFAULT 0,
                FOREIGN KEY (event_id) REFERENCES events (id) ON DELETE CASCADE
            )
        ''')

        conn.commit()
        conn.close()

    def add_event(self, user_id: int, title: str, event_date: str,
                  event_type: str, description: str = "") -> int:
        """Добавить событие и создать напоминания"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()

        created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        cursor.execute('''
            INSERT INTO events (user_id, title, description, event_date, event_type, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (user_id, title, description, event_date, event_type, created_at))

        event_id = cursor.lastrowid

        # Создаем напоминания за неделю, 3 дня и 1 день
        event_datetime = datetime.strptime(event_date, "%Y-%m-%d")

        reminder_dates = [
            event_datetime - timedelta(days=7),
            event_datetime - timedelta(days=3),
            event_datetime - timedelta(days=1)
        ]

        for remind_date in reminder_dates:
            if remind_date > datetime.now():
                cursor.execute('''
                    INSERT INTO reminders (event_id, remind_date)
                    VALUES (?, ?)
                ''', (event_id, remind_date.strftime("%Y-%m-%d %H:%M:%S")))

        conn.commit()
        conn.close()

        return event_id

    def get_user_events(self, user_id: int, event_type: Optional[str] = None) -> List[Tuple]:
        """Получить все события пользователя"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()

        if event_type:
            cursor.execute('''
                SELECT id, title, description, event_date, event_type
                FROM events
                WHERE user_id = ? AND event_type = ?
                ORDER BY event_date ASC
            ''', (user_id, event_type))
        else:
            cursor.execute('''
                SELECT id, title, description, event_date, event_type
                FROM events
                WHERE user_id = ?
                ORDER BY event_date ASC
            ''', (user_id,))

        events = cursor.fetchall()
        conn.close()

        return events

    def delete_event(self, event_id: int, user_id: int) -> bool:
        """Удалить событие"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()

        cursor.execute('''
            DELETE FROM events
            WHERE id = ? AND user_id = ?
        ''', (event_id, user_id))

        deleted = cursor.rowcount > 0
        conn.commit()
        conn.close()

        return deleted

    def get_pending_reminders(self) -> List[Tuple]:
        """Получить все несотправленные напоминания, которые пора отправить"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()

        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        cursor.execute('''
            SELECT r.id, r.event_id, e.user_id, e.title, e.description,
                   e.event_date, e.event_type, r.remind_date
            FROM reminders r
            JOIN events e ON r.event_id = e.id
            WHERE r.sent = 0 AND r.remind_date <= ?
            ORDER BY r.remind_date ASC
        ''', (now,))

        reminders = cursor.fetchall()
        conn.close()

        return reminders

    def mark_reminder_sent(self, reminder_id: int):
        """Отметить напоминание как отправленное"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()

        cursor.execute('''
            UPDATE reminders
            SET sent = 1
            WHERE id = ?
        ''', (reminder_id,))

        conn.commit()
        conn.close()
