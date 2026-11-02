"""Start the PureSpace website.

    python run.py            production-style server (Waitress) on http://127.0.0.1:8000
    python run.py --dev      Flask development server with auto-reload (never use on a live site)

Settings come from environment variables (see .env.example).
"""
from __future__ import annotations

import argparse
import os
import sys

from purespace import create_app


def main() -> None:
    ap = argparse.ArgumentParser(description="Run the PureSpace website")
    ap.add_argument("--host", default=os.environ.get("PURESPACE_HOST", "127.0.0.1"))
    ap.add_argument("--port", type=int, default=int(os.environ.get("PURESPACE_PORT", "8000")))
    ap.add_argument("--dev", action="store_true", help="development server with reload and debugger")
    args = ap.parse_args()

    app = create_app()
    if args.dev:
        app.run(host=args.host, port=args.port, debug=True)
        return
    try:
        from waitress import serve
    except ImportError:
        sys.exit("Waitress is not installed. Run:  pip install -r requirements.txt\n"
                 "(or use  python run.py --dev  for local testing only)")
    print(f"PureSpace running on http://{args.host}:{args.port}  (Ctrl+C to stop)")
    serve(app, host=args.host, port=args.port, threads=8)


if __name__ == "__main__":
    main()
