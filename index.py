import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from az_job_radar.app import create_app  # noqa: E402
from az_job_radar.gate import PreviewGate  # noqa: E402

app = create_app(preview_gate=PreviewGate.from_env())
