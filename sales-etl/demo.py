"""One-command demo: start the mock marketplace API, then run the pipeline for October 2026."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from scripts import mock_api  # noqa: E402
from etl.pipeline import run  # noqa: E402

srv = mock_api.start()
try:
    r = run("2026-10")
finally:
    srv.shutdown()
print(f"\nDone: {r['loaded']} sales lines loaded, {r['rejected']} rows set aside, {r['alerts']} stock alerts.")
print(f"Excel report: {r['excel']}\nEmail summary: {r['html']}")
