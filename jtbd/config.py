"""Configuration management for JTBD applications."""

import os
import json
from typing import Dict, Any, Optional

class Config:
    """Shared configuration for JTBD applications."""
    
    def __init__(self):
        """Initialize configuration with default values."""
        self.home_dir = os.path.expanduser("~")
        self.config_dir = os.path.join(self.home_dir, ".jtbd")
        self.config_file = os.path.join(self.config_dir, "config.json")
        self.todo_db = os.path.join(self.config_dir, "todo.db")
        self.buildit_db = os.path.join(self.config_dir, "buildit.db")
        self._ensure_config_dir()
        self._load_config()

    def _ensure_config_dir(self) -> None:
        """Create configuration directory if it doesn't exist."""
        if not os.path.exists(self.config_dir):
            os.makedirs(self.config_dir)

    def _load_config(self) -> None:
        """Load configuration from file or create with defaults."""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r') as f:
                    config = json.load(f)
                self.todo_db = config.get('todo_db', self.todo_db)
                self.buildit_db = config.get('buildit_db', self.buildit_db)
            except Exception as e:
                print(f"Error loading config: {e}")
        else:
            self._save_config()

    def _save_config(self) -> None:
        """Save current configuration to file."""
        config = {
            'todo_db': self.todo_db,
            'buildit_db': self.buildit_db
        }
        try:
            with open(self.config_file, 'w') as f:
                json.dump(config, f, indent=2)
        except Exception as e:
            print(f"Error saving config: {e}")

    def update(self, **kwargs) -> None:
        """Update configuration values."""
        if 'todo_db' in kwargs:
            self.todo_db = kwargs['todo_db']
        if 'buildit_db' in kwargs:
            self.buildit_db = kwargs['buildit_db']
        self._save_config()

    def get_todo_db(self) -> str:
        """Get the todo database path."""
        return self.todo_db

    def get_buildit_db(self) -> str:
        """Get the buildit database path."""
        return self.buildit_db

# Create global config instance
config = Config()

def get_config() -> Config:
    """Get the global configuration instance."""
    return config 