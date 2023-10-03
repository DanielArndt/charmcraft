# Copyright 2023 Canonical Ltd.
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
import pathlib
import tempfile

import pytest

from charmcraft.utils.package import (
    exclude_packages,
    get_package_names,
    get_pip_command,
    get_pip_version,
    get_pypi_packages,
)


@pytest.mark.parametrize(
    ("requirements", "expected"),
    [
        pytest.param([], set(), id="empty"),
        pytest.param(["abc==1.0.0"], {"abc==1.0.0"}, id="simple"),
        pytest.param(["-e ."], set(), id="editable-ignored"),
    ],
)
def test_get_pypi_packages(requirements, expected):
    assert get_pypi_packages(requirements) == expected


@pytest.mark.parametrize(
    ("packages", "expected"),
    [
        # Specifiers from pep440: https://peps.python.org/pep-0440/#version-specifiers
        pytest.param({"abc"}, {"abc"}, id="no-version"),
        pytest.param({"abc==1.0.0"}, {"abc"}, id="version-matching"),
        pytest.param({"abc >= 1.0.0"}, {"abc"}, id="inclusive-ordered-gt"),
        pytest.param({"abc<= 1.0.0"}, {"abc"}, id="inclusive-ordered-lt"),
        pytest.param({"abc ~= 1.0"}, {"abc"}, id="compatible-release"),
        pytest.param({"abc===foobar"}, {"abc"}, id="arbitrary-equality"),
        pytest.param({"abc >=1.0,<2.0, !=1.2.3.*"}, {"abc"}, id="compound-specifier"),
    ],
)
def test_get_package_names(packages, expected):
    assert get_package_names(packages) == expected


@pytest.mark.parametrize(
    ("requirements", "excluded", "expected"),
    [
        pytest.param(set(), set(), set(), id="empty"),
        pytest.param({"abc==1.0.0"}, {"abc"}, set(), id="make-empty"),
        pytest.param({"abc==1.0.0", "def==1.2.3"}, {"abc"}, {"def==1.2.3"}, id="remove-one"),
        pytest.param({"abc==1.0.0"}, {"invalid"}, {"abc==1.0.0"}, id="irrelevant-exclusion"),
    ],
)
def test_exclude_packages(requirements, excluded, expected):
    assert exclude_packages(requirements, excluded=excluded) == expected


@pytest.mark.parametrize(
    (
        "requirements",
        "source_deps",
        "binary_deps",
        "expected_no_binary",
        "expected_other_packages",
    ),
    [
        (["abc==1.0.0", "def>=1.2.3"], [], ["def"], "--no-binary=abc", []),
        (
            ["abc==1.0", "def>=1.2.3"],
            ["ghi"],
            ["def", "jkl"],
            "--no-binary=abc,ghi",
            ["ghi", "jkl"],
        ),
    ],
)
@pytest.mark.parametrize("prefix", [["/bin/pip"], ["/some/path/to/pip3"], ["pip", "--some-param"]])
def test_get_pip_command(
    prefix, requirements, source_deps, binary_deps, expected_no_binary, expected_other_packages
):
    with tempfile.TemporaryDirectory() as tmp_dir:
        path = pathlib.Path(tmp_dir, "requirements.txt")
        path.write_text("\n".join(requirements))

        command = get_pip_command(prefix, [path], source_deps=source_deps, binary_deps=binary_deps)
        assert command[: len(prefix)] == prefix
        actual_no_binary, actual_requirement, *actual_other_packgaes = command[len(prefix) :]
        assert actual_no_binary == expected_no_binary
        assert actual_other_packgaes == expected_other_packages
        assert actual_requirement == f"--requirement={path}"


@pytest.mark.parametrize(
    ("pip_cmd", "stdout", "expected"),
    [("pip", "pip 22.0.2 from /usr/lib/python3/dist-packages/pip (python 3.10)\n", (22, 0, 2))],
)
def test_get_pip_version_success(
    fake_process,
    pip_cmd,
    stdout,
    expected,
):
    fake_process.register([pip_cmd, "--version"], stdout=stdout)

    assert get_pip_version(pip_cmd) == expected


@pytest.mark.parametrize(
    ("pip_cmd", "stdout", "error_msg"),
    [
        ("pip", "pip?", "Unknown pip version"),
        ("pip", "pip 1.0.0-dev0-yolo", "Unknown pip version 1.0.0-dev0-yolo"),
    ],
)
def test_get_pip_version_parsing_failure(fake_process, pip_cmd, stdout, error_msg):
    fake_process.register([pip_cmd, "--version"], stdout=stdout)

    with pytest.raises(ValueError) as exc_info:
        get_pip_version(pip_cmd)

    assert exc_info.value.args[0] == error_msg
