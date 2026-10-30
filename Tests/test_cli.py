"""Tests for the user commands msub (Msub.py), mstat (Mstat.py) and
mdel (Mdel.py), run as subprocesses against a sandbox installation."""

import json
import os
import pwd
import re

import pytest

import Mutil
from conftest import job

ME = pwd.getpwuid(os.getuid()).pw_name


def submitted(box):
    """The single subjob file written by msub, as (id, job)."""
    files = box.pending("subjob")
    assert len(files) == 1, files
    data = json.loads(files[0].read_text())
    assert len(data) == 1
    jobid, entry = next(iter(data.items()))
    assert files[0].name == f"subjob{jobid}.mns"
    return jobid, entry


def delete_request(box):
    files = box.pending("remove")
    assert len(files) == 1, files
    data = json.loads(files[0].read_text())
    assert len(data) == 1
    return next(iter(data.values()))


# ---------------------------------------------------------------------------
# msub
# ---------------------------------------------------------------------------

def test_msub_writes_a_submission(sandbox):
    result = sandbox.run("Msub", "-f", "/jobs/a.sh", "-c", 2, "-m", 300,
                         "-p", 70)
    assert result.returncode == 0, result.stderr
    _, entry = submitted(sandbox)
    assert entry["script"] == "/jobs/a.sh"
    assert entry["Ncpu"] == 2
    assert entry["RAM"] == 300
    assert entry["priority"] == 70
    assert entry["status"] == "que"
    assert entry["chain"] == "none"
    assert entry["user"] == ME
    assert re.fullmatch(r"\d\d/\d\d/\d\d \d\d\.\d\d\.\d\d", entry["subtime"])


def test_msub_applies_defaults(sandbox):
    sandbox.run("Msub", "-f", "/jobs/a.sh")
    _, entry = submitted(sandbox)
    defaults = sandbox.read("defaults")
    assert entry["Ncpu"] == defaults["Ncpu"]
    assert entry["RAM"] == defaults["RAM"]
    assert entry["priority"] == defaults["priority"]


def test_msub_rejects_non_integer_resources(sandbox):
    result = sandbox.run("Msub", "-f", "/jobs/a.sh", "-c", "two")
    assert result.returncode != 0
    assert sandbox.pending("subjob") == []


@pytest.mark.parametrize("field", [
    "Ncpu", "RAM", "priority", "status", "script", "user", "subtime",
    "runtime", "pid", "HDmemory", "id",
])
def test_msub_sets_fields_read_by_the_daemon(sandbox, field):
    sandbox.run("Msub", "-f", "/jobs/a.sh")
    _, entry = submitted(sandbox)
    assert field in entry


def test_msub_job_can_be_scheduled(sandbox):
    sandbox.run("Msub", "-f", "/jobs/a.sh", "-c", 1, "-m", 100)
    jobid, entry = submitted(sandbox)
    queue = {jobid: entry}
    available = Mutil.find_available_resources(sandbox.read("status"),
                                               sandbox.read("nodes"))
    assert Mutil.check_for_submissions(
        available, Mutil.sortbypriority(queue), queue) == [jobid]


def test_msub_requires_a_script(sandbox):
    result = sandbox.run("Msub", "-c", 1)
    assert result.returncode != 0
    assert sandbox.pending("subjob") == []


def test_msub_stores_absolute_script_path(sandbox):
    sandbox.run("Msub", "-f", "job.sh")
    _, entry = submitted(sandbox)
    assert entry["script"] == os.path.abspath("job.sh")


def test_msub_ignores_user_environment(sandbox):
    env = {**os.environ, "LOGNAME": "someoneelse", "USER": "someoneelse"}
    sandbox.run("Msub", "-f", "/jobs/a.sh", env=env)
    _, entry = submitted(sandbox)
    assert entry["user"] == ME


@pytest.mark.xfail(reason="DESIGN: a request larger than the node is "
                          "accepted and stays queued forever")
def test_msub_rejects_requests_larger_than_the_node(sandbox):
    result = sandbox.run("Msub", "-f", "/jobs/a.sh", "-c", 99)
    assert result.returncode != 0
    assert sandbox.pending("subjob") == []


# ---------------------------------------------------------------------------
# mstat
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("flags", [[], ["-v"]])
def test_mstat_on_idle_system(sandbox, flags):
    result = sandbox.run("Mstat", *flags)
    assert result.returncode == 0, result.stderr
    assert "System free: no job queued or running" in result.stdout


def test_mstat_lists_jobs(sandbox):
    sandbox.write("charge", {
        "11": job(user="alice", Ncpu=2, RAM=300, priority=70),
        "22": job(user="bob", status="run", pid=4321)})
    result = sandbox.run("Mstat")
    assert result.returncode == 0, result.stderr
    rows = [line.split() for line in result.stdout.splitlines()]
    assert ["alice", "2", "300", "11", "que", "70"] in rows
    assert ["bob", "1", "100", "22", "run", "50"] in rows


def test_mstat_verbose_shows_details(sandbox):
    sandbox.write("charge", {
        "11": job(script="/jobs/a.sh"),
        "22": job(status="run", pid=4321, runtime="01/01/26 00.01.00")})
    result = sandbox.run("Mstat", "-v")
    assert result.returncode == 0, result.stderr
    out = result.stdout
    assert "script: /jobs/a.sh" in out
    assert "pid: 4321" in out
    assert "runtime: 01/01/26 00.01.00" in out
    assert "pid: -" in out


def test_mstat_verbose_with_a_submitted_job(sandbox):
    sandbox.run("Msub", "-f", "/jobs/a.sh")
    jobid, entry = submitted(sandbox)
    sandbox.write("charge", {jobid: entry})
    result = sandbox.run("Mstat", "-v")
    assert result.returncode == 0, result.stderr
    assert f"{jobid}:" in result.stdout


# ---------------------------------------------------------------------------
# mdel
# ---------------------------------------------------------------------------

def test_mdel_without_daemon_does_nothing(sandbox):
    result = sandbox.run("Mdel", "-j", 42)
    assert "no minosse demon running!" in result.stdout
    assert sandbox.pending("remove") == []


def test_mdel_by_id(sandbox, fake_daemon):
    result = sandbox.run("Mdel", "-j", 42)
    assert result.returncode == 0, result.stderr
    request = delete_request(sandbox)
    # charge.mns keys are strings
    assert request == {"id": "42", "script": None, "all": False, "user": ME}


def test_mdel_rejects_non_integer_id(sandbox, fake_daemon):
    result = sandbox.run("Mdel", "-j", "abc")
    assert result.returncode != 0
    assert sandbox.pending("remove") == []


def test_mdel_by_script(sandbox, fake_daemon):
    result = sandbox.run("Mdel", "-s", "job.sh")
    assert result.returncode == 0, result.stderr
    request = delete_request(sandbox)
    # msub stores absolute paths
    assert request["script"] == os.path.abspath("job.sh")
    assert request["id"] is None


def test_mdel_requires_a_target(sandbox, fake_daemon):
    result = sandbox.run("Mdel")
    assert result.returncode != 0
    assert "Traceback" not in result.stderr, "should be a usage error"
    assert sandbox.pending("remove") == []
