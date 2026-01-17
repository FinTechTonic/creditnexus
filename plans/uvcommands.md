## 📦 Python Environment Management

### Common uv Commands

```bash
# Install/update dependencies
uv sync

# Add a new dependency
uv add <package-name>

# Add a development dependency
uv add --dev <package-name>

# Remove a dependency
uv remove <package-name>

# Update all dependencies
uv sync --upgrade

# Run commands in the uv environment
uv run python main.py
uv run pytest
uv run alembic upgrade head
# Show installed packages
uv pip list
```

### Adding Dependencies

When adding new Python packages, use `uv add` instead of manually editing `requirements.txt`:

```bash
uv add fastapi  # Add a regular dependency
uv add --dev pytest  # Add a development dependency
```

This automatically updates `pyproject.toml` and `uv.lock`.

### Running the Development Server

**Option 1: Using the startup script with uv (Recommended)**
```bash
uv run python run_dev.py
```

**Option 2: Using the startup script without uv (Simple)**
```bash
python run_dev.py
```
*Note: Requires Python environment with dependencies installed*

**Option 3: Using uvicorn directly with uv**
```bash
uv run uvicorn server:app --reload \
  --reload-exclude ".venv/**" \
  --reload-exclude "**/__pycache__/**" \
  --reload-exclude "**/*.pyc" \
  --reload-exclude "**/*.pyo" \
  --reload-exclude "**/.git/**" \
  --reload-exclude "**/node_modules/**"
```

**Option 4: Using uvicorn directly without uv**
```bash
uvicorn server:app --reload \
  --reload-exclude ".venv/**" \
  --reload-exclude "**/__pycache__/**" \
  --reload-exclude "**/*.pyc" \
  --reload-exclude "**/*.pyo" \
  --reload-exclude "**/.git/**" \
  --reload-exclude "**/node_modules/**"
```
*Note: Requires Python environment with dependencies installed*

**Note:** The `CancelledError` traceback during reload is expected and harmless. 
It occurs when uvicorn's reloader restarts the server and is normal development behavior.


