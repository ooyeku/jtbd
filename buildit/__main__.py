"""
BuildIt application entry point.
"""

from .app import BuildApp

def main():
    """Run the BuildIt application."""
    app = BuildApp()
    app.run()

if __name__ == "__main__":
    main() 