"""End-to-end tests of the Minosse.py daemon on the simulated server.

The daemon runs as root on a sandbox node with 4 CPUs, 1000 MB RAM and
10 GB of disk; jobs are submitted with msub as the unprivileged users
alice and bob.
"""

import subprocess
import sys
import time

import pytest

from conftest import Daemon, job, needs_server, process_alive, wait_until

pytestmark = needs_server


def msub(box, script, *args, user="alice"):
    result = box.run("Msub", "-f", script, *args, user=user)
    assert result.returncode == 0, result.stderr


def mdel(box, *args, user="alice"):
    return box.run("Mdel", *args, user=user)


def queued(box):
    return {i for i, j in box.read("charge").items() if j["status"] == "que"}


def picked_up(box):
    """All submissions have been read and none is still queued."""
    return not box.pending("subjob") and not queued(box)


# ---------------------------------------------------------------------------
# start-up
# ---------------------------------------------------------------------------

def test_daemon_initialises_the_node(sandbox):
    sandbox.write("status", {**sandbox.read("status"), "Ncpu": 3, "RAM": 50})
    daemon = Daemon(sandbox)
    try:
        daemon.wait_for(lambda: sandbox.read("conf") == {"status": "up"},
                        "conf.mns to be set to up")
    finally:
        daemon.stop()
    assert "---MINOSSE START---" in sandbox.messages()
    status = sandbox.read("status")
    assert (status["Ncpu"], status["RAM"], status["HDmemory"]) == (0, 0, 0)


def test_jobs_submitted_while_the_daemon_is_down_run_after_start(sandbox):
    msub(sandbox, sandbox.job_script("a"))
    daemon = Daemon(sandbox)
    try:
        daemon.wait_for(lambda: sandbox.started_by("a"), "job a to start")
    finally:
        daemon.stop()


def stop(box, daemon):
    """What "minosse stop" does."""
    subprocess.run(["sed", "-i", "s/up/stop/", box.path("conf")], check=True)
    assert wait_until(lambda: not daemon.alive(), timeout=10)


def test_queued_jobs_are_kept_across_a_restart(sandbox):
    daemon = Daemon(sandbox)
    try:
        msub(sandbox, sandbox.job_script("blocker", 30), "-c", 4)
        daemon.wait_for(lambda: sandbox.started_by("blocker"),
                        "blocker to start")
        script = sandbox.job_script("waiting")
        msub(sandbox, script, "-c", 4)
        jobid, _ = daemon.wait_for(lambda: sandbox.find_job(script),
                                   "the waiting job to be queued")
        stop(sandbox, daemon)
    finally:
        daemon.stop()
    assert wait_until(lambda: not process_alive(sandbox.job_pid("blocker")))
    assert list(sandbox.read("charge")) == [jobid]

    daemon = Daemon(sandbox)
    try:
        daemon.wait_for(lambda: sandbox.started_by("waiting"),
                        "the kept job to start")
    finally:
        daemon.stop()
    assert "1 pending jobs kept" in sandbox.messages()


def test_pending_jobs_can_be_deleted_at_start(sandbox):
    sandbox.write("charge", {"7": {**job(user="alice"), "id": "7"}})
    msub(sandbox, sandbox.job_script("a"))
    daemon = Daemon(sandbox, "--delete-pending")
    try:
        daemon.wait_for(lambda: "Pending jobs deleted" in sandbox.messages(),
                        "the pending jobs to be deleted")
        time.sleep(1)
        assert sandbox.read("charge") == {}
        assert sandbox.pending("subjob") == []
        assert sandbox.started_by("a") is None
    finally:
        daemon.stop()


def test_job_ids_are_not_reused_after_a_restart(sandbox):
    for name, expected in (("a", "1"), ("b", "2")):
        # One script per run: the first run's job is still in charge.mns
        # until the second daemon cleans it up.
        script = sandbox.job_script(name, 30)
        daemon = Daemon(sandbox)
        try:
            msub(sandbox, script)
            jobid, _ = daemon.wait_for(lambda: sandbox.find_job(script),
                                       "the job to be queued")
            assert jobid == expected
        finally:
            daemon.stop()
            sandbox.kill_everything()


def test_daemon_stays_up_when_idle(sandbox, daemon):
    time.sleep(3)
    assert daemon.alive(), daemon.log.read_text()


# ---------------------------------------------------------------------------
# running jobs
# ---------------------------------------------------------------------------

def test_job_runs_as_the_submitting_user(sandbox, daemon):
    msub(sandbox, sandbox.job_script("a", 5), "-c", 1, "-m", 100)
    daemon.wait_for(lambda: sandbox.started_by("a"), "job a to start")
    assert sandbox.started_by("a") == "alice"
    # Users cannot write in the install directory: jobs run in their own.
    assert (sandbox.jobs / "a.cwd").read_text().strip() == str(sandbox.jobs)


def test_running_job_is_tracked(sandbox, daemon):
    script = sandbox.job_script("a", 5)
    msub(sandbox, script, "-c", 2, "-m", 300)
    daemon.wait_for(lambda: sandbox.started_by("a"), "job a to start")
    jobid, entry = daemon.wait_for(lambda: sandbox.find_job(script),
                                   "job a in charge.mns")
    assert entry["status"] == "run"
    assert entry["runtime"]
    assert process_alive(entry["pid"])
    status = sandbox.read("status")
    assert (status["Ncpu"], status["RAM"]) == (2, 300)
    stat = sandbox.run("Mstat")
    assert any(line.split()[3:5] == [jobid, "run"]
               for line in stat.stdout.splitlines() if len(line.split()) > 4)


def test_finished_job_is_released(sandbox, daemon):
    script = sandbox.job_script("a", 1)
    msub(sandbox, script, "-c", 2, "-m", 300)
    daemon.wait_for(lambda: sandbox.done("a"), "job a to finish")
    daemon.wait_for(lambda: sandbox.find_job(script) is None,
                    "job a to leave charge.mns")
    status = sandbox.read("status")
    assert (status["Ncpu"], status["RAM"]) == (0, 0)
    assert f"Job {script} ended" in sandbox.messages()


def test_jobs_wait_for_free_cpus(sandbox, daemon):
    msub(sandbox, sandbox.job_script("a", 2), "-c", 2, "-m", 100)
    msub(sandbox, sandbox.job_script("b", 2), "-c", 2, "-m", 100)
    daemon.wait_for(lambda: sandbox.started_by("a") and sandbox.started_by("b"),
                    "jobs a and b to start")
    msub(sandbox, sandbox.job_script("c", 0), "-c", 2, "-m", 100)
    time.sleep(1)
    assert sandbox.started_by("c") is None, "c started on a full node"
    daemon.wait_for(lambda: sandbox.started_by("c"),
                    "job c to start once a CPU is free")
    assert sandbox.done("a") or sandbox.done("b")


def test_jobs_wait_for_free_memory(sandbox, daemon):
    msub(sandbox, sandbox.job_script("a", 2), "-c", 1, "-m", 700)
    daemon.wait_for(lambda: sandbox.started_by("a"), "job a to start")
    msub(sandbox, sandbox.job_script("b", 0), "-c", 1, "-m", 700)
    time.sleep(1)
    assert sandbox.started_by("b") is None, "b started without enough RAM"
    daemon.wait_for(lambda: sandbox.started_by("b"), "job b to start")
    assert sandbox.done("a")


def test_higher_priority_job_starts_first(sandbox, daemon):
    msub(sandbox, sandbox.job_script("blocker", 2), "-c", 4, "-m", 100)
    daemon.wait_for(lambda: sandbox.started_by("blocker"), "blocker to start")
    msub(sandbox, sandbox.job_script("low", 3), "-c", 4, "-p", 10)
    msub(sandbox, sandbox.job_script("high", 3), "-c", 4, "-p", 90)
    daemon.wait_for(lambda: sandbox.started_by("high") or
                    sandbox.started_by("low"), "a queued job to start")
    assert sandbox.started_by("high")
    assert sandbox.started_by("low") is None


def test_small_jobs_do_not_starve_a_big_one(sandbox, daemon):
    msub(sandbox, sandbox.job_script("blocker", 2), "-c", 2)
    daemon.wait_for(lambda: sandbox.started_by("blocker"), "blocker to start")
    msub(sandbox, sandbox.job_script("big", 0), "-c", 4, "-p", 90)
    msub(sandbox, sandbox.job_script("small", 0), "-c", 1, "-p", 10)
    time.sleep(1)
    # Two CPUs are free, but the small job must not overtake the big one.
    assert sandbox.started_by("small") is None
    daemon.wait_for(lambda: sandbox.started_by("small"), "small to start")
    assert sandbox.started_by("big")


def test_impossible_jobs_are_rejected(sandbox, daemon):
    # Written by hand, bypassing the checks of msub.
    sandbox.request("subjob1", {"script": "/bin/true", "Ncpu": 99, "RAM": 1,
                                "HDmemory": 0, "priority": 50})
    daemon.wait_for(lambda: "rejected" in sandbox.messages(),
                    "the request to be rejected")
    assert sandbox.read("charge") == {}
    assert "Ncpu 99 exceeds the node (4)" in sandbox.messages()


# ---------------------------------------------------------------------------
# mdel
# ---------------------------------------------------------------------------

def test_mdel_removes_a_queued_job(sandbox, daemon):
    msub(sandbox, sandbox.job_script("blocker", 30), "-c", 4)
    daemon.wait_for(lambda: sandbox.started_by("blocker"), "blocker to start")
    script = sandbox.job_script("victim")
    msub(sandbox, script, "-c", 4)
    jobid, _ = daemon.wait_for(lambda: sandbox.find_job(script),
                               "victim in charge.mns")
    assert mdel(sandbox, "-j", jobid).returncode == 0
    daemon.wait_for(lambda: sandbox.find_job(script) is None,
                    "victim to be deleted")


def test_mdel_kills_a_running_job(sandbox, daemon):
    script = sandbox.job_script("a", 30)
    msub(sandbox, script, "-c", 2, "-m", 300)
    child = daemon.wait_for(lambda: sandbox.job_pid("a", "child"),
                            "job a to start its child")
    jobid, _ = sandbox.find_job(script)
    assert mdel(sandbox, "-j", jobid).returncode == 0
    daemon.wait_for(lambda: not process_alive(sandbox.job_pid("a")),
                    "job a's script to be killed")
    # Otherwise the program run by the script would go on, untracked.
    daemon.wait_for(lambda: not process_alive(child),
                    "job a's child to be killed")
    daemon.wait_for(lambda: sandbox.find_job(script) is None,
                    "job a to leave charge.mns")
    status = sandbox.read("status")
    assert (status["Ncpu"], status["RAM"]) == (0, 0)


def test_mdel_by_script(sandbox, daemon):
    script = sandbox.job_script("a", 30)
    msub(sandbox, script)
    daemon.wait_for(lambda: sandbox.started_by("a"), "job a to start")
    assert mdel(sandbox, "-s", script).returncode == 0
    daemon.wait_for(lambda: sandbox.find_job(script) is None,
                    "job a to be deleted")


def test_mdel_cannot_delete_another_users_job(sandbox, daemon):
    script = sandbox.job_script("a", 30)
    msub(sandbox, script, user="alice")
    daemon.wait_for(lambda: sandbox.started_by("a"), "job a to start")
    jobid, _ = sandbox.find_job(script)
    mdel(sandbox, "-j", jobid, user="bob")
    daemon.wait_for(lambda: not sandbox.pending("remove") and
                    sandbox.read("delete") == {}, "the request to be handled")
    assert sandbox.find_job(script)
    assert process_alive(sandbox.job_pid("a"))


# ---------------------------------------------------------------------------
# stop
# ---------------------------------------------------------------------------

def test_minosse_stop(sandbox, daemon):
    msub(sandbox, sandbox.job_script("a", 30))
    child = daemon.wait_for(lambda: sandbox.job_pid("a", "child"),
                            "job a to start its child")
    # What "minosse stop" does:
    subprocess.run(["sed", "-i", "s/up/stop/", sandbox.path("conf")],
                   check=True)
    assert wait_until(lambda: not daemon.alive(), timeout=10)
    assert sandbox.read("conf") == {"status": "down"}
    assert sandbox.read("charge") == {}
    assert wait_until(lambda: not process_alive(sandbox.job_pid("a")))
    assert wait_until(lambda: not process_alive(child))
    assert "---MINOSSE STOPS---" in sandbox.messages()


# ---------------------------------------------------------------------------
# security: the daemon runs as root and starts whatever users submit
# ---------------------------------------------------------------------------

def assert_not_run_as_root(box, daemon, name):
    daemon.wait_for(lambda: picked_up(box), "the job to be picked up")
    wait_until(lambda: box.started_by(name), timeout=3)
    assert box.started_by(name) != "root"


def test_script_name_cannot_inject_root_commands(sandbox, daemon):
    script = sandbox.job_script("a")
    pwned = sandbox.jobs / "pwned"
    msub(sandbox, f"{script}; id -un > {pwned}")
    daemon.wait_for(lambda: picked_up(sandbox), "the job to be picked up")
    time.sleep(1)
    assert not pwned.exists(), f"injected command ran as {pwned.read_text()}"


def test_user_cannot_impersonate_root_via_environment(sandbox, daemon):
    script = sandbox.job_script("a")
    subprocess.run(["runuser", "-u", "alice", "--", "env", "LOGNAME=root",
                    "USER=root", sys.executable, sandbox.script("Msub"),
                    "-f", script], check=True)
    assert_not_run_as_root(sandbox, daemon, "a")


def test_user_cannot_forge_a_root_submission(sandbox, daemon):
    script = sandbox.job_script("a")
    sandbox.request("subjob999", {
        "user": "root", "script": str(script), "status": "que",
        "priority": 50, "Ncpu": 1, "RAM": 100, "HDmemory": 0, "pid": "",
        "runtime": "", "subtime": "", "chain": "none"}, owner="alice")
    assert_not_run_as_root(sandbox, daemon, "a")
    assert sandbox.started_by("a") == "alice"


def test_malformed_request_does_not_stop_the_daemon(sandbox, daemon):
    sandbox.request("subjob1", {"2": "garbage"}, owner="alice")
    daemon.wait_for(lambda: not sandbox.pending("subjob"),
                    "the request to be rejected")
    assert "rejected" in sandbox.messages()
    msub(sandbox, sandbox.job_script("a"))
    daemon.wait_for(lambda: sandbox.started_by("a"), "job a to start")
