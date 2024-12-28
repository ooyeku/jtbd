"""
JTBD Dashboard entry point.
"""

from .app import DashboardApp

def main():
    """Run the JTBD Dashboard application."""
    app = DashboardApp()
    app.run()

if __name__ == "__main__":
    main() 