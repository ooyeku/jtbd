"""JTBD Dashboard application."""

from datetime import datetime, timedelta
from typing import Dict, List, Any
import sqlite3
from collections import defaultdict

from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical, Grid
from textual.widgets import Header, Footer, Static, ProgressBar, DataTable, Label, RichLog, Sparkline
from textual.reactive import reactive
from textual.binding import Binding
from rich.text import Text
from rich.table import Table
from rich.progress_bar import ProgressBar as RichProgressBar

from jtbd import get_config
from todo.db import TodoDB
from buildit.db import BuildDB

class ProgressStatCard(Static):
    """A card displaying a statistic with a progress bar."""
    
    DEFAULT_CSS = """
    ProgressStatCard {
        width: 100%;
        min-height: 7;
        border: tall $primary;
        padding: 1;
        margin: 0 1;
        background: $boost;
    }
    
    ProgressStatCard > Label {
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
    
    .progress-label {
        color: $text-muted;
        text-align: right;
    }
    """
    
    def __init__(self, title: str, value: str, progress: float = 0):
        super().__init__()
        self.title = title
        self._value_label = None
        self._progress_label = None
        self.value = value
        self.progress = min(max(progress, 0), 100)
        self._progress_bar = None
    
    def compose(self) -> ComposeResult:
        yield Label(self.title, classes="stat-title")
        self._value_label = Label(self.value, classes="stat-value")
        yield self._value_label
        self._progress_bar = ProgressBar()
        self._progress_bar.update(progress=int(self.progress))
        yield self._progress_bar
        self._progress_label = Label(f"{self.progress:.1f}%", classes="progress-label")
        yield self._progress_label
    
    def update_value(self, new_value: str, new_progress: float = None):
        """Update the displayed value and progress."""
        self.value = new_value
        if self._value_label:
            self._value_label.update(new_value)
        
        if new_progress is not None:
            self.progress = min(max(new_progress, 0), 100)
            if self._progress_label:
                self._progress_label.update(f"{self.progress:.1f}%")
                if self._progress_bar:
                    self._progress_bar.update(progress=int(self.progress))

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
    
    TodoStats Sparkline {
        height: 5;
        margin: 1;
    }
    """
    
    def __init__(self):
        super().__init__()
        self.db = TodoDB()
        self._cards = {}
        self._log = None
        self._sparkline = None
    
    def compose(self) -> ComposeResult:
        yield Label("Todo Overview", id="todo-title")
        with Grid():
            self._cards["total"] = ProgressStatCard("Total Tasks", "0", 0)
            self._cards["completed"] = ProgressStatCard("Completed", "0", 0)
            self._cards["due"] = ProgressStatCard("Due Today", "0", 0)
            self._cards["priority"] = ProgressStatCard("High Priority", "0", 0)
            yield self._cards["total"]
            yield self._cards["completed"]
            yield self._cards["due"]
            yield self._cards["priority"]
        
        self._sparkline = Sparkline(data=[0] * 7, summary_function=max)
        yield Label("7-Day Activity")
        yield self._sparkline
        
        self._log = RichLog()
        yield self._log
        self.refresh_data()
    
    def refresh_data(self):
        """Refresh all statistics and upcoming tasks."""
        total = self._get_total_tasks()
        completed = self._get_completed_tasks()
        due_today = self._get_due_today()
        high_priority = self._get_high_priority()
        
        completion_rate = (completed / total * 100) if total > 0 else 0
        due_rate = (due_today / total * 100) if total > 0 else 0
        priority_rate = (high_priority / total * 100) if total > 0 else 0
        
        self._cards["total"].update_value(str(total), completion_rate)
        self._cards["completed"].update_value(str(completed), completion_rate)
        self._cards["due"].update_value(str(due_today), due_rate)
        self._cards["priority"].update_value(str(high_priority), priority_rate)
        
        # Update activity sparkline
        activity_data = self._get_daily_activity()
        self._sparkline.data = activity_data
        
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
                    due_date = datetime.strptime(task["due_date"], "%Y-%m-%d").strftime("%Y-%m-%d")
                    days_left = (datetime.strptime(due_date, "%Y-%m-%d").date() - datetime.now().date()).days
                    due_text = f"[red]({days_left}d left)[/red]" if days_left <= 2 else f"({days_left}d left)"
                    self._log.write(
                        f"{priority_marker} {task['status']} {due_date} {due_text}: {task['title']}"
                    )
    
    def _get_total_tasks(self) -> int:
        with sqlite3.connect(self.db.db_path) as conn:
            cursor = conn.execute("SELECT COUNT(*) FROM todos")
            return cursor.fetchone()[0]
    
    def _get_completed_tasks(self) -> int:
        with sqlite3.connect(self.db.db_path) as conn:
            cursor = conn.execute("SELECT COUNT(*) FROM todos WHERE completed = 1")
            return cursor.fetchone()[0]
    
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
    
    def _get_daily_activity(self) -> List[int]:
        """Get task activity for the last 7 days."""
        today = datetime.now().date()
        dates = [(today - timedelta(days=i)).isoformat() for i in range(6, -1, -1)]
        
        with sqlite3.connect(self.db.db_path) as conn:
            cursor = conn.execute("""
                SELECT date(created_at) as date, COUNT(*) as count
                FROM todos
                WHERE date(created_at) >= date('now', '-7 days')
                GROUP BY date(created_at)
            """)
            activity = dict(cursor.fetchall())
        
        return [activity.get(date, 0) for date in dates]

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
    
    BuildStats Sparkline {
        height: 5;
        margin: 1;
    }
    """
    
    def __init__(self):
        super().__init__()
        self.db = BuildDB()
        self._cards = {}
        self._log = None
        self._sparkline = None
    
    def compose(self) -> ComposeResult:
        yield Label("Project Overview", id="build-title")
        with Grid():
            self._cards["total"] = ProgressStatCard("Total Projects", "0", 0)
            self._cards["active"] = ProgressStatCard("Active Projects", "0", 0)
            self._cards["open"] = ProgressStatCard("Open Issues", "0", 0)
            self._cards["critical"] = ProgressStatCard("Critical Issues", "0", 0)
            yield self._cards["total"]
            yield self._cards["active"]
            yield self._cards["open"]
            yield self._cards["critical"]
        
        self._sparkline = Sparkline(data=[0] * 7, summary_function=max)
        yield Label("7-Day Issue Activity")
        yield self._sparkline
        
        self._log = RichLog()
        yield self._log
        self.refresh_data()
    
    def refresh_data(self):
        """Refresh all statistics and project status."""
        try:
            total_projects = self._get_total_projects()
            active_projects = self._get_active_projects()
            open_issues = self._get_open_issues()
            critical_issues = self._get_critical_issues()
            
            active_rate = (active_projects / total_projects * 100) if total_projects > 0 else 0
            critical_rate = (critical_issues / open_issues * 100) if open_issues > 0 else 0
            
            self._cards["total"].update_value(str(total_projects), active_rate)
            self._cards["active"].update_value(str(active_projects), active_rate)
            self._cards["open"].update_value(str(open_issues), 100 - critical_rate)
            self._cards["critical"].update_value(str(critical_issues), critical_rate)
            
            # Update issue activity sparkline
            activity_data = self._get_daily_activity()
            self._sparkline.data = activity_data
            
            # Update project status
            self._log.clear()
            self._log.write("[b]Active Projects:[/b]")
            
            with sqlite3.connect(self.db.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute("""
                    SELECT p.name, p.version,
                           COUNT(CASE WHEN i.status NOT IN ('closed', 'done', 'completed') THEN 1 END) as open_issues,
                           COUNT(CASE WHEN i.priority >= 2 AND i.status NOT IN ('closed', 'done', 'completed') THEN 1 END) as critical,
                           MAX(i.created_date) as last_activity
                    FROM projects p
                    LEFT JOIN issues i ON i.project_id = p.id
                    WHERE LOWER(p.status) = 'active'
                    GROUP BY p.id
                    ORDER BY last_activity DESC
                    LIMIT 5
                """)
                projects = cursor.fetchall()
                
                if not projects:
                    self._log.write("No active projects")
                else:
                    for proj in projects:
                        critical_marker = "🔥" if proj["critical"] > 0 else "  "
                        last_activity = datetime.strptime(proj["last_activity"], "%Y-%m-%d").strftime("%Y-%m-%d") if proj["last_activity"] else "No activity"
                        self._log.write(
                            f"{critical_marker} {proj['name']} v{proj['version']} "
                            f"({proj['open_issues']} open, {proj['critical']} critical) "
                            f"[dim]Last: {last_activity}[/dim]"
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
    
    def _get_daily_activity(self) -> List[int]:
        """Get issue activity for the last 7 days."""
        today = datetime.now().date()
        dates = [(today - timedelta(days=i)).isoformat() for i in range(6, -1, -1)]
        
        with sqlite3.connect(self.db.db_path) as conn:
            cursor = conn.execute("""
                SELECT date(created_date) as date, COUNT(*) as count
                FROM issues
                WHERE date(created_date) >= date('now', '-7 days')
                GROUP BY date(created_date)
            """)
            activity = dict(cursor.fetchall())
        
        return [activity.get(date, 0) for date in dates]

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
        border: tall $primary;
        background: $boost;
    }
    """
    
    def __init__(self):
        super().__init__()
        self.todo_db = TodoDB()
        self.build_db = BuildDB()
        self._table = None
    
    def compose(self) -> ComposeResult:
        yield Label("Recent Activity")
        self._table = DataTable(zebra_stripes=True, show_header=True)
        self._table.add_columns(
            "Time", 
            "Type", 
            "Description", 
            "Status"
        )
        self._table.styles.width = "100%"
        yield self._table
        self.refresh_data()
    
    def refresh_data(self):
        """Refresh the activity table."""
        if not self._table:
            return
        
        self._table.clear()
        
        # Get recent todos
        try:
            with sqlite3.connect(self.todo_db.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute("""
                    SELECT 
                        datetime(created_at) as time,
                        'Todo' as type,
                        title as description,
                        CASE WHEN completed = 1 THEN '✓ Done' ELSE '○ Pending' END as status
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
                        datetime(created_date) as time,
                        'Issue' as type,
                        title as description,
                        CASE 
                            WHEN LOWER(status) IN ('closed', 'done', 'completed') THEN '✓ ' || status
                            ELSE '○ ' || status
                        END as status
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
            
            if not activities:
                self._table.add_row(
                    "No activity",
                    "-",
                    "No recent items found",
                    "-"
                )
            else:
                for activity in activities:
                    time_str = datetime.strptime(activity['time'], "%Y-%m-%d %H:%M:%S").strftime("%Y-%m-%d %H:%M")
                    type_str = "[blue]Todo[/blue]" if activity['type'] == 'Todo' else "[green]Issue[/green]"
                    status_str = "[green]" + activity['status'] + "[/green]" if "✓" in activity['status'] else activity['status']
                    
                    self._table.add_row(
                        time_str,
                        type_str,
                        Text.from_markup(activity['description']),
                        Text.from_markup(status_str)
                    )
        except Exception as e:
            self._table.add_row(
                "Error",
                "-",
                f"Failed to load activities: {str(e)}",
                "-"
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