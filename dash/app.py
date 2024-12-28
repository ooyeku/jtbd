"""JTBD Dashboard application."""

from datetime import datetime, timedelta
from typing import Dict, List, Any
import sqlite3

from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical, Grid
from textual.widgets import Header, Footer, Static, ProgressBar, DataTable, Label, RichLog
from textual.reactive import reactive
from textual.binding import Binding
from rich.text import Text
from rich.table import Table

from jtbd import get_config
from todo.db import TodoDB
from buildit.db import BuildDB

class StatCard(Static):
    """A card displaying a statistic with title and value."""
    
    DEFAULT_CSS = """
    StatCard {
        width: 100%;
        min-height: 5;
        border: tall $primary;
        padding: 1;
        margin: 0 1;
        background: $boost;
    }
    
    StatCard > Label {
        text-align: center;
        width: 100%;
    }
    
    .stat-title {
        color: $text;
        text-style: bold;
    }
    
    .stat-value {
        color: $accent;
        text-style: bold;
        content-align: center middle;
    }
    """
    
    def __init__(self, title: str, value: str):
        super().__init__()
        self.title = title
        self._value_label = None
        self.value = value
    
    def compose(self) -> ComposeResult:
        yield Label(self.title, classes="stat-title")
        self._value_label = Label(self.value, classes="stat-value")
        yield self._value_label
    
    def update_value(self, new_value: str):
        """Update the displayed value."""
        self.value = new_value
        if self._value_label:
            self._value_label.update(new_value)

class TodoStats(Container):
    """Container for Todo statistics and upcoming tasks."""
    
    DEFAULT_CSS = """
    TodoStats {
        layout: vertical;
        min-height: 20;
        border: heavy $primary-darken-2;
        background: $surface;
        padding: 1;
    }
    
    TodoStats > Label {
        text-align: center;
        padding: 1;
        text-style: bold;
        color: $secondary;
        margin: 0 0 1 0;
    }
    
    TodoStats > Grid {
        layout: grid;
        grid-size: 2;
        grid-columns: 1fr 1fr;
        grid-rows: 1fr 1fr;
        height: auto;
        margin: 0 0 1 0;
    }
    
    TodoStats RichLog {
        min-height: 10;
        border: tall $primary;
        background: $boost;
        margin: 0 1;
        padding: 1;
    }
    """
    
    def __init__(self):
        super().__init__()
        self.db = TodoDB()
        self._cards = {}
        self._log = None
    
    def compose(self) -> ComposeResult:
        yield Label("Todo Overview", id="todo-title")
        with Grid():
            self._cards["total"] = StatCard("Total Tasks", "0")
            self._cards["completed"] = StatCard("Completed", "0%")
            self._cards["due"] = StatCard("Due Today", "0")
            self._cards["priority"] = StatCard("High Priority", "0")
            yield self._cards["total"]
            yield self._cards["completed"]
            yield self._cards["due"]
            yield self._cards["priority"]
        
        self._log = RichLog()
        yield self._log
        self.refresh_data()
    
    def refresh_data(self):
        """Refresh all statistics and upcoming tasks."""
        self._cards["total"].update_value(str(self._get_total_tasks()))
        self._cards["completed"].update_value(f"{self._get_completion_rate():.1f}%")
        self._cards["due"].update_value(str(self._get_due_today()))
        self._cards["priority"].update_value(str(self._get_high_priority()))
        
        # Update upcoming tasks
        self._log.clear()
        self._log.write("[b]Upcoming Tasks:[/b]")
        
        with sqlite3.connect(self.db.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("""
                SELECT title, due_date, priority,
                       CASE WHEN completed = 1 THEN '✓' ELSE '○' END as status
                FROM todos
                WHERE due_date IS NOT NULL 
                  AND date(due_date) >= date('now')
                  AND completed = 0
                ORDER BY due_date ASC
                LIMIT 5
            """)
            tasks = cursor.fetchall()
            
            if not tasks:
                self._log.write("No upcoming tasks")
            else:
                for task in tasks:
                    priority_marker = "🔥" if task["priority"] >= 2 else "  "
                    self._log.write(
                        f"{priority_marker} {task['status']} {task['due_date']}: {task['title']}"
                    )
    
    def _get_total_tasks(self) -> int:
        with sqlite3.connect(self.db.db_path) as conn:
            cursor = conn.execute("SELECT COUNT(*) FROM todos")
            return cursor.fetchone()[0]
    
    def _get_completion_rate(self) -> float:
        with sqlite3.connect(self.db.db_path) as conn:
            cursor = conn.execute("""
                SELECT 
                    CAST(SUM(CASE WHEN completed = 1 THEN 1 ELSE 0 END) AS FLOAT) / 
                    CASE WHEN COUNT(*) = 0 THEN 1 ELSE COUNT(*) END * 100
                FROM todos
            """)
            rate = cursor.fetchone()[0]
            return rate if rate is not None else 0.0
    
    def _get_due_today(self) -> int:
        today = datetime.now().date().isoformat()
        with sqlite3.connect(self.db.db_path) as conn:
            cursor = conn.execute(
                "SELECT COUNT(*) FROM todos WHERE date(due_date) = date(?)",
                (today,)
            )
            return cursor.fetchone()[0]
    
    def _get_high_priority(self) -> int:
        with sqlite3.connect(self.db.db_path) as conn:
            cursor = conn.execute(
                "SELECT COUNT(*) FROM todos WHERE priority >= 2"
            )
            return cursor.fetchone()[0]

class BuildStats(Container):
    """Container for BuildIt statistics and project status."""
    
    DEFAULT_CSS = """
    BuildStats {
        layout: vertical;
        min-height: 20;
        border: heavy $primary-darken-2;
        background: $surface;
        padding: 1;
    }
    
    BuildStats > Label {
        text-align: center;
        padding: 1;
        text-style: bold;
        color: $secondary;
        margin: 0 0 1 0;
    }
    
    BuildStats > Grid {
        layout: grid;
        grid-size: 2;
        grid-columns: 1fr 1fr;
        grid-rows: 1fr 1fr;
        height: auto;
        margin: 0 0 1 0;
    }
    
    BuildStats RichLog {
        min-height: 10;
        border: tall $primary;
        background: $boost;
        margin: 0 1;
        padding: 1;
    }
    """
    
    def __init__(self):
        super().__init__()
        self.db = BuildDB()
        self._cards = {}
        self._log = None
    
    def compose(self) -> ComposeResult:
        yield Label("Project Overview", id="build-title")
        with Grid():
            self._cards["total"] = StatCard("Total Projects", "0")
            self._cards["active"] = StatCard("Active Projects", "0")
            self._cards["open"] = StatCard("Open Issues", "0")
            self._cards["critical"] = StatCard("Critical Issues", "0")
            yield self._cards["total"]
            yield self._cards["active"]
            yield self._cards["open"]
            yield self._cards["critical"]
        
        self._log = RichLog()
        yield self._log
        self.refresh_data()
    
    def refresh_data(self):
        """Refresh all statistics and project status."""
        try:
            self._cards["total"].update_value(str(self._get_total_projects()))
            self._cards["active"].update_value(str(self._get_active_projects()))
            self._cards["open"].update_value(str(self._get_open_issues()))
            self._cards["critical"].update_value(str(self._get_critical_issues()))
            
            # Update project status
            self._log.clear()
            self._log.write("[b]Active Projects:[/b]")
            
            with sqlite3.connect(self.db.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute("""
                    SELECT p.name, p.version,
                           COUNT(CASE WHEN i.status NOT IN ('closed', 'done', 'completed') THEN 1 END) as open_issues,
                           COUNT(CASE WHEN i.priority >= 2 AND i.status NOT IN ('closed', 'done', 'completed') THEN 1 END) as critical
                    FROM projects p
                    LEFT JOIN issues i ON i.project_id = p.id
                    WHERE LOWER(p.status) = 'active'
                    GROUP BY p.id
                    ORDER BY critical DESC, open_issues DESC
                    LIMIT 5
                """)
                projects = cursor.fetchall()
                
                if not projects:
                    self._log.write("No active projects")
                else:
                    for proj in projects:
                        critical_marker = "🔥" if proj["critical"] > 0 else "  "
                        self._log.write(
                            f"{critical_marker} {proj['name']} v{proj['version']} "
                            f"({proj['open_issues']} open)"
                        )
        
        except Exception as e:
            print(f"Error refreshing BuildStats: {e}")
    
    def _get_total_projects(self) -> int:
        with sqlite3.connect(self.db.db_path) as conn:
            cursor = conn.execute("SELECT COUNT(*) FROM projects")
            return cursor.fetchone()[0]
    
    def _get_active_projects(self) -> int:
        with sqlite3.connect(self.db.db_path) as conn:
            cursor = conn.execute(
                "SELECT COUNT(*) FROM projects WHERE LOWER(status) = 'active'"
            )
            return cursor.fetchone()[0]
    
    def _get_open_issues(self) -> int:
        with sqlite3.connect(self.db.db_path) as conn:
            cursor = conn.execute(
                "SELECT COUNT(*) FROM issues WHERE LOWER(status) NOT IN ('closed', 'done', 'completed')"
            )
            return cursor.fetchone()[0]
    
    def _get_critical_issues(self) -> int:
        with sqlite3.connect(self.db.db_path) as conn:
            cursor = conn.execute(
                "SELECT COUNT(*) FROM issues WHERE priority >= 2 AND LOWER(status) NOT IN ('closed', 'done', 'completed')"
            )
            return cursor.fetchone()[0]

class RecentActivity(Container):
    """Container showing recent activity across both apps."""
    
    DEFAULT_CSS = """
    RecentActivity {
        height: 1fr;
        min-height: 15;
        border: heavy $primary-darken-2;
        background: $surface;
        padding: 1;
    }
    
    RecentActivity > Label {
        text-align: center;
        padding: 1;
        text-style: bold;
        color: $secondary;
        margin: 0 0 1 0;
    }
    
    DataTable {
        height: 1fr;
        min-height: 10;
        margin: 0 1;
    }
    """
    
    def __init__(self):
        super().__init__()
        self.todo_db = TodoDB()
        self.build_db = BuildDB()
        self._table = None
    
    def compose(self) -> ComposeResult:
        yield Label("Recent Activity")
        self._table = DataTable()
        self._table.add_columns("Time", "Type", "Description", "Status")
        yield self._table
        self.refresh_data()
    
    def refresh_data(self):
        """Refresh the activity table."""
        if not self._table:
            return
        
        self._table.clear()
        
        # Get recent todos
        with sqlite3.connect(self.todo_db.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("""
                SELECT 
                    created_at as time,
                    'Todo' as type,
                    title as description,
                    CASE WHEN completed = 1 THEN 'Completed' ELSE 'Pending' END as status
                FROM todos
                ORDER BY created_at DESC
                LIMIT 5
            """)
            todos = cursor.fetchall()
        
        # Get recent issues
        with sqlite3.connect(self.build_db.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("""
                SELECT 
                    created_date as time,
                    'Issue' as type,
                    title as description,
                    status
                FROM issues
                ORDER BY created_date DESC
                LIMIT 5
            """)
            issues = cursor.fetchall()
        
        # Combine and sort
        activities = sorted(
            [dict(t) for t in todos] + [dict(i) for i in issues],
            key=lambda x: x['time'],
            reverse=True
        )[:5]
        
        for activity in activities:
            self._table.add_row(
                activity['time'],
                activity['type'],
                activity['description'],
                activity['status']
            )

class DashboardApp(App):
    """JTBD Dashboard application."""
    
    CSS = """
    Screen {
        layout: grid;
        grid-size: 2 2;
        grid-columns: 1fr 1fr;
        grid-rows: auto 1fr;
        padding: 1;
    }
    
    TodoStats {
        row-span: 1;
        height: auto;
        min-height: 20;
        margin: 0 1 1 0;
    }
    
    BuildStats {
        row-span: 1;
        height: auto;
        min-height: 20;
        margin: 0 0 1 1;
    }
    
    RecentActivity {
        column-span: 2;
        height: 1fr;
        min-height: 15;
        margin: 0 0 0 0;
    }
    
    Header {
        background: $boost;
        color: $text;
        text-style: bold;
        content-align: center middle;
        margin: 0 0 1 0;
    }
    
    Footer {
        background: $boost;
        color: $text;
        margin: 1 0 0 0;
    }
    """
    
    BINDINGS = [
        Binding("q", "quit", "Quit", show=True),
        Binding("r", "refresh", "Refresh", show=True),
    ]
    
    def compose(self) -> ComposeResult:
        yield Header()
        yield TodoStats()
        yield BuildStats()
        yield RecentActivity()
        yield Footer()
    
    def action_refresh(self):
        """Refresh all statistics."""
        self.query_one(TodoStats).refresh_data()
        self.query_one(BuildStats).refresh_data()
        self.query_one(RecentActivity).refresh_data() 