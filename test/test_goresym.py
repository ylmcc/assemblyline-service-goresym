"""End-to-end TestHelper-based test. The vendored GoReSym binary is never actually
invoked here -- subprocess.run is mocked to return a canned, schema-accurate payload
(see test/unit/fixtures.py), so the sample fixture's own bytes are just an arbitrary
placeholder, never real (or real-shaped) executable content.
"""
import json
import os
import subprocess
from unittest.mock import patch

import pytest
from assemblyline.common.importing import load_module_by_path
from assemblyline_service_utilities.testing.helper import TestHelper

from test.unit.fixtures import SUCCESS_PAYLOAD

os.environ["SERVICE_MANIFEST_PATH"] = os.path.join(os.path.dirname(__file__), "..", "service_manifest.yml")

RESULTS_FOLDER = os.path.join(os.path.dirname(__file__), "results")
SAMPLES_FOLDER = os.path.join(os.path.dirname(__file__), "samples")

service_class = load_module_by_path(
    "goresym_service.goresym_service.GoReSym", os.path.join(os.path.dirname(__file__), "..")
)
th = TestHelper(service_class, RESULTS_FOLDER, SAMPLES_FOLDER)


def _fake_run(cmd, **kwargs):
    return subprocess.CompletedProcess(args=cmd, returncode=0, stdout=json.dumps(SUCCESS_PAYLOAD), stderr="")


@pytest.mark.parametrize("sample", th.result_list())
@patch("goresym_service.runner.subprocess.run", side_effect=_fake_run)
def test_sample(mock_run, sample):
    th.run_test_comparison(sample)
