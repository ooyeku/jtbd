"""
Todo application entry point.
"""

from .app import TodoApp

def main():
    """Run the Todo application."""
    app = TodoApp()
    app.run()

if __name__ == "__main__":
    main() 