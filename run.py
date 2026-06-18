"""
ONE-COMMAND LAUNCHER
====================
Runs the entire app (backend + frontend) with a single command:

    python run.py

What it does:
  1. Checks/installs Python dependencies
  2. Builds Flutter web (first run only, if Flutter installed)
  3. Starts the all-in-one server at http://localhost:8000
  4. Opens your browser

If Flutter isn't installed, the backend still runs and you can use
`flutter run -d chrome` separately for the UI.
"""

import os
import sys
import subprocess
import time
import webbrowser
from pathlib import Path

ROOT = Path(__file__).parent
BACKEND = ROOT / "backend"
FLUTTER = ROOT / "flutter_app"
WEB_BUILD = FLUTTER / "build" / "web"


def run(cmd, cwd=None, check=True):
    print(f"  $ {cmd}")
    return subprocess.run(cmd, shell=True, cwd=cwd, check=check)


def has_command(cmd):
    from shutil import which
    return which(cmd) is not None


def main():
    print("\n" + "=" * 55)
    print("  NIFTY AI BOT — One-command launcher")
    print("=" * 55 + "\n")

    # 1. Python deps
    venv_py = BACKEND / "venv" / ("Scripts" if os.name == "nt" else "bin") / "python"
    if not venv_py.exists():
        print("[1/3] Creating virtual environment + installing deps...")
        run(f'"{sys.executable}" -m venv venv', cwd=BACKEND)
        pip = BACKEND / "venv" / ("Scripts" if os.name == "nt" else "bin") / "pip"
        run(f'"{pip}" install -r requirements.txt', cwd=BACKEND)
    else:
        print("[1/3] Dependencies already installed ✓")

    # 2. Build Flutter web (so backend can serve it = one process)
    if not WEB_BUILD.exists():
        if has_command("flutter"):
            print("[2/3] Building Flutter web (first run, ~2 min)...")
            run("flutter pub get", cwd=FLUTTER)
            run("flutter build web", cwd=FLUTTER)
        else:
            print("[2/3] Flutter not found — backend will run without bundled UI.")
            print("      Install Flutter, or run 'flutter run -d chrome' separately.")
    else:
        print("[2/3] Flutter web already built ✓")

    # 3. Start server + open browser
    print("[3/3] Starting server at http://localhost:8000\n")
    py = str(venv_py)

    # Open browser after delay
    def open_browser():
        time.sleep(4)
        webbrowser.open("http://localhost:8000")
    import threading
    threading.Thread(target=open_browser, daemon=True).start()

    # Run server (blocks)
    subprocess.run(f'"{py}" main.py', shell=True, cwd=BACKEND)


if __name__ == "__main__":
    main()
