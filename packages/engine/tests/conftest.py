import copy
import json
from pathlib import Path

import pytest

SAMPLE = Path(__file__).resolve().parents[3] / "tests" / "reference" / "sample-terminal.json"


@pytest.fixture
def sample():
    """Fresh deep copy of the reference sample terminal document."""
    return copy.deepcopy(json.loads(SAMPLE.read_text(encoding="utf-8")))
