import sqlite3
from datetime import datetime
from typing import List, Dict, Any, Optional
import json
import os

class BuildDB:
    """Database manager for the BuildIt application."""
    
    def __init__(self, db_path: str = None):
        """Initialize the database connection."""
        if db_path is None:
            db_path = os.path.join(os.path.expanduser("~"), ".buildit.db")
        self.db_path = db_path
        self._init_db()
    
    def _init_db(self):
        """Initialize the database schema."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Create projects table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS projects (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    description TEXT,
                    version TEXT,
                    status TEXT NOT NULL,
                    created_date TEXT NOT NULL,
                    last_updated TEXT NOT NULL
                )
            """)
            
            # Create issues table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS issues (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project_id INTEGER,
                    type TEXT NOT NULL,
                    title TEXT NOT NULL,
                    description TEXT,
                    priority INTEGER NOT NULL,
                    status TEXT NOT NULL,
                    assigned_to TEXT,
                    created_date TEXT NOT NULL,
                    due_date TEXT,
                    tags TEXT,
                    FOREIGN KEY (project_id) REFERENCES projects (id)
                )
            """)
            
            # Create comments table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS comments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    issue_id INTEGER NOT NULL,
                    content TEXT NOT NULL,
                    author TEXT NOT NULL,
                    created_date TEXT NOT NULL,
                    FOREIGN KEY (issue_id) REFERENCES issues (id)
                )
            """)
            
            # Create tags table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS tags (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE,
                    color TEXT NOT NULL
                )
            """)
            
            conn.commit()
    
    # Project operations
    def add_project(self, name: str, description: str = "", version: str = "0.1.0",
                   status: str = "Active") -> int:
        """Add a new project."""
        now = datetime.now().isoformat()
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO projects (name, description, version, status, created_date, last_updated)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (name, description, version, status, now, now))
            return cursor.lastrowid
    
    def get_projects(self) -> List[Dict[str, Any]]:
        """Get all projects."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM projects ORDER BY last_updated DESC")
            return [dict(row) for row in cursor.fetchall()]
    
    def update_project(self, project_id: int, name: str = None, description: str = None,
                      version: str = None, status: str = None) -> bool:
        """Update a project."""
        updates = []
        values = []
        if name is not None:
            updates.append("name = ?")
            values.append(name)
        if description is not None:
            updates.append("description = ?")
            values.append(description)
        if version is not None:
            updates.append("version = ?")
            values.append(version)
        if status is not None:
            updates.append("status = ?")
            values.append(status)
        
        if not updates:
            return False
        
        updates.append("last_updated = ?")
        values.append(datetime.now().isoformat())
        values.append(project_id)
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(f"""
                UPDATE projects
                SET {", ".join(updates)}
                WHERE id = ?
            """, values)
            return cursor.rowcount > 0
    
    def delete_project(self, project_id: int) -> bool:
        """Delete a project and all its issues."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            # Delete associated comments first
            cursor.execute("""
                DELETE FROM comments
                WHERE issue_id IN (SELECT id FROM issues WHERE project_id = ?)
            """, (project_id,))
            # Delete associated issues
            cursor.execute("DELETE FROM issues WHERE project_id = ?", (project_id,))
            # Delete the project
            cursor.execute("DELETE FROM projects WHERE id = ?", (project_id,))
            return cursor.rowcount > 0
    
    # Issue operations
    def add_issue(self, project_id: int, type: str, title: str, description: str = "",
                 priority: int = 0, status: str = "Open", assigned_to: str = "",
                 due_date: str = None, tags: List[str] = None) -> int:
        """Add a new issue."""
        now = datetime.now().isoformat()
        tags_str = json.dumps(tags) if tags else "[]"
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO issues (
                    project_id, type, title, description, priority, status,
                    assigned_to, created_date, due_date, tags
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (project_id, type, title, description, priority, status,
                 assigned_to, now, due_date, tags_str))
            return cursor.lastrowid
    
    def get_issues(self, project_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get all issues, optionally filtered by project."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            if project_id is not None:
                cursor.execute("""
                    SELECT * FROM issues
                    WHERE project_id = ?
                    ORDER BY priority DESC, created_date DESC
                """, (project_id,))
            else:
                cursor.execute("""
                    SELECT * FROM issues
                    ORDER BY priority DESC, created_date DESC
                """)
            return [dict(row) for row in cursor.fetchall()]
    
    def update_issue(self, issue_id: int, **kwargs) -> bool:
        """Update an issue."""
        valid_fields = {
            'type', 'title', 'description', 'priority', 'status',
            'assigned_to', 'due_date', 'tags'
        }
        
        updates = []
        values = []
        for field, value in kwargs.items():
            if field in valid_fields:
                updates.append(f"{field} = ?")
                values.append(value if field != 'tags' else json.dumps(value))
        
        if not updates:
            return False
        
        values.append(issue_id)
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(f"""
                UPDATE issues
                SET {", ".join(updates)}
                WHERE id = ?
            """, values)
            return cursor.rowcount > 0
    
    def delete_issue(self, issue_id: int) -> bool:
        """Delete an issue and its comments."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            # Delete associated comments first
            cursor.execute("DELETE FROM comments WHERE issue_id = ?", (issue_id,))
            # Delete the issue
            cursor.execute("DELETE FROM issues WHERE id = ?", (issue_id,))
            return cursor.rowcount > 0
    
    # Comment operations
    def add_comment(self, issue_id: int, content: str, author: str) -> int:
        """Add a new comment to an issue."""
        now = datetime.now().isoformat()
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO comments (issue_id, content, author, created_date)
                VALUES (?, ?, ?, ?)
            """, (issue_id, content, author, now))
            return cursor.lastrowid
    
    def get_comments(self, issue_id: int) -> List[Dict[str, Any]]:
        """Get all comments for an issue."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM comments
                WHERE issue_id = ?
                ORDER BY created_date ASC
            """, (issue_id,))
            return [dict(row) for row in cursor.fetchall()]
    
    # Tag operations
    def add_tag(self, name: str, color: str = "#ffffff") -> int:
        """Add a new tag."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO tags (name, color)
                VALUES (?, ?)
            """, (name, color))
            return cursor.lastrowid
    
    def get_tags(self) -> List[Dict[str, Any]]:
        """Get all tags."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM tags ORDER BY name")
            return [dict(row) for row in cursor.fetchall()]
    
    # Search operations
    def search(self, query: str) -> Dict[str, List[Dict[str, Any]]]:
        """Search across projects and issues."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # Search projects
            cursor.execute("""
                SELECT * FROM projects
                WHERE name LIKE ? OR description LIKE ?
                ORDER BY last_updated DESC
            """, (f"%{query}%", f"%{query}%"))
            projects = [dict(row) for row in cursor.fetchall()]
            
            # Search issues
            cursor.execute("""
                SELECT * FROM issues
                WHERE title LIKE ? OR description LIKE ? OR tags LIKE ?
                ORDER BY priority DESC, created_date DESC
            """, (f"%{query}%", f"%{query}%", f"%{query}%"))
            issues = [dict(row) for row in cursor.fetchall()]
            
            return {
                "projects": projects,
                "issues": issues
            }
    
    # Import/Export operations
    def export_data(self) -> Dict[str, Any]:
        """Export all data as a dictionary."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # Export projects
            cursor.execute("SELECT * FROM projects")
            projects = [dict(row) for row in cursor.fetchall()]
            
            # Export issues
            cursor.execute("SELECT * FROM issues")
            issues = [dict(row) for row in cursor.fetchall()]
            
            # Export comments
            cursor.execute("SELECT * FROM comments")
            comments = [dict(row) for row in cursor.fetchall()]
            
            # Export tags
            cursor.execute("SELECT * FROM tags")
            tags = [dict(row) for row in cursor.fetchall()]
            
            return {
                "projects": projects,
                "issues": issues,
                "comments": comments,
                "tags": tags
            }
    
    def import_data(self, data: Dict[str, Any]) -> bool:
        """Import data from a dictionary."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Clear existing data
                cursor.execute("DELETE FROM comments")
                cursor.execute("DELETE FROM issues")
                cursor.execute("DELETE FROM projects")
                cursor.execute("DELETE FROM tags")
                
                # Import projects
                for project in data.get("projects", []):
                    cursor.execute("""
                        INSERT INTO projects (
                            id, name, description, version, status,
                            created_date, last_updated
                        )
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (
                        project["id"], project["name"], project["description"],
                        project["version"], project["status"],
                        project["created_date"], project["last_updated"]
                    ))
                
                # Import issues
                for issue in data.get("issues", []):
                    cursor.execute("""
                        INSERT INTO issues (
                            id, project_id, type, title, description,
                            priority, status, assigned_to, created_date,
                            due_date, tags
                        )
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        issue["id"], issue["project_id"], issue["type"],
                        issue["title"], issue["description"], issue["priority"],
                        issue["status"], issue["assigned_to"],
                        issue["created_date"], issue["due_date"], issue["tags"]
                    ))
                
                # Import comments
                for comment in data.get("comments", []):
                    cursor.execute("""
                        INSERT INTO comments (
                            id, issue_id, content, author, created_date
                        )
                        VALUES (?, ?, ?, ?, ?)
                    """, (
                        comment["id"], comment["issue_id"], comment["content"],
                        comment["author"], comment["created_date"]
                    ))
                
                # Import tags
                for tag in data.get("tags", []):
                    cursor.execute("""
                        INSERT INTO tags (id, name, color)
                        VALUES (?, ?, ?)
                    """, (tag["id"], tag["name"], tag["color"]))
                
                return True
        except Exception:
            return False 