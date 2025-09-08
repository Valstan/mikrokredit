from __future__ import annotations
import webbrowser
from threading import Timer
from web import create_app


def open_browser():
    webbrowser.open("http://127.0.0.1:5000/")


def main() -> int:
    app = create_app()
    Timer(0.5, open_browser).start()
    app.run(host="127.0.0.1", port=5000, debug=False)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
