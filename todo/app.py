from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal
from textual.widgets import Header, Footer, Input, Button, DataTable, Static, Label
from textual.binding import Binding
from textual.screen import ModalScreen
from textual.coordinate import Coordinate
from textual.message import Message
from datetime import datetime
import json
import os
from .db import TodoDB


class AddTodoModal(ModalScreen):
    """Modal screen for adding new todos."""
    
    BINDINGS = [Binding("escape", "cancel", "Cancel")]
    
    class Submitted(Message):
        """Message sent when a todo is submitted."""
        def __init__(self, todo_data: dict) -> None:
            self.todo_data = todo_data
            super().__init__()
    
    def compose(self) -> ComposeResult:
        yield Container(
            Static("Add New Todo", id="modal-title"),
            Input(placeholder="Title", id="title"),
            Input(placeholder="Description", id="description"),
            Input(placeholder="Due Date (YYYY-MM-DD)", id="due-date"),
            Input(placeholder="Priority (0-5)", id="priority"),
            Horizontal(
                Button("Cancel", variant="default", id="cancel"),
                Button("Add", variant="primary", id="add"),
                classes="buttons"
            ),
            id="add-todo-modal",
        )

    def on_mount(self) -> None:
        # Focus the title input when modal opens
        self.query_one("#title").focus()

    def action_cancel(self) -> None:
        self.app.pop_screen()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "cancel":
            self.app.pop_screen()
        elif event.button.id == "add":
            self._submit_form()

    def on_input_submitted(self) -> None:
        """Handle Enter key in any input."""
        self._submit_form()

    def _submit_form(self) -> None:
        """Process and submit the form data."""
        try:
            title = self.query_one("#title").value.strip()
            if not title:
                self.app.notify("Title is required", severity="error")
                return

            description = self.query_one("#description").value.strip()
            due_date = self.query_one("#due-date").value.strip() or None
            priority_str = self.query_one("#priority").value.strip() or "0"
            
            try:
                priority = int(priority_str)
                if not 0 <= priority <= 5:
                    raise ValueError("Priority must be between 0 and 5")
            except ValueError as e:
                self.app.notify(str(e), severity="error")
                return

            todo_data = {
                "title": title,
                "description": description,
                "due_date": due_date,
                "priority": priority
            }
            
            self.post_message(self.Submitted(todo_data))
            self.app.pop_screen()
            
        except Exception as e:
            self.app.notify(f"Error adding todo: {str(e)}", severity="error")

class ViewEditTodoModal(ModalScreen):
    """Modal screen for viewing and editing todos."""
    
    BINDINGS = [Binding("escape", "cancel", "Cancel")]
    
    class TodoUpdated(Message):
        """Message sent when a todo is updated."""
        def __init__(self, todo_id: int, todo_data: dict) -> None:
            self.todo_id = todo_id
            self.todo_data = todo_data
            super().__init__()
    
    def __init__(self, todo_id: int, todo_data: dict):
        super().__init__()
        self.todo_id = todo_id
        self.todo_data = todo_data
    
    def compose(self) -> ComposeResult:
        yield Container(
            Static("View/Edit Todo", id="modal-title"),
            Input(value=self.todo_data["title"], placeholder="Title", id="title"),
            Input(value=self.todo_data["description"], placeholder="Description", id="description"),
            Input(value=self.todo_data["due_date"] or "", placeholder="Due Date (YYYY-MM-DD)", id="due-date"),
            Input(value=str(self.todo_data["priority"]), placeholder="Priority (0-5)", id="priority"),
            Horizontal(
                Button("Cancel", variant="default", id="cancel"),
                Button("Save", variant="primary", id="save"),
                classes="buttons"
            ),
            id="add-todo-modal",
        )

    def on_mount(self) -> None:
        self.query_one("#title").focus()

    def action_cancel(self) -> None:
        self.app.pop_screen()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "cancel":
            self.app.pop_screen()
        elif event.button.id == "save":
            self._submit_form()

    def on_input_submitted(self) -> None:
        """Handle Enter key in any input."""
        self._submit_form()

    def _submit_form(self) -> None:
        try:
            title = self.query_one("#title").value.strip()
            if not title:
                self.app.notify("Title is required", severity="error")
                return

            description = self.query_one("#description").value.strip()
            due_date = self.query_one("#due-date").value.strip() or None
            priority_str = self.query_one("#priority").value.strip() or "0"
            
            try:
                priority = int(priority_str)
                if not 0 <= priority <= 5:
                    raise ValueError("Priority must be between 0 and 5")
            except ValueError as e:
                self.app.notify(str(e), severity="error")
                return

            todo_data = {
                "title": title,
                "description": description,
                "due_date": due_date,
                "priority": priority
            }
            
            self.post_message(self.TodoUpdated(self.todo_id, todo_data))
            self.app.pop_screen()
            
        except Exception as e:
            self.app.notify(f"Error updating todo: {str(e)}", severity="error")

class SearchModal(ModalScreen):
    """Modal for searching todos."""
    
    BINDINGS = [
        Binding("escape", "cancel", "Cancel"),
        Binding("enter", "select", "Select"),
    ]
    
    def compose(self) -> ComposeResult:
        yield Container(
            Static("Search Todos", id="modal-title"),
            Input(placeholder="Type to search...", id="search"),
            DataTable(id="search-results"),
            Static("No results found", id="no-results", classes="help-text"),
            Horizontal(
                Button("Cancel", variant="default", id="cancel"),
                Button("Select", variant="primary", id="select"),
                classes="buttons"
            ),
            id="search-modal",
        )

    def on_mount(self) -> None:
        """Set up the search interface."""
        table = self.query_one("#search-results", DataTable)
        table.add_columns("ID", "Title", "Description", "Due Date", "Priority", "Status")
        self.query_one("#search").focus()

    def on_input_changed(self, event: Input.Changed) -> None:
        """Update search results as user types."""
        if event.input.id == "search":
            self._update_results()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "cancel":
            self.app.pop_screen()
        elif event.button.id == "select":
            self._select_current_todo()

    def action_cancel(self) -> None:
        """Handle escape key."""
        self.app.pop_screen()

    def action_select(self) -> None:
        """Handle enter key."""
        self._select_current_todo()

    def _update_results(self) -> None:
        """Update the search results."""
        search_term = self.query_one("#search").value.strip()
        table = self.query_one("#search-results", DataTable)
        table.clear()
        
        try:
            todos = self.app.db.search_todos(search_term)
            
            for todo in todos:
                table.add_row(
                    str(todo["id"]),
                    todo["title"],
                    todo["description"] or "",
                    todo["due_date"] or "",
                    "⭐" * todo["priority"],
                    "✅" if todo["completed"] else "⬜"
                )
            
            # Show/hide no results message
            no_results = self.query_one("#no-results")
            no_results.display = not bool(todos)
            
            # Select first row if results exist
            if todos:
                table.move_cursor(row=0)
                
        except Exception as e:
            self.app.notify(f"Search error: {str(e)}", severity="error")

    def _select_current_todo(self) -> None:
        """Select the current todo and close the modal."""
        table = self.query_one("#search-results", DataTable)
        if table.cursor_row is not None and table.cursor_row < len(table.rows):
            try:
                todo_id = int(table.get_cell_at(Coordinate(table.cursor_row, 0)))
                self.app.pop_screen()
                self.post_message(self.Selected(todo_id))
            except Exception as e:
                self.app.notify(f"Error selecting todo: {str(e)}", severity="error")

    class Selected(Message):
        """Message sent when a todo is selected."""
        def __init__(self, todo_id: int):
            self.todo_id = todo_id
            super().__init__()

class FileDialog(ModalScreen):
    """Modal for file operations."""
    
    def __init__(self, operation: str = "save", extension: str = ".json"):
        super().__init__()
        self.operation = operation
        self.extension = extension
        self.current_path = os.path.expanduser("~")
    
    def compose(self) -> ComposeResult:
        yield Container(
            Static(f"{'Save' if self.operation == 'save' else 'Open'} File", id="modal-title"),
            Input(value=self.current_path, placeholder="Path", id="path"),
            Input(placeholder="Filename", id="filename"),
            Static("", id="status", classes="help-text"),
            Horizontal(
                Button("Cancel", variant="default", id="cancel"),
                Button("Save" if self.operation == "save" else "Open", variant="primary", id="confirm"),
                classes="buttons"
            ),
            id="file-dialog",
        )

    def on_mount(self) -> None:
        self.query_one("#filename").focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "cancel":
            self.app.pop_screen()
        elif event.button.id == "confirm":
            path = self.query_one("#path").value
            filename = self.query_one("#filename").value
            
            if not filename:
                self.query_one("#status").update("Please enter a filename")
                return
                
            if not filename.endswith(self.extension):
                filename += self.extension
                
            full_path = os.path.join(path, filename)
            
            try:
                if self.operation == "save":
                    self.dismiss(("save", full_path))
                else:
                    if not os.path.exists(full_path):
                        self.query_one("#status").update("File does not exist")
                        return
                    self.dismiss(("open", full_path))
            except Exception as e:
                self.query_one("#status").update(f"Error: {str(e)}")

class HelpModal(ModalScreen):
    """Modal for displaying keyboard shortcuts help."""
    
    BINDINGS = [
        Binding("escape", "close", "Close"),
    ]
    
    def compose(self) -> ComposeResult:
        help_text = """
        Keyboard Shortcuts:
        
        Navigation:
        - j/↓: Move down
        - k/↑: Move up
        - g: Go to top
        - G: Go to bottom
        
        Actions:
        - a: Add new todo
        - e: Edit selected todo
        - space: Toggle completion
        - d: Delete todo
        - f: Find/search todos
        
        File Operations:
        - s: Save/export todos
        - l: Load/import todos
        
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
        """Handle button presses."""
        if event.button.id == "close":
            self.app.pop_screen()

    def action_close(self) -> None:
        """Handle escape key."""
        self.app.pop_screen()

class TodoApp(App):
    """Main todo application."""
    
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

    /* Table styling */
    #todo-table {
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

    DataTable > .datatable--cursor {
        background: $accent;
        color: $text;
        text-style: bold;
    }

    DataTable > .datatable--row {
        height: 1;
        padding: 0 1;
    }

    DataTable > .datatable--row-hover {
        background: $boost;
    }

    DataTable > .datatable--row-selected {
        background: $accent;
        color: $text;
        text-style: bold;
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

    Input {
        margin: 1 0;
        width: 100%;
    }

    Input:focus {
        border: tall $accent;
    }

    .buttons {
        width: 100%;
        height: 3;
        align: center middle;
        margin-top: 1;
    }

    Button {
        min-width: 16;
        margin: 0 1;
    }

    Button:hover {
        background: $accent;
    }

    /* Help modal */
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

    /* Search modal */
    #search-modal {
        width: 80;
        height: 40;
        padding: 1 2;
        background: $surface;
        border: thick $primary;
    }

    #search-modal #search-results {
        height: 1fr;
        min-height: 20;
        margin: 1 0;
    }

    #search-modal .help-text {
        text-align: center;
        color: $text-disabled;
        margin: 1 0;
    }

    /* Footer styling */
    Footer {
        background: $primary;
        color: $text;
        padding: 0 1;
    }

    Footer > .footer--key {
        text-style: bold;
        background: $accent;
        color: $text;
    }

    Footer > .footer--highlight {
        background: $boost;
        color: $text;
    }
    """

    BINDINGS = [
        Binding("q", "quit", "Quit", show=True),
        Binding("a", "add_todo", "Add", show=True),
        Binding("d", "delete_todo", "Delete", show=True),
        Binding("space", "toggle_todo", "Toggle", show=True),
        Binding("e", "view_edit_todo", "Edit", show=True),
        Binding("f", "search_todos", "Find", show=True),
        Binding("s", "export_todos", "Save", show=True),
        Binding("l", "import_todos", "Load", show=True),
        Binding("j", "cursor_down", "Down", show=False),
        Binding("k", "cursor_up", "Up", show=False),
        Binding("g", "cursor_home", "Top", show=False),
        Binding("G", "cursor_end", "Bottom", show=False),
        Binding("p", "toggle_dark", "Theme", show=True),
        Binding("?", "show_help", "Help", show=True),
    ]

    def __init__(self):
        super().__init__()
        self.db = TodoDB()

    def compose(self) -> ComposeResult:
        """Create child widgets for the app."""
        yield Header(show_clock=True)
        yield Container(
            Static("Welcome to TodoApp! Press ? for help", id="help-text"),
            DataTable(id="todo-table", show_cursor=True),
            id="main-container"
        )
        yield Footer()

    def on_mount(self) -> None:
        """Initialize the application."""
        # Initialize table
        table = self.query_one("#todo-table", DataTable)
        table.cursor_type = "row"
        table.zebra_stripes = True
        table.show_header = True
        table.add_columns(
            "ID", "Title", "Description", "Due Date", "Priority", "Status", "Created"
        )
        
        # Add tooltips
        self.query_one("#help-text").tooltip = "Press ? to show keyboard shortcuts"
        
        # Initial refresh
        self.refresh_todos()
        
        # Auto-focus table
        table.focus()

    def action_show_help(self) -> None:
        """Show help modal with keyboard shortcuts."""
        self.push_screen(HelpModal())

    def refresh_todos(self) -> None:
        """Refresh the todo list display."""
        table = self.query_one("#todo-table", DataTable)
        current_row = table.cursor_row
        
        # Clear and update table
        table.clear()
        todos = self.db.get_todos()
        
        for todo in todos:
            # Get priority and status
            priority = todo[4]
            completed = todo[5]
            due_date = todo[3]
            
            # Style priority stars
            if priority >= 4:
                priority_text = f"[red]{'⭐' * priority}[/]"
            elif priority >= 2:
                priority_text = f"[yellow]{'⭐' * priority}[/]"
            else:
                priority_text = f"[green]{'⭐' * priority}[/]"
            
            # Style status
            status_text = "[green]✅[/]" if completed else "⬜"
            
            # Style due date
            if due_date:
                try:
                    due = datetime.strptime(due_date, "%Y-%m-%d")
                    if due.date() < datetime.now().date():
                        due_date_text = f"[red bold]{due_date}[/]"
                    else:
                        due_date_text = f"[yellow]{due_date}[/]"
                except ValueError:
                    due_date_text = due_date
            else:
                due_date_text = ""
            
            # Add row with styled text
            table.add_row(
                str(todo[0]),
                todo[1],
                todo[2] or "",
                due_date_text,
                priority_text,
                status_text,
                todo[6]
            )
        
        # Restore cursor position and focus
        if todos:
            if current_row is not None and current_row < len(todos):
                table.move_cursor(row=current_row)
            else:
                table.move_cursor(row=0)
            table.focus()

    def notify_with_sound(self, message: str, severity: str = "information") -> None:
        """Show notification with sound based on severity."""
        self.notify(message, severity=severity)
        # You could add sound here if the terminal supports it 

    def add_todo(self, todo_data: dict) -> None:
        """Add a new todo item."""
        try:
            self.db.add_todo(
                todo_data["title"],
                todo_data["description"],
                todo_data["due_date"],
                todo_data["priority"]
            )
            self.refresh_todos()
            self.notify("Todo added successfully!", severity="information")
        except Exception as e:
            self.notify(f"Error adding todo: {str(e)}", severity="error")

    def action_add_todo(self) -> None:
        """Show the add todo modal."""
        self.push_screen(AddTodoModal())

    def action_toggle_todo(self) -> None:
        """Toggle the completion status of the selected todo."""
        table = self.query_one("#todo-table", DataTable)
        if table.cursor_row is not None and table.cursor_row < len(table.rows):
            try:
                todo_id = int(table.get_cell_at(Coordinate(table.cursor_row, 0)))
                self.db.toggle_todo(todo_id)
                self.refresh_todos()
                self.notify("Todo status toggled!", severity="information")
            except Exception as e:
                self.notify(f"Could not toggle todo: {str(e)}", severity="error")

    def action_delete_todo(self) -> None:
        """Delete the selected todo."""
        table = self.query_one("#todo-table", DataTable)
        if table.cursor_row is not None and table.cursor_row < len(table.rows):
            try:
                todo_id = int(table.get_cell_at(Coordinate(table.cursor_row, 0)))
                self.db.delete_todo(todo_id)
                self.refresh_todos()
                self.notify("Todo deleted!", severity="information")
            except Exception as e:
                self.notify(f"Could not delete todo: {str(e)}", severity="error")

    def action_view_edit_todo(self) -> None:
        """Show the view/edit todo modal for the selected todo."""
        table = self.query_one("#todo-table", DataTable)
        if table.cursor_row is not None and table.cursor_row < len(table.rows):
            try:
                todo_id = int(table.get_cell_at(Coordinate(table.cursor_row, 0)))
                todo = self._get_todo_data(table.cursor_row)
                self.push_screen(ViewEditTodoModal(todo_id, todo))
            except Exception as e:
                self.notify(f"Could not open todo: {str(e)}", severity="error")

    def _get_todo_data(self, row: int) -> dict:
        """Get todo data from the table row."""
        table = self.query_one("#todo-table", DataTable)
        return {
            "title": table.get_cell_at(Coordinate(row, 1)),
            "description": table.get_cell_at(Coordinate(row, 2)),
            "due_date": table.get_cell_at(Coordinate(row, 3)),
            "priority": len(table.get_cell_at(Coordinate(row, 4)).strip()) # Count stars for priority
        }

    def on_add_todo_modal_submitted(self, message: AddTodoModal.Submitted) -> None:
        """Handle the submitted message from the add todo modal."""
        self.add_todo(message.todo_data)

    def on_view_edit_todo_modal_todo_updated(self, message: ViewEditTodoModal.TodoUpdated) -> None:
        """Handle the todo updated message from the view/edit modal."""
        try:
            self.db.update_todo(
                message.todo_id,
                message.todo_data["title"],
                message.todo_data["description"],
                message.todo_data["due_date"],
                message.todo_data["priority"]
            )
            self.refresh_todos()
            self.notify("Todo updated successfully!", severity="information")
        except Exception as e:
            self.notify(f"Error updating todo: {str(e)}", severity="error")

    def action_export_todos(self) -> None:
        """Export todos to JSON."""
        try:
            home = os.path.expanduser("~")
            filepath = os.path.join(home, "todos_backup.json")
            todos = self.db.export_todos()
            with open(filepath, 'w') as f:
                json.dump(todos, f, indent=2)
            self.notify(f"Todos exported to {filepath}", severity="information")
        except Exception as e:
            self.notify(f"Error exporting todos: {str(e)}", severity="error")

    def action_import_todos(self) -> None:
        """Import todos from JSON."""
        try:
            home = os.path.expanduser("~")
            filepath = os.path.join(home, "todos_backup.json")
            if not os.path.exists(filepath):
                self.notify(f"No backup file found at {filepath}", severity="error")
                return
                
            with open(filepath, 'r') as f:
                todos = json.load(f)
            self.db.import_todos(todos)
            self.refresh_todos()
            self.notify(f"Todos imported from {filepath}", severity="information")
        except json.JSONDecodeError:
            self.notify("Invalid JSON file format", severity="error")
        except Exception as e:
            self.notify(f"Error importing todos: {str(e)}", severity="error")

    def action_search_todos(self) -> None:
        """Show the search modal."""
        self.push_screen(SearchModal())

    def on_search_modal_selected(self, message: SearchModal.Selected) -> None:
        """Handle the selected message from the search modal."""
        # Find the todo in the main table and select it
        table = self.query_one("#todo-table", DataTable)
        for row in range(len(table.rows)):
            if int(table.get_cell_at(Coordinate(row, 0))) == message.todo_id:
                table.move_cursor(row=row)
                table.focus()
                break

    def action_cursor_up(self) -> None:
        """Move cursor up."""
        table = self.query_one("#todo-table", DataTable)
        if table.cursor_row is not None and table.cursor_row > 0:
            table.move_cursor(row=table.cursor_row - 1)

    def action_cursor_down(self) -> None:
        """Move cursor down."""
        table = self.query_one("#todo-table", DataTable)
        if table.cursor_row is not None and table.cursor_row < len(table.rows) - 1:
            table.move_cursor(row=table.cursor_row + 1)

    def action_cursor_home(self) -> None:
        """Move cursor to first row."""
        table = self.query_one("#todo-table", DataTable)
        if len(table.rows) > 0:
            table.move_cursor(row=0)

    def action_cursor_end(self) -> None:
        """Move cursor to last row."""
        table = self.query_one("#todo-table", DataTable)
        if len(table.rows) > 0:
            table.move_cursor(row=len(table.rows) - 1) 