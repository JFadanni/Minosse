"""Tests of minosse_config.sh, minosse_install.sh and minosse_uninst.sh on
the simulated server, answering their prompts through stdin."""

import json
import os
import shutil
import stat
import subprocess
import tempfile
import time
from pathlib import Path

import pytest

from conftest import SRC, needs_server, wait_until

pytestmark = [
    needs_server,
    pytest.mark.skipif(not os.path.ismount("/scratch"),
                       reason="needs /scratch mounted as the work partition"),
]

SYSMEM = 300
MNS = ("charge", "conf", "delete", "defaults", "nodes", "status")


def run_script(cwd, script, answers):
    return subprocess.run(["bash", script], cwd=cwd, input=answers,
                          capture_output=True, text=True, timeout=60)


@pytest.fixture
def source(tmp_path):
    """A writable copy of the sources: the scripts create Tmp/ in place."""
    copy = tmp_path / "src"
    shutil.copytree(SRC, copy, ignore=shutil.ignore_patterns(".git", "Tests"))
    return copy


@pytest.fixture
def configured(source):
    result = run_script(source, "minosse_config.sh",
                        f"/scratch\n{SYSMEM}\n50\ny\n")
    assert result.returncode == 0, result.stdout + result.stderr
    return source


@pytest.fixture
def installed(configured):
    # Outside tmp_path, whose parents users cannot traverse.
    root = Path(tempfile.mkdtemp(prefix="minosse-install-"))
    os.chmod(root, 0o755)
    instdir = root / "Minosse"
    linkdir = root / "bin"
    linkdir.mkdir()
    result = run_script(configured, "minosse_install.sh",
                        f"{instdir}\ny\n{linkdir}\nn\n")
    assert "INSTALLATION COMPLETE" in result.stdout, \
        result.stdout + result.stderr
    yield instdir, linkdir
    subprocess.run(["pkill", "-KILL", "-f", str(instdir)])
    shutil.rmtree(root, ignore_errors=True)


def read_mns(path):
    return json.loads(path.read_text())


def test_config_describes_this_machine(configured):
    tmp = configured / "Tmp"
    for name in MNS:
        read_mns(tmp / f"{name}.mns")
    node = read_mns(tmp / "nodes.mns")
    with open("/proc/meminfo") as meminfo:
        total_mb = int(meminfo.readline().split()[1]) // 1024
    assert node["Ncpu"] == os.cpu_count()
    assert node["RAM"] == total_mb - SYSMEM
    assert node["HDmemory"] == shutil.disk_usage("/scratch").total // 2**30
    assert node["HDmemory"] > 0
    assert node["hostname"] == os.uname().nodename
    assert read_mns(tmp / "conf.mns") == {"status": "down"}
    assert read_mns(tmp / "charge.mns") == {}
    defaults = read_mns(tmp / "defaults.mns")
    assert (defaults["Ncpu"], defaults["status"]) == (1, "que")


def test_config_accepts_a_directory_inside_a_partition(source):
    os.makedirs("/scratch/minosse", exist_ok=True)
    result = run_script(source, "minosse_config.sh",
                        f"/scratch/minosse\n{SYSMEM}\n50\ny\n")
    assert "INSTALLATION ABORT" not in result.stdout, result.stdout
    node = read_mns(source / "Tmp" / "nodes.mns")
    assert node["HDmemory"] == shutil.disk_usage("/scratch").total // 2**30


def test_config_aborts_on_unknown_partition(source):
    result = run_script(source, "minosse_config.sh", "/no/such/partition\n")
    assert "INSTALLATION ABORT" in result.stdout
    assert not any((source / "Tmp").glob("*.mns"))


def test_install_requires_root(configured, tmp_path):
    result = subprocess.run(["bash", "minosse_install.sh"], cwd=configured,
                            input=f"{tmp_path}/x\ny\n", text=True,
                            capture_output=True, env={**os.environ,
                                                      "USER": "alice"})
    assert "Permission denied" in result.stdout
    assert not (tmp_path / "x").exists()


def test_install_lays_out_the_files(installed, configured):
    instdir, linkdir = installed
    for name in MNS:
        read_mns(instdir / f"{name}.mns")
    for name in ("Minosse.py", "Msub.py", "Mstat.py", "Mdel.py", "Mutil.py",
                 "minosse", "minosse_uninst.sh", "README.md", "COPYING",
                 "VERSION"):
        assert (instdir / name).is_file(), name
    assert not (configured / "Tmp").exists()

    for name in ("Minosse.py", "Msub.py", "Mstat.py", "Mdel.py", "minosse",
                 "minosse_uninst.sh"):
        text = (instdir / name).read_text()
        assert "$instdir" not in text, name
        assert str(instdir) in text, name
    assert "$linkdir" not in (instdir / "minosse_uninst.sh").read_text()

    for tool in ("Msub.py", "Mstat.py", "Mdel.py"):
        assert os.stat(instdir / tool).st_mode & stat.S_IXOTH, tool
    assert stat.S_IMODE(os.stat(instdir).st_mode) == 0o755
    assert stat.S_IMODE(os.stat(instdir / "requests").st_mode) == 0o1777
    for name in MNS:
        assert not os.stat(instdir / f"{name}.mns").st_mode & stat.S_IWOTH

    links = {"minosse": "minosse", "msub": "Msub.py", "mdel": "Mdel.py",
             "mstat": "Mstat.py", "minosse_uninst": "minosse_uninst.sh"}
    for link, target in links.items():
        assert os.readlink(linkdir / link) == f"{instdir}/{target}"


def as_alice(*cmd):
    return subprocess.run(["runuser", "-u", "alice", "--", *map(str, cmd)],
                          capture_output=True, text=True)


def test_minosse_version(installed, configured):
    instdir, linkdir = installed
    version = (configured / "VERSION").read_text().strip()
    assert minosse(linkdir, "version").stdout.strip() == f"Minosse {version}"
    result = run_script(configured, "minosse_config.sh", "/no/such/dir\n")
    assert f"Minosse version {version}" in result.stdout


def test_installed_commands_work_for_users(installed):
    instdir, linkdir = installed
    result = as_alice(f"{linkdir}/mstat")
    assert "System free" in result.stdout, result.stderr
    result = as_alice(f"{linkdir}/msub", "-f", "/bin/true")
    assert result.returncode == 0, result.stderr
    [request] = (instdir / "requests").glob("subjob*.mns")
    entry = read_mns(request)
    assert entry["user"] == "alice"


def test_users_cannot_plant_code_or_replace_files(installed):
    instdir, _ = installed
    # Python imports from the directory of the scripts the daemon runs.
    assert as_alice("touch", instdir / "json.py").returncode != 0
    assert as_alice("mv", instdir / "charge.mns",
                    instdir / "requests").returncode != 0
    # Requests of other users are protected by the sticky bit.
    request = instdir / "requests" / "subjob1.mns"
    subprocess.run(["runuser", "-u", "bob", "--", "touch", request],
                   check=True)
    assert as_alice("rm", "-f", request).returncode != 0
    assert request.exists()


def user_job(instdir):
    """A job script that records who ran it, and its marker file."""
    job = instdir.parent / "job.sh"
    marker = instdir.parent / "job.out"
    job.write_text(f"#!/bin/bash\nid -un > {marker}\n")
    os.chmod(job, 0o755)
    os.chmod(instdir.parent, 0o777)
    return job, marker


def daemon_running(instdir):
    return subprocess.run(["pgrep", "-f", f"{instdir}/Minosse.py"],
                          capture_output=True).returncode == 0


def minosse(linkdir, *args, answers=""):
    return subprocess.run([f"{linkdir}/minosse", *args], input=answers,
                          capture_output=True, text=True, timeout=30)


def test_minosse_start_and_stop(installed):
    instdir, linkdir = installed
    result = minosse(linkdir, "start")
    assert "Minosse demon started" in result.stdout
    # Nothing is pending, so there is nothing to ask.
    assert "Keep them?" not in result.stdout
    time.sleep(2)
    assert daemon_running(instdir), "daemon is not running"

    job, marker = user_job(instdir)
    assert as_alice(f"{linkdir}/msub", "-f", job).returncode == 0
    assert wait_until(marker.exists)
    assert marker.read_text().strip() == "alice"

    minosse(linkdir, "stop")
    assert wait_until(lambda: not daemon_running(instdir))
    assert read_mns(instdir / "conf.mns") == {"status": "down"}


@pytest.mark.parametrize("flag, answers, kept", [
    (None, "\n", True),         # the default answer keeps them
    (None, "yes\n", True),
    (None, "no\n", False),
    (None, "", True),           # no terminal to answer: keep them
    ("--keep", "", True),
    ("--delete", "", False),
])
def test_minosse_start_asks_about_pending_jobs(installed, flag, answers,
                                               kept):
    instdir, linkdir = installed
    job, marker = user_job(instdir)
    # Submitted while the daemon is down.
    assert as_alice(f"{linkdir}/msub", "-f", job).returncode == 0
    result = minosse(linkdir, "start", *filter(None, [flag]), answers=answers)
    try:
        assert "Jobs still waiting from the last run:" in result.stdout
        assert f"alice\t{job}" in result.stdout
        assert ("Keep them? [Yes/no]" in result.stdout) == (flag is None)
        if kept:
            assert "Pending jobs kept" in result.stdout
            assert wait_until(marker.exists)
        else:
            assert "Pending jobs deleted" in result.stdout
            time.sleep(2)
            assert not marker.exists()
            assert list((instdir / "requests").iterdir()) == []
    finally:
        minosse(linkdir, "stop")


def test_uninstall_stops_the_daemon(installed):
    instdir, linkdir = installed
    minosse(linkdir, "start")
    assert wait_until(lambda: daemon_running(instdir))
    # As root usually runs it, with the links directory not in PATH.
    result = subprocess.run(["bash", f"{instdir}/minosse_uninst.sh"],
                            input="yes\n", capture_output=True, text=True,
                            env={**os.environ, "PATH": "/usr/bin:/bin"})
    assert "Minosse demon stopped" in result.stdout, result.stderr
    assert "Minosse uninstalled" in result.stdout
    assert wait_until(lambda: not daemon_running(instdir))


def test_uninstall_removes_everything(installed):
    instdir, linkdir = installed
    result = subprocess.run(["bash", f"{instdir}/minosse_uninst.sh"],
                            input="yes\n", capture_output=True, text=True)
    assert "Minosse uninstalled" in result.stdout, result.stderr
    assert not instdir.exists()
    assert list(linkdir.iterdir()) == []
