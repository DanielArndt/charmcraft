# Copyright 2021 Canonical Ltd.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# For further info, check https://github.com/canonical/charmcraft

import logging
import pathlib
from unittest import mock

import pytest

from charmcraft import providers


@pytest.fixture()
def mock_mkstemp():
    with mock.patch("charmcraft.providers._logs.tempfile.mkstemp") as mock_mkstemp:
        yield mock_mkstemp


def test_capture_logs_from_instance(mock_instance, caplog, mock_mkstemp, tmp_path):
    caplog.set_level(logging.DEBUG, logger="charmcraft")

    fake_log = tmp_path / "x.log"
    mock_mkstemp.return_value = (None, str(fake_log))

    fake_log_data = "some\nlog data\nhere"
    fake_log.write_text(fake_log_data)

    providers.capture_logs_from_instance(mock_instance)

    assert mock_instance.mock_calls == [
        mock.call.pull_file(source=pathlib.Path("/tmp/charmcraft.log"), destination=fake_log),
    ]
    expected = [
        "Logs captured from managed instance:",
        ":: some",
        ":: log data",
        ":: here",
    ]
    assert expected == [rec.message for rec in caplog.records]


def test_capture_logs_from_instance_not_found(mock_instance, caplog, mock_mkstemp, tmp_path):
    caplog.set_level(logging.DEBUG, logger="charmcraft")

    fake_log = tmp_path / "x.log"
    mock_mkstemp.return_value = (None, str(fake_log))
    mock_instance.pull_file.side_effect = FileNotFoundError()

    providers.capture_logs_from_instance(mock_instance)

    assert mock_instance.mock_calls == [
        mock.call.pull_file(source=pathlib.Path("/tmp/charmcraft.log"), destination=fake_log),
    ]
    assert ["No logs found in instance."] == [rec.message for rec in caplog.records]