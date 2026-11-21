import os
import sys
import subprocess
import time

def main():
    print("================================================================")
    print("MEETME — AI Meeting Intelligence & Autonomous Execution Platform")
    print("Philosophy: MEETINGS IN. EXECUTION OUT.")
    print("================================================================")

    # 1. Start backend
    backend_env = os.environ.copy()
    backend_env["PYTHONPATH"] = "."
    
    python_exe = sys.executable
    if os.path.exists(os.path.join("venv", "Scripts", "python.exe")):
        python_exe = os.path.abspath(os.path.join("venv", "Scripts", "python.exe"))

    print("\n[1/2] Launching FastAPI Backend on http://127.0.0.1:8000...")
    backend_cmd = [python_exe, "-m", "uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
    backend_proc = subprocess.Popen(backend_cmd, env=backend_env)

    time.sleep(3)

    print("\n[2/2] Launching Next.js Frontend on http://127.0.0.1:3000...")
    frontend_dir = os.path.abspath("frontend")
    
    # Run npm run dev or npm start
    npm_cmd = "npm.cmd" if sys.platform == "win32" else "npm"
    frontend_proc = subprocess.Popen([npm_cmd, "run", "dev"], cwd=frontend_dir)

    print("\nMEETME is running!")
    print("Frontend UI:   http://localhost:3000")
    print("Backend API:   http://127.0.0.1:8000")
    print("API Docs:      http://127.0.0.1:8000/docs")
    print("\nPress Ctrl+C to terminate both servers.")

    try:
        backend_proc.wait()
        frontend_proc.wait()
    except KeyboardInterrupt:
        print("\nStopping MEETME...")
        backend_proc.terminate()
        frontend_proc.terminate()

if __name__ == "__main__":
    main()
