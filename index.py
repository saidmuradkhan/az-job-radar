import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from az_job_radar.app import create_app_from_env  # noqa: E402

app = create_app_from_env()
