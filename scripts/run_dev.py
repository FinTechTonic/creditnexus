#!/usr/bin/env python
"""Development server startup script with proper reload configuration."""
import os
import sys
import traceback
import uvicorn

if __name__ == "__main__":
    # Note: We use string format "server:app" because uvicorn needs to import the module
    # itself when using reload=True. This allows uvicorn to properly track the module
    # for file changes. Passing app object directly breaks reload mechanism.
    try:
        # With PM2, reload=True spawns a child whose stdout often doesn't reach PM2 logs;
        # use reload=False so the main process binds and logs are visible.
        reload = os.environ.get("PM2") != "1"
        uvicorn.run(
            "server:app",  # String format required when reload=True
            host="127.0.0.1",
            port=8000,
            reload=reload,
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
        print(f"ERROR: Failed to start uvicorn: {e}", flush=True)
        traceback.print_exc()
        sys.exit(1)
