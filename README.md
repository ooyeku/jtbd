# JTBD (Just Track By Doing)

A collection of task tracking tools designed to help you manage your work efficiently.

## Features

- **Todo**: A simple, keyboard-driven todo list manager
- **BuildIt**: A project and issue tracking system for software development
- **Dashboard**: A beautiful overview of your tasks and projects
- More modules coming soon!

## Installation

```bash
# Clone the repository
git clone <tbd>
cd jtbd

# Create and activate virtual environment (optional but recommended)
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install the package
pip install -e .
```

## Usage

### Todo App
```bash
# Run the todo application
todo
```

Key bindings:
- `a`: Add new todo
- `d`: Delete todo
- `t`: Toggle todo completion
- `e`: Edit todo
- `s`: Search todos
- `i`: Import todos
- `x`: Export todos
- `h`: Show help
- `q`: Quit

### BuildIt App
```bash
# Run the buildit application
buildit
```

Key bindings:
- `/`: Switch between Projects and Issues view
- `a`: Add new project/issue
- `d`: Delete project/issue
- `e`: Edit project/issue
- `v`: View details
- `c`: Add comment (in issue view)
- `f`: Find/search
- `h`: Show help
- `q`: Quit

### Dashboard
```bash
# Run the dashboard
jtbd-dash
```

Key bindings:
- `r`: Refresh statistics
- `q`: Quit

The dashboard provides:
- Todo statistics (total tasks, completion rate, due today, high priority)
- Project statistics (total projects, active projects, open issues, critical issues)
- Recent activity across both applications
- Real-time updates with refresh

## Configuration

JTBD stores its configuration and databases in `~/.jtbd/`. You can modify the configuration by editing `~/.jtbd/config.json`.

## Development

To add a new module:

1. Create a new directory for your module
2. Add `__init__.py` and implement your module
3. Update `setup.py` to include your module's entry point
4. Add documentation in README.md

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
