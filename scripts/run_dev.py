#!/usr/bin/env python
"""Development server startup script with proper reload configuration."""
import json
import os
import sys
import time
import traceback
import uvicorn

if __name__ == "__main__":
    # #region agent log
    try:
        with open(r"c:\Users\MeMyself\creditnexus\.cursor\debug.log", "a") as f:
            f.write(json.dumps({"sessionId":"debug-session","runId":"run_dev","hypothesisId":"H1","location":"run_dev.py:entry","message":"run_dev __main__ entered","data":{"cwd":__import__("os").getcwd()},"timestamp":int(time.time()*1000)}) + "\n")
    except Exception:
        pass
    # #endregion
    # Note: We use string format "server:app" because uvicorn needs to import the module
    # itself when using reload=True. This allows uvicorn to properly track the module
    # for file changes. Passing app object directly breaks reload mechanism.
    try:
        # #region agent log
        try:
            with open(r"c:\Users\MeMyself\creditnexus\.cursor\debug.log", "a") as f:
                f.write(json.dumps({"sessionId":"debug-session","runId":"run_dev","hypothesisId":"H2","location":"run_dev.py:before_uvicorn","message":"about to uvicorn.run(server:app)","data":{},"timestamp":int(time.time()*1000)}) + "\n")
        except Exception:
            pass
        # #endregion
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
        # #region agent log
        try:
            with open(r"c:\Users\MeMyself\creditnexus\.cursor\debug.log", "a") as f:
                f.write(json.dumps({"sessionId":"debug-session","runId":"run_dev","hypothesisId":"H3","location":"run_dev.py:except","message":"uvicorn exception","data":{"error":str(e),"type":type(e).__name__},"timestamp":int(time.time()*1000)}) + "\n")
        except Exception:
            pass
        # #endregion
        print(f"ERROR: Failed to start uvicorn: {e}", flush=True)
        traceback.print_exc()
        sys.exit(1)
