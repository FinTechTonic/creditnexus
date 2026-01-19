#!/usr/bin/env python
"""Development server startup script with proper reload configuration."""
import sys
import traceback
import uvicorn

if __name__ == "__main__":
    # Note: We use string format "server:app" because uvicorn needs to import the module
    # itself when using reload=True. This allows uvicorn to properly track the module
    # for file changes. Passing app object directly breaks reload mechanism.
    try:
        uvicorn.run(
            "server:app",  # String format required for reload to work
            host="127.0.0.1",
            port=8000,
            reload=True,
            reload_excludes=[
                "*.venv/**",
                ".venv/**",
                "**/__pycache__/**",
                "**/*.pyc",
                "**/*.pyo",
                "**/.git/**",
                "**/node_modules/**",
                "**/alembic/versions/**",
            ],
            log_level="info",
        )
    except KeyboardInterrupt:
        print("\nServer stopped by user")
    except Exception as e:
        print(f"ERROR: Failed to start uvicorn: {e}")
        traceback.print_exc()
        sys.exit(1)
