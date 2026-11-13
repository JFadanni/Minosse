"""Tests for the user commands msub (Msub.py), mstat (Mstat.py) and
mdel (Mdel.py), run as subprocesses against a sandbox installation."""

import json
import os
import pwd
import re

import pytest

import Mutil
from conftest import job, needs_server

ME = pwd.getpwuid(os.getuid()).pw_name


def request(box, prefix):
    """The single request file written by msub or mdel."""
    files = box.pending(prefix)
    assert len(files) == 1, files
    assert re.fullmatch(rf"{prefix}\d+_\d+\.mns", files[0].name)
    return json.loads(files[0].read_text())


def submitted(box):
    return request(box, "subjob")


def delete_request(box):
    return request(box, "remove")


# ---------------------------------------------------------------------------
# msub
# ---------------------------------------------------------------------------

def test_msub_writes_a_submission(sandbox):
    result = sandbox.run("Msub", "-f", "/jobs/a.sh", "-c", 2, "-m", 300,
                         "-p", 70)
    assert result.returncode == 0, result.stderr
    assert "Job /jobs/a.sh submitted" in result.stdout
    entry = submitted(sandbox)
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
    entry = submitted(sandbox)
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
    "runtime", "pid", "HDmemory",
])
def test_msub_sets_fields_read_by_the_daemon(sandbox, field):
    sandbox.run("Msub", "-f", "/jobs/a.sh")
    entry = submitted(sandbox)
    assert field in entry


def test_msub_job_can_be_scheduled(sandbox):
    sandbox.run("Msub", "-f", "/jobs/a.sh", "-c", 1, "-m", 100)
    entry = submitted(sandbox)
    assert Mutil.invalidjob(entry, sandbox.read("nodes")) is None
    queue = {"1": entry}
    available = Mutil.find_available_resources(sandbox.read("status"),
                                               sandbox.read("nodes"))
    assert Mutil.check_for_submissions(
        available, Mutil.sortbypriority(queue), queue) == ["1"]


def test_msub_requires_a_script(sandbox):
    result = sandbox.run("Msub", "-c", 1)
    assert result.returncode != 0
    assert sandbox.pending("subjob") == []


def test_msub_stores_absolute_script_path(sandbox):
    sandbox.run("Msub", "-f", "job.sh")
    entry = submitted(sandbox)
    assert entry["script"] == os.path.abspath("job.sh")


@pytest.mark.parametrize("chain, stored", [
    ("none", "none"), ("/jobs/a.sh", "/jobs/a.sh"),
    ("a.sh", os.path.abspath("a.sh"))])
def test_msub_stores_the_chained_script(sandbox, chain, stored):
    sandbox.run("Msub", "-f", "/jobs/b.sh", "-l", chain)
    assert submitted(sandbox)["chain"] == stored


def test_msub_ignores_user_environment(sandbox):
    env = {**os.environ, "LOGNAME": "someoneelse", "USER": "someoneelse"}
    sandbox.run("Msub", "-f", "/jobs/a.sh", env=env)
    entry = submitted(sandbox)
    assert entry["user"] == ME


@pytest.mark.parametrize("args, error", [
    (["-c", 99], "Ncpu 99 exceeds the node (4)"),
    (["-m", 5000], "RAM 5000 exceeds the node (1000)"),
    (["-c", 0], "at least one cpu is needed"),
    (["-m", -5], "RAM must not be negative"),
])
def test_msub_rejects_jobs_that_can_never_run(sandbox, args, error):
    result = sandbox.run("Msub", "-f", "/jobs/a.sh", *args)
    assert result.returncode != 0
    assert error in result.stderr
    assert "Traceback" not in result.stderr
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
    entry = submitted(sandbox)
    sandbox.write("charge", {"1": {**entry, "id": "1"}})
    result = sandbox.run("Mstat", "-v")
    assert result.returncode == 0, result.stderr
    assert "1:" in result.stdout


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
    assert request == {"id": ["42"], "script": None, "all": False,
                       "user": ME, "alljobs": False, "flush": False}


def test_mdel_by_several_ids_and_ranges(sandbox, fake_daemon):
    result = sandbox.run("Mdel", "-j", 3, 4, "7-10")
    assert result.returncode == 0, result.stderr
    assert delete_request(sandbox)["id"] == ["3", "4", "7-10"]


@pytest.mark.parametrize("ids, error", [
    (["abc"], "abc is not a job id or a range of ids"),
    (["3", "x"], "x is not a job id"),
    (["7-"], "7- is not a job id"),
    (["-3"], "-3 is not a job id"),
    (["10-7"], "the range 10-7 is reversed"),
])
def test_mdel_rejects_malformed_ids(sandbox, fake_daemon, ids, error):
    result = sandbox.run("Mdel", "-j", *ids)
    assert result.returncode != 0
    assert error in result.stderr
    assert "Traceback" not in result.stderr
    assert sandbox.pending("remove") == []


def test_mdel_all_jobs(sandbox, fake_daemon):
    result = sandbox.run("Mdel", "--all-jobs")
    assert result.returncode == 0, result.stderr
    request = delete_request(sandbox)
    assert request["alljobs"] is True
    assert (request["id"], request["script"], request["flush"]) == (
        None, None, False)


@pytest.mark.parametrize("args", [
    ["-j", 1, "-s", "job.sh"], ["-j", 1, "--all-jobs"],
    ["-s", "job.sh", "--flush"], ["--all-jobs", "--flush"]])
def test_mdel_takes_one_target(sandbox, fake_daemon, args):
    result = sandbox.run("Mdel", *args)
    assert result.returncode != 0
    assert "not allowed with" in result.stderr
    assert sandbox.pending("remove") == []


@needs_server
def test_mdel_flush_by_root(sandbox, fake_daemon):
    result = sandbox.run("Mdel", "--flush")
    assert result.returncode == 0, result.stderr
    request = delete_request(sandbox)
    assert request["flush"] is True
    assert request["user"] == "root"


@needs_server
def test_mdel_flush_is_for_root_only(sandbox, fake_daemon):
    result = sandbox.run("Mdel", "--flush", user="alice")
    assert result.returncode != 0
    assert "only root can delete the jobs of everybody" in result.stderr
    assert sandbox.pending("remove") == []


def test_mdel_by_script(sandbox, fake_daemon):
    result = sandbox.run("Mdel", "-s", "job.sh")
    assert result.returncode == 0, result.stderr
    request = delete_request(sandbox)
    # msub stores absolute paths
    assert request["script"] == os.path.abspath("job.sh")
    assert request["id"] is None
    assert request["alljobs"] is False


def test_mdel_requires_a_target(sandbox, fake_daemon):
    result = sandbox.run("Mdel")
    assert result.returncode != 0
    assert "Traceback" not in result.stderr, "should be a usage error"
    assert sandbox.pending("remove") == []
