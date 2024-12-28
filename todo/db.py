import sqlite3
from datetime import datetime
from typing import List, Optional, Tuple, Dict, Any

class TodoDB:
    def __init__(self, db_path: str = "todo.db"):
        self.db_path = db_path
        self.init_db()

    def init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS todos (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    description TEXT,
                    due_date TEXT,
                    priority INTEGER DEFAULT 0,
                    completed INTEGER DEFAULT 0,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.commit()

    def add_todo(self, title: str, description: str = "", due_date: Optional[str] = None, priority: int = 0) -> int:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "INSERT INTO todos (title, description, due_date, priority) VALUES (?, ?, ?, ?)",
                (title, description, due_date, priority)
            )
            conn.commit()
            return cursor.lastrowid

    def get_todos(self) -> List[Tuple]:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT id, title, description, due_date, priority, completed, created_at FROM todos ORDER BY priority DESC, created_at DESC"
            )
            return cursor.fetchall()

    def toggle_todo(self, todo_id: int):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "UPDATE todos SET completed = ((completed | 1) - (completed & 1)) WHERE id = ?",
                (todo_id,)
            )
            conn.commit()

    def delete_todo(self, todo_id: int):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM todos WHERE id = ?", (todo_id,))
            conn.commit()

    def update_todo(self, todo_id: int, title: str, description: str, due_date: Optional[str], priority: int):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "UPDATE todos SET title = ?, description = ?, due_date = ?, priority = ? WHERE id = ?",
                (title, description, due_date, priority, todo_id)
            )
            conn.commit()

    def export_todos(self) -> List[Dict[str, Any]]:
        """Export todos in a JSON-friendly format."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row  # This enables column access by name
            cursor = conn.execute(
                "SELECT id, title, description, due_date, priority, completed, created_at FROM todos"
            )
            todos = []
            for row in cursor:
                todos.append({
                    "id": row["id"],
                    "title": row["title"],
                    "description": row["description"],
                    "due_date": row["due_date"],
                    "priority": row["priority"],
                    "completed": bool(row["completed"]),
                    "created_at": row["created_at"]
                })
            return todos

    def import_todos(self, todos_data: List[Dict[str, Any]]) -> None:
        """Import todos from a JSON-friendly format."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            for todo in todos_data:
                cursor.execute(
                    """
                    INSERT INTO todos (title, description, due_date, priority, completed, created_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        todo["title"],
                        todo["description"],
                        todo.get("due_date"),
                        todo["priority"],
                        1 if todo.get("completed", False) else 0,
                        todo.get("created_at", datetime.now().isoformat())
                    )
                )
            conn.commit()

    def search_todos(self, query: str) -> List[Dict[str, Any]]:
        """
        Search todos by title and description.
        
        Args:
            query: Search term to match against title and description
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            
            sql = """
                SELECT id, title, description, due_date, priority, completed, created_at
                FROM todos
                WHERE title LIKE ? OR description LIKE ?
                ORDER BY priority DESC, created_at DESC
            """
            
            cursor = conn.execute(sql, [f"%{query}%", f"%{query}%"] if query else ["%%", "%%"])
            return [dict(row) for row in cursor] 