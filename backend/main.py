import sys
import os

_current_dir = os.path.dirname(os.path.abspath(__file__))
_repo_root = os.path.dirname(_current_dir)
for _p in [_repo_root, _current_dir]:
    if _p and _p not in sys.path:
        sys.path.insert(0, _p)

from backend.app.main import app

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("backend.app.main:app", host="0.0.0.0", port=port)
