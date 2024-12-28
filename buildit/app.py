from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Header, Footer, Input, Button, DataTable, Static, Label, Select
from textual.binding import Binding
from textual.screen import ModalScreen
from textual.coordinate import Coordinate
from textual.message import Message
from datetime import datetime
import json
import os
from .db import BuildDB

class AddProjectModal(ModalScreen):
    """Modal screen for adding new projects."""
    
    BINDINGS = [Binding("escape", "cancel", "Cancel")]
    
    class Submitted(Message):
        """Message sent when a project is submitted."""
        def __init__(self, project_data: dict) -> None:
            self.project_data = project_data
            super().__init__()
    
    def compose(self) -> ComposeResult:
        yield Container(
            Static("Add New Project", id="modal-title"),
            Input(placeholder="Name", id="name"),
            Input(placeholder="Description", id="description"),
            Input(placeholder="Version (e.g. 0.1.0)", id="version"),
            Select(
                [(status, status) for status in ["Active", "On Hold", "Completed"]],
                value="Active",
                id="status"
            ),
            Horizontal(
                Button("Cancel", variant="default", id="cancel"),
                Button("Add", variant="primary", id="add"),
                classes="buttons"
            ),
            id="add-project-modal",
        )

    def on_mount(self) -> None:
        self.query_one("#name").focus()

    def action_cancel(self) -> None:
        self.app.pop_screen()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "cancel":
            self.app.pop_screen()
        elif event.button.id == "add":
            self._submit_form()

    def _submit_form(self) -> None:
        try:
            name = self.query_one("#name").value.strip()
            if not name:
                self.app.notify("Name is required", severity="error")
                return

            description = self.query_one("#description").value.strip()
            version = self.query_one("#version").value.strip() or "0.1.0"
            status = self.query_one("#status").value

            project_data = {
                "name": name,
                "description": description,
                "version": version,
                "status": status
            }
            
            self.post_message(self.Submitted(project_data))
            self.app.pop_screen()
            
        except Exception as e:
            self.app.notify(f"Error adding project: {str(e)}", severity="error")

class AddIssueModal(ModalScreen):
    """Modal screen for adding new issues."""
    
    BINDINGS = [Binding("escape", "cancel", "Cancel")]
    
    class Submitted(Message):
        def __init__(self, issue_data: dict) -> None:
            self.issue_data = issue_data
            super().__init__()
    
    def __init__(self, project_id: int):
        super().__init__()
        self.project_id = project_id
    
    def compose(self) -> ComposeResult:
        yield Container(
            Static("Add New Issue", id="modal-title"),
            Select(
                [(type_, type_) for type_ in ["Feature", "Bug", "Task"]],
                value="Task",
                id="type"
            ),
            Input(placeholder="Title", id="title"),
            Input(placeholder="Description", id="description"),
            Input(placeholder="Due Date (YYYY-MM-DD)", id="due-date"),
            Select(
                [("Low", "Low"), ("Medium", "Medium"), ("High", "High")],
                value="Low",
                id="priority"
            ),
            Input(placeholder="Assigned To", id="assigned-to"),
            Input(placeholder="Tags (comma-separated)", id="tags"),
            Horizontal(
                Button("Cancel", variant="default", id="cancel"),
                Button("Add", variant="primary", id="add"),
                classes="buttons"
            ),
            id="add-issue-modal",
        )

    def on_mount(self) -> None:
        self.query_one("#title").focus()

    def action_cancel(self) -> None:
        self.app.pop_screen()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "cancel":
            self.app.pop_screen()
        elif event.button.id == "add":
            self._submit_form()

    def _submit_form(self) -> None:
        try:
            title = self.query_one("#title").value.strip()
            if not title:
                self.app.notify("Title is required", severity="error")
                return

            type_ = self.query_one("#type").value
            description = self.query_one("#description").value.strip()
            due_date = self.query_one("#due-date").value.strip() or None
            priority_map = {"Low": 1, "Medium": 3, "High": 5}
            priority = priority_map[self.query_one("#priority").value]
            assigned_to = self.query_one("#assigned-to").value.strip()
            tags = [tag.strip() for tag in self.query_one("#tags").value.split(",") if tag.strip()]

            issue_data = {
                "project_id": self.project_id,
                "type": type_,
                "title": title,
                "description": description,
                "due_date": due_date,
                "priority": priority,
                "assigned_to": assigned_to,
                "tags": tags
            }
            
            self.post_message(self.Submitted(issue_data))
            self.app.pop_screen()
            
        except Exception as e:
            self.app.notify(f"Error adding issue: {str(e)}", severity="error")

class ViewIssueModal(ModalScreen):
    """Modal screen for viewing issue details."""
    
    BINDINGS = [Binding("escape", "close", "Close")]
    
    def __init__(self, issue_data: dict, comments: list):
        super().__init__()
        self.issue_data = issue_data
        self.comments = comments
    
    def compose(self) -> ComposeResult:
        yield Container(
            Static(f"Issue Details: {self.issue_data['title']}", id="modal-title"),
            Vertical(
                Label(f"Type: {self.issue_data['type']}"),
                Label(f"Status: {self.issue_data['status']}"),
                Label(f"Priority: {'⭐' * self.issue_data['priority']}"),
                Label(f"Assigned To: {self.issue_data['assigned_to'] or 'Unassigned'}"),
                Label(f"Due Date: {self.issue_data['due_date'] or 'None'}"),
                Label(f"Tags: {', '.join(json.loads(self.issue_data['tags']))}"),
                Static("Description:", classes="section-header"),
                Static(self.issue_data['description'] or "No description"),
                Static("Comments:", classes="section-header"),
                *[Static(f"{c['author']} ({c['created_date']}): {c['content']}")
                  for c in self.comments],
                id="issue-details"
            ),
            Button("Close", variant="primary", id="close"),
            id="view-issue-modal",
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "close":
            self.app.pop_screen()

    def action_close(self) -> None:
        self.app.pop_screen()

class AddCommentModal(ModalScreen):
    """Modal screen for adding comments."""
    
    BINDINGS = [Binding("escape", "cancel", "Cancel")]
    
    class Submitted(Message):
        def __init__(self, comment_data: dict) -> None:
            self.comment_data = comment_data
            super().__init__()
    
    def __init__(self, issue_id: int):
        super().__init__()
        self.issue_id = issue_id
    
    def compose(self) -> ComposeResult:
        yield Container(
            Static("Add Comment", id="modal-title"),
            Input(placeholder="Your Name", id="author"),
            Input(placeholder="Comment", id="content"),
            Horizontal(
                Button("Cancel", variant="default", id="cancel"),
                Button("Add", variant="primary", id="add"),
                classes="buttons"
            ),
            id="add-comment-modal",
        )

    def on_mount(self) -> None:
        self.query_one("#author").focus()

    def action_cancel(self) -> None:
        self.app.pop_screen()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "cancel":
            self.app.pop_screen()
        elif event.button.id == "add":
            self._submit_form()

    def _submit_form(self) -> None:
        try:
            author = self.query_one("#author").value.strip()
            content = self.query_one("#content").value.strip()
            
            if not author or not content:
                self.app.notify("Author and content are required", severity="error")
                return

            comment_data = {
                "issue_id": self.issue_id,
                "author": author,
                "content": content
            }
            
            self.post_message(self.Submitted(comment_data))
            self.app.pop_screen()
            
        except Exception as e:
            self.app.notify(f"Error adding comment: {str(e)}", severity="error")

class HelpModal(ModalScreen):
    """Modal screen for displaying keyboard shortcuts help."""
    
    BINDINGS = [Binding("escape", "close", "Close")]
    
    def compose(self) -> ComposeResult:
        help_text = """
        Keyboard Shortcuts:
        
        Navigation:
        - j/↓: Move down
        - k/↑: Move up
        - tab: Switch between Projects/Issues view
        
        Projects:
        - a: Add new project
        - s: Toggle project status
        - d: Delete project
        
        Issues:
        - i: Add new issue
        - v: View issue details
        - c: Add comment
        - s: Toggle issue status
        - d: Delete issue
        
        File Operations:
        - e: Export data
        - l: Import data
        
        UI:
        - p: Toggle theme
        - ?: Show this help
        - q: Quit
        """
        yield Container(
            Static("Keyboard Shortcuts", id="modal-title"),
            Static(help_text, id="help-content"),
            Button("Close", variant="primary", id="close"),
            id="help-modal"
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "close":
            self.app.pop_screen()

    def action_close(self) -> None:
        self.app.pop_screen()

class SearchModal(ModalScreen):
    """Modal screen for searching."""
    
    BINDINGS = [Binding("escape", "cancel", "Cancel")]
    
    def compose(self) -> ComposeResult:
        yield Container(
            Static("Search", id="modal-title"),
            Input(placeholder="Enter search term", id="search-term"),
            DataTable(id="search-results", show_cursor=True),
            Button("Close", variant="primary", id="close"),
            id="search-modal",
        )

    def on_mount(self) -> None:
        """Set up the search results table and focus the input."""
        table = self.query_one("#search-results", DataTable)
        table.cursor_type = "row"
        table.zebra_stripes = True
        table.show_header = True
        
        if self.app.current_view == "projects":
            table.add_columns("ID", "Name", "Description", "Version", "Status", "Last Updated")
        else:
            table.add_columns("ID", "Type", "Title", "Priority", "Status", "Assigned To", "Due Date", "Tags")
        
        self.query_one("#search-term").focus()

    def on_input_changed(self, event: Input.Changed) -> None:
        """Update search results as user types."""
        if event.input.id == "search-term":
            self._update_results(event.value)

    def _update_results(self, search_term: str) -> None:
        """Update the results table based on search term."""
        table = self.query_one("#search-results", DataTable)
        table.clear()
        
        if not search_term:
            return
            
        search_term = search_term.lower()
        
        if self.app.current_view == "projects":
            projects = self.app.db.get_projects()
            for project in projects:
                if (search_term in project["name"].lower() or 
                    search_term in (project["description"] or "").lower()):
                    table.add_row(
                        str(project["id"]),
                        project["name"],
                        project["description"] or "",
                        project["version"],
                        project["status"],
                        project["last_updated"]
                    )
        else:
            issues = self.app.db.get_issues(self.app.current_project_id)
            for issue in issues:
                if (search_term in issue["title"].lower() or 
                    search_term in (issue["description"] or "").lower() or
                    search_term in (issue["assigned_to"] or "").lower() or
                    search_term in issue["type"].lower()):
                    tags = json.loads(issue["tags"])
                    table.add_row(
                        str(issue["id"]),
                        issue["type"],
                        issue["title"],
                        "⭐" * issue["priority"],
                        issue["status"],
                        issue["assigned_to"] or "",
                        issue["due_date"] or "",
                        ", ".join(tags)
                    )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "close":
            self.app.pop_screen()

    def action_cancel(self) -> None:
        """Close the search modal."""
        self.app.pop_screen()

class BuildApp(App):
    """Main BuildIt application."""
    
    CSS = """
    /* Main layout */
    #main-container {
        height: 1fr;
        padding: 0 1;
    }

    #help-text {
        text-align: center;
        padding: 1;
        background: $boost;
        color: $text-muted;
        text-style: italic;
    }

    /* Tables */
    DataTable {
        height: 1fr;
        min-height: 10;
        border: tall $primary;
        background: $surface;
    }

    DataTable > .datatable--header {
        background: $primary;
        color: $text;
        text-style: bold;
        height: 1;
    }

    /* Bottom bar */
    #bottom-bar {
        height: 3;
        padding: 1;
        background: $primary;
        color: $text;
        align: center middle;
    }

    #switch-view-button {
        min-width: 20;
        margin: 0 1;
    }

    /* Modal styling */
    .modal-container {
        width: 60;
        height: auto;
        padding: 1 2;
        border: thick $background 80%;
        background: $surface;
    }

    #modal-title {
        text-align: center;
        text-style: bold;
        width: 100%;
        height: 3;
    }

    Input, Select {
        margin: 1 0;
        width: 100%;
    }

    .section-header {
        margin-top: 1;
        text-style: bold;
    }

    #issue-details {
        margin: 1 0;
        height: auto;
        max-height: 30;
        overflow-y: auto;
    }

    #help-modal {
        width: 60;
        padding: 1 2;
        background: $surface;
        border: thick $primary;
    }

    #help-content {
        margin: 1 0;
        height: auto;
        min-height: 20;
    }
    """

    BINDINGS = [
        Binding("q", "quit", "Quit", show=True),
        Binding("a", "add_project", "Add Project", show=True),
        Binding("i", "add_issue", "Add Issue", show=True),
        Binding("v", "view_issue", "View Issue", show=True),
        Binding("c", "add_comment", "Comment", show=True),
        Binding("d", "delete", "Delete", show=True),
        Binding("s", "toggle_status", "Toggle Status", show=True),
        Binding("f", "search", "Find", show=True),
        Binding("e", "export", "Export", show=True),
        Binding("l", "import", "Import", show=True),
        Binding("/", "switch_view", "Switch View", show=True),
        Binding("p", "toggle_dark", "Theme", show=True),
        Binding("?", "show_help", "Help", show=True),
        Binding("j", "cursor_down", "Down", show=False),
        Binding("k", "cursor_up", "Up", show=False),
        Binding("down", "cursor_down", "Down", show=False),
        Binding("up", "cursor_up", "Up", show=False),
    ]

    def __init__(self):
        super().__init__()
        self.db = BuildDB()
        self.current_view = "projects"  # or "issues"
        self.current_project_id = None

    def compose(self) -> ComposeResult:
        """Create child widgets for the app."""
        yield Header(show_clock=True)
        yield Container(
            Static("Welcome to BuildIt! Press ? for help", id="help-text"),
            DataTable(id="main-table", show_cursor=True),
            id="main-container"
        )
        yield Container(
            Button("Switch View (Press /)", id="switch-view-button", variant="primary"),
            id="bottom-bar"
        )
        yield Footer()

    def on_mount(self) -> None:
        """Initialize the application."""
        table = self.query_one("#main-table", DataTable)
        table.cursor_type = "row"
        table.zebra_stripes = True
        table.show_header = True
        
        # Set up projects view initially
        self.setup_projects_view()
        
        # Auto-focus table and select first row if exists
        table.focus()
        if len(table.rows) > 0:
            table.move_cursor(row=0)

    def setup_projects_view(self) -> None:
        """Set up the projects view."""
        table = self.query_one("#main-table", DataTable)
        current_row = table.cursor_row
        table.clear()
        table.add_columns("ID", "Name", "Description", "Version", "Status", "Last Updated")
        
        # Update help text and button to show current view
        self.query_one("#help-text").update("[bold blue]Projects View[/] - Press ? for help")
        self.query_one("#switch-view-button").label = "Switch to Issues View"
        
        projects = self.db.get_projects()
        for project in projects:
            table.add_row(
                str(project["id"]),
                project["name"],
                project["description"] or "",
                project["version"],
                project["status"],
                project["last_updated"]
            )
        
        # Restore cursor position or select first row
        if len(projects) > 0:
            if current_row is not None and current_row < len(projects):
                table.move_cursor(row=current_row)
            else:
                table.move_cursor(row=0)

    def setup_issues_view(self) -> None:
        """Set up the issues view."""
        table = self.query_one("#main-table", DataTable)
        current_row = table.cursor_row
        table.clear()
        table.add_columns(
            "ID", "Type", "Title", "Priority", "Status",
            "Assigned To", "Due Date", "Tags"
        )
        
        # Update help text and button to show current view
        project_name = ""
        try:
            projects = self.db.get_projects()
            project = next(p for p in projects if p["id"] == self.current_project_id)
            project_name = f" for {project['name']}"
        except:
            pass
        
        self.query_one("#help-text").update(f"[bold green]Issues View{project_name}[/] - Press ? for help")
        self.query_one("#switch-view-button").label = "Back to Projects View"
        
        issues = self.db.get_issues(self.current_project_id)
        for issue in issues:
            tags = json.loads(issue["tags"])
            table.add_row(
                str(issue["id"]),
                issue["type"],
                issue["title"],
                "⭐" * issue["priority"],
                issue["status"],
                issue["assigned_to"] or "",
                issue["due_date"] or "",
                ", ".join(tags)
            )
        
        # Restore cursor position or select first row
        if len(issues) > 0:
            if current_row is not None and current_row < len(issues):
                table.move_cursor(row=current_row)
            else:
                table.move_cursor(row=0)

    def action_switch_view(self) -> None:
        """Switch between projects and issues view."""
        table = self.query_one("#main-table", DataTable)
        
        if self.current_view == "projects":
            # If no row is selected, select the first row
            if table.cursor_row is None and len(table.rows) > 0:
                table.move_cursor(row=0)
            
            # Only switch if we have a selected row
            if table.cursor_row is not None:
                try:
                    self.current_project_id = int(table.get_cell_at(Coordinate(table.cursor_row, 0)))
                    self.current_view = "issues"
                    self.setup_issues_view()
                    self.notify(f"Viewing issues for project {self.current_project_id}")
                except Exception as e:
                    self.notify(f"Error switching view: {str(e)}", severity="error")
            else:
                self.notify("Please select a project first", severity="error")
        else:
            self.current_view = "projects"
            self.current_project_id = None
            self.setup_projects_view()
            self.notify("Viewing all projects")

    def action_add_project(self) -> None:
        """Show the add project modal."""
        if self.current_view != "projects":
            self.notify("Switch to projects view to add a project", severity="error")
            return
        self.push_screen(AddProjectModal())

    def action_add_issue(self) -> None:
        """Show the add issue modal."""
        if self.current_view != "issues":
            self.notify("Switch to issues view to add an issue", severity="error")
            return
        if self.current_project_id is None:
            self.notify("No project selected", severity="error")
            return
        self.push_screen(AddIssueModal(self.current_project_id))

    def action_view_issue(self) -> None:
        """Show the view issue modal."""
        if self.current_view != "issues":
            self.notify("Switch to issues view to view issue details", severity="error")
            return
            
        table = self.query_one("#main-table", DataTable)
        if table.cursor_row is not None:
            try:
                issue_id = int(table.get_cell_at(Coordinate(table.cursor_row, 0)))
                issues = self.db.get_issues(self.current_project_id)
                issue = next(i for i in issues if i["id"] == issue_id)
                comments = self.db.get_comments(issue_id)
                self.push_screen(ViewIssueModal(issue, comments))
            except Exception as e:
                self.notify(f"Error viewing issue: {str(e)}", severity="error")

    def action_add_comment(self) -> None:
        """Show the add comment modal."""
        if self.current_view != "issues":
            self.notify("Switch to issues view to add a comment", severity="error")
            return
            
        table = self.query_one("#main-table", DataTable)
        if table.cursor_row is not None:
            try:
                issue_id = int(table.get_cell_at(Coordinate(table.cursor_row, 0)))
                self.push_screen(AddCommentModal(issue_id))
            except Exception as e:
                self.notify(f"Error adding comment: {str(e)}", severity="error")

    def action_delete(self) -> None:
        """Delete the selected item."""
        table = self.query_one("#main-table", DataTable)
        if table.cursor_row is None:
            return
            
        try:
            item_id = int(table.get_cell_at(Coordinate(table.cursor_row, 0)))
            if self.current_view == "projects":
                if self.db.delete_project(item_id):
                    self.notify("Project deleted successfully")
                    self.setup_projects_view()
            else:
                if self.db.delete_issue(item_id):
                    self.notify("Issue deleted successfully")
                    self.setup_issues_view()
        except Exception as e:
            self.notify(f"Error deleting item: {str(e)}", severity="error")

    def action_toggle_status(self) -> None:
        """Toggle the status of the selected item."""
        table = self.query_one("#main-table", DataTable)
        if table.cursor_row is None:
            return
            
        try:
            item_id = int(table.get_cell_at(Coordinate(table.cursor_row, 0)))
            if self.current_view == "projects":
                current_status = table.get_cell_at(Coordinate(table.cursor_row, 4))
                new_status = "Completed" if current_status != "Completed" else "Active"
                if self.db.update_project(item_id, status=new_status):
                    self.notify("Project status updated")
                    self.setup_projects_view()
            else:
                current_status = table.get_cell_at(Coordinate(table.cursor_row, 4))
                new_status = "Done" if current_status != "Done" else "Open"
                if self.db.update_issue(item_id, status=new_status):
                    self.notify("Issue status updated")
                    self.setup_issues_view()
        except Exception as e:
            self.notify(f"Error updating status: {str(e)}", severity="error")

    def action_export(self) -> None:
        """Export data to JSON."""
        try:
            home = os.path.expanduser("~")
            filepath = os.path.join(home, "buildit_backup.json")
            data = self.db.export_data()
            with open(filepath, 'w') as f:
                json.dump(data, f, indent=2)
            self.notify(f"Data exported to {filepath}")
        except Exception as e:
            self.notify(f"Error exporting data: {str(e)}", severity="error")

    def action_import(self) -> None:
        """Import data from JSON."""
        try:
            home = os.path.expanduser("~")
            filepath = os.path.join(home, "buildit_backup.json")
            if not os.path.exists(filepath):
                self.notify(f"No backup file found at {filepath}", severity="error")
                return
                
            with open(filepath, 'r') as f:
                data = json.load(f)
            
            if self.db.import_data(data):
                self.notify("Data imported successfully")
                if self.current_view == "projects":
                    self.setup_projects_view()
                else:
                    self.setup_issues_view()
            else:
                self.notify("Error importing data", severity="error")
        except Exception as e:
            self.notify(f"Error importing data: {str(e)}", severity="error")

    def on_add_project_modal_submitted(self, message: AddProjectModal.Submitted) -> None:
        """Handle the submitted message from add project modal."""
        try:
            self.db.add_project(
                message.project_data["name"],
                message.project_data["description"],
                message.project_data["version"],
                message.project_data["status"]
            )
            self.notify("Project added successfully")
            self.setup_projects_view()
        except Exception as e:
            self.notify(f"Error adding project: {str(e)}", severity="error")

    def on_add_issue_modal_submitted(self, message: AddIssueModal.Submitted) -> None:
        """Handle the submitted message from add issue modal."""
        try:
            self.db.add_issue(
                message.issue_data["project_id"],
                message.issue_data["type"],
                message.issue_data["title"],
                message.issue_data["description"],
                message.issue_data["priority"],
                "Open",
                message.issue_data["assigned_to"],
                message.issue_data["due_date"],
                message.issue_data["tags"]
            )
            self.notify("Issue added successfully")
            self.setup_issues_view()
        except Exception as e:
            self.notify(f"Error adding issue: {str(e)}", severity="error")

    def on_add_comment_modal_submitted(self, message: AddCommentModal.Submitted) -> None:
        """Handle the submitted message from add comment modal."""
        try:
            self.db.add_comment(
                message.comment_data["issue_id"],
                message.comment_data["content"],
                message.comment_data["author"]
            )
            self.notify("Comment added successfully")
        except Exception as e:
            self.notify(f"Error adding comment: {str(e)}", severity="error")

    def action_show_help(self) -> None:
        """Show help modal with keyboard shortcuts."""
        self.push_screen(HelpModal())

    def action_cursor_up(self) -> None:
        """Move cursor up."""
        table = self.query_one("#main-table", DataTable)
        if table.cursor_row is not None and table.cursor_row > 0:
            table.move_cursor(row=table.cursor_row - 1)

    def action_cursor_down(self) -> None:
        """Move cursor down."""
        table = self.query_one("#main-table", DataTable)
        if table.cursor_row is not None and table.cursor_row < len(table.rows) - 1:
            table.move_cursor(row=table.cursor_row + 1)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "switch-view-button":
            self.action_switch_view()

    def action_search(self) -> None:
        """Show the search modal."""
        self.push_screen(SearchModal())
