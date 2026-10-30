"""The version is kept in the VERSION file only: everything that shows it
must agree with it."""

import re
import subprocess

import pytest

import Mutil
from conftest import SRC

VERSION = (SRC / "VERSION").read_text().strip()

# https://semver.org/#is-there-a-suggested-regular-expression-regex-to-check-a-semver-string
SEMVER = (r"(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)"
          r"(?:-((?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*)"
          r"(?:\.(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*))*))?"
          r"(?:\+([0-9a-zA-Z-]+(?:\.[0-9a-zA-Z-]+)*))?")


def test_version_is_semantic():
    assert re.fullmatch(SEMVER, VERSION)


def test_mutil_reads_the_version():
    assert Mutil.__version__ == VERSION


def test_changelog_documents_the_version():
    changelog = (SRC / "CHANGELOG.md").read_text()
    releases = re.findall(r"^## \[(.+?)\]", changelog, flags=re.M)
    assert releases[0] == VERSION
    assert re.search(rf"^## \[{re.escape(VERSION)}\] - \d{{4}}-\d\d-\d\d$",
                     changelog, flags=re.M)
    assert f"[{VERSION}]: https://github.com/" in changelog


@pytest.mark.parametrize("tool", ["Msub", "Mstat", "Mdel"])
def test_commands_show_the_version(sandbox, tool):
    result = sandbox.run(tool, "--version")
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == f"{tool}.py {VERSION}"


def test_mstat_shows_the_version(sandbox):
    assert f"Minosse batch system {VERSION}" in sandbox.run("Mstat").stdout


def test_daemon_shows_the_version(sandbox):
    result = sandbox.run("Minosse", "--version")
    assert result.stdout.strip() == f"Minosse.py {VERSION}"


def test_mutil_without_version_file(tmp_path):
    # An installation without VERSION still runs.
    (tmp_path / "Mutil.py").write_text((SRC / "Utils" / "Mutil.py").read_text())
    result = subprocess.run(
        ["python3", "-c", "import Mutil; print(Mutil.__version__)"],
        cwd=tmp_path, capture_output=True, text=True)
    assert result.stdout.strip() == "unknown"
