import sys
import subprocess
import shutil
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent
ENTRY = PROJECT_ROOT / "app" / "main.py"
NAME = "MikroKredit"


def main() -> int:
    if not ENTRY.exists():
        print(f"Entry not found: {ENTRY}")
        return 1

    # Clean old build artifacts
    for d in (PROJECT_ROOT / "build", PROJECT_ROOT / "dist"):
        if d.exists():
            shutil.rmtree(d)

    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--clean",
        "--onefile",
        "--windowed",
        f"--name={NAME}",
        str(ENTRY),
    ]
    print("Running:", " ".join(cmd))
    return subprocess.call(cmd)


if __name__ == "__main__":
    raise SystemExit(main())
