"""Unit tests for Utils/Mutil.py.

Tests marked xfail describe the intended behaviour of code that is known to
be broken; the reason names the defect.  xfail is strict (see pytest.ini),
so fixing a defect turns its test into a failure until the marker is removed.
"""

import os
import pwd
import signal
import subprocess
import sys

import pytest

import Mutil
from conftest import job, needs_server, wait_until

# Request files are written by the test process, so the daemon, which takes
# the user from the file owner, sees this user.
ME = pwd.getpwuid(os.getuid()).pw_name


@pytest.fixture
def sleeper():
    proc = subprocess.Popen(["sleep", "60"])
    yield proc
    proc.kill()
    proc.wait()


def dead_pid():
    proc = subprocess.Popen(["true"])
    proc.wait()
    return proc.pid


# ---------------------------------------------------------------------------
# messages
# ---------------------------------------------------------------------------

def test_initialization_message_truncates_log(tmp_path):
    log = tmp_path / "messages"
    log.write_text("old content\n")
    Mutil.writeinitializationmessage(str(log))
    text = log.read_text()
    assert "old content" not in text
    assert text.rstrip().endswith("---MINOSSE START---")


def test_writemessage_appends_timestamped_lines(tmp_path):
    log = tmp_path / "messages"
    Mutil.writemessage("first", str(log))
    Mutil.writemessage("second", str(log))
    lines = log.read_text().splitlines()
    assert len(lines) == 2
    assert lines[0].endswith("   first")
    assert lines[1].endswith("   second")


def test_writewarning(tmp_path):
    log = tmp_path / "messages"
    Mutil.writewarning("disk full", str(log))
    assert "WARNING:disk full" in log.read_text()


def test_writefatalerror_logs_and_exits(tmp_path):
    log = tmp_path / "messages"
    with pytest.raises(SystemExit):
        Mutil.writefatalerror("boom", str(log))
    text = log.read_text()
    assert "FATAL:  boom" in text
    assert "--- MINOSSE STOPS ABNORMALLY ---" in text


# ---------------------------------------------------------------------------
# .mns files
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("data", [
    {},
    {"status": "up"},
    {"42": job(), "7": job(status="run", pid=1234)},
])
def test_mns_roundtrip(tmp_path, data):
    base = str(tmp_path / "charge")
    Mutil.writeallfile(base, data)
    assert (tmp_path / "charge.mns").exists()
    assert Mutil.readallfile(base) == data


def test_mns_files_are_human_readable(tmp_path):
    base = str(tmp_path / "conf")
    Mutil.writeallfile(base, {"status": "up"})
    assert (tmp_path / "conf.mns").read_text() == '{\n  "status": "up"\n}'


def test_writeallfile_replaces_the_file_atomically(tmp_path):
    base = str(tmp_path / "charge")
    Mutil.writeallfile(base, {"1": job()})
    before = os.stat(f"{base}.mns").st_ino
    Mutil.writeallfile(base, {})
    # A new inode: readers holding the old file never see a partial write.
    assert os.stat(f"{base}.mns").st_ino != before
    assert os.listdir(tmp_path) == ["charge.mns"]
    assert os.stat(f"{base}.mns").st_mode & 0o777 == 0o644


def test_readallfile_missing_file(tmp_path):
    with pytest.raises(FileNotFoundError):
        Mutil.readallfile(str(tmp_path / "nothing"))


# ---------------------------------------------------------------------------
# scheduling helpers
# ---------------------------------------------------------------------------

def test_applydefaults_keeps_explicit_values():
    defaults = {"Ncpu": 1, "RAM": 900, "HDmemory": 0, "priority": 50}
    charge = {"1": job(Ncpu=3, RAM=200, HDmemory=2, priority=10)}
    result = Mutil.applydefaults(charge, defaults)
    assert result["1"]["Ncpu"] == 3
    assert result["1"]["RAM"] == 200
    assert result["1"]["priority"] == 10


def test_applydefaults_fills_undefined_values():
    defaults = {"Ncpu": 1, "RAM": 900, "HDmemory": 0, "priority": 50}
    charge = {"1": job(RAM=float("nan"), priority=None)}
    del charge["1"]["HDmemory"]
    result = Mutil.applydefaults(charge, defaults)
    assert result["1"]["RAM"] == 900
    assert result["1"]["priority"] == 50
    assert result["1"]["HDmemory"] == 0


def test_find_queued_jobs():
    charge = {"1": job(status="que"), "2": job(status="run"),
              "3": job(status="que"), "4": job(status="end")}
    assert set(Mutil.find_queued_jobs(charge)) == {"1", "3"}
    assert Mutil.find_queued_jobs({}) == {}


def test_sortbypriority_highest_first():
    jobs = {"a": job(priority=3), "b": job(priority=-1), "c": job(priority=7)}
    assert Mutil.sortbypriority(jobs) == [["c", 7], ["a", 3], ["b", -1]]


def test_sortbypriority_ties_keep_submission_order():
    jobs = {"a": job(priority=5), "b": job(priority=5), "c": job(priority=5)}
    assert [j for j, _ in Mutil.sortbypriority(jobs)] == ["a", "b", "c"]


def test_sortbypriority_empty():
    assert Mutil.sortbypriority({}) == []


@pytest.mark.parametrize("used, free_space", [
    ({"Ncpu": 0, "RAM": 0, "HDmemory": 0}, True),
    ({"Ncpu": 3, "RAM": 999, "HDmemory": 9}, True),
    ({"Ncpu": 4, "RAM": 0, "HDmemory": 0}, False),
    ({"Ncpu": 0, "RAM": 1000, "HDmemory": 0}, False),
    ({"Ncpu": 0, "RAM": 0, "HDmemory": 10}, False),
    ({"Ncpu": 5, "RAM": 0, "HDmemory": 0}, False),
])
def test_find_available_resources(used, free_space):
    node = {"Ncpu": 4, "RAM": 1000, "HDmemory": 10}
    available = Mutil.find_available_resources(used, node)
    assert available == {"free_space": free_space,
                         "Ncpu": 4 - used["Ncpu"],
                         "RAM": 1000 - used["RAM"],
                         "HDmemory": 10 - used["HDmemory"]}


def schedule(available, queue):
    return Mutil.check_for_submissions(
        available, Mutil.sortbypriority(queue), queue)


def test_check_for_submissions_all_fit():
    queue = {"1": job(Ncpu=2), "2": job(Ncpu=2)}
    available = {"Ncpu": 4, "RAM": 1000, "HDmemory": 10}
    assert schedule(available, queue) == ["1", "2"]


def test_check_for_submissions_exact_fit():
    queue = {"1": job(Ncpu=4, RAM=1000, HDmemory=10)}
    available = {"Ncpu": 4, "RAM": 1000, "HDmemory": 10}
    assert schedule(available, queue) == ["1"]


@pytest.mark.parametrize("request_", [
    {"Ncpu": 5}, {"RAM": 1001}, {"HDmemory": 11}])
def test_check_for_submissions_too_big(request_):
    queue = {"1": job(**request_)}
    available = {"Ncpu": 4, "RAM": 1000, "HDmemory": 10}
    assert schedule(available, queue) == []


def test_check_for_submissions_respects_priority_when_resources_are_short():
    queue = {"low": job(Ncpu=3, priority=10), "high": job(Ncpu=3, priority=90)}
    available = {"Ncpu": 4, "RAM": 1000, "HDmemory": 10}
    assert schedule(available, queue) == ["high"]


def test_check_for_submissions_backfills_smaller_jobs():
    # A job that does not fit is skipped and lower-priority jobs that fit
    # are started: small jobs can starve a big high-priority one.
    queue = {"big": job(Ncpu=4, priority=90), "small": job(Ncpu=1, priority=10)}
    available = {"Ncpu": 3, "RAM": 1000, "HDmemory": 10}
    assert schedule(available, queue) == ["small"]


def test_check_for_submissions_accounts_all_resources():
    queue = {"1": job(Ncpu=1, RAM=600), "2": job(Ncpu=1, RAM=600)}
    available = {"Ncpu": 4, "RAM": 1000, "HDmemory": 10}
    assert schedule(available, queue) == ["1"]


def test_update_status():
    status = {"Ncpu": 1, "RAM": 100, "HDmemory": 0, "status": "up"}
    Mutil.update_status(status, job(Ncpu=2, RAM=300, HDmemory=1), 1)
    assert status == {"Ncpu": 3, "RAM": 400, "HDmemory": 1, "status": "up"}
    Mutil.update_status(status, job(Ncpu=2, RAM=300, HDmemory=1), -1)
    assert status == {"Ncpu": 1, "RAM": 100, "HDmemory": 0, "status": "up"}


def test_delete():
    jobs = {"1": job(), "2": job(script="/jobs/b.sh")}
    assert Mutil.delete("2", jobs)["script"] == "/jobs/b.sh"
    assert list(jobs) == ["1"]
    assert Mutil.delete("missing", jobs) is None


# ---------------------------------------------------------------------------
# endjob
# ---------------------------------------------------------------------------

def test_endjob_ignores_queued_jobs(tmp_path):
    charge = {"1": job(status="que")}
    status = {"Ncpu": 0, "RAM": 0, "HDmemory": 0}
    assert Mutil.endjob(charge, status, str(tmp_path / "messages")) == (
        {"1": job(status="que")}, {"Ncpu": 0, "RAM": 0, "HDmemory": 0})


def test_endjob_keeps_running_job(tmp_path, sleeper):
    # The daemon stores Popen.pid, an int, and it survives the JSON roundtrip.
    charge = {"1": job(status="run", pid=sleeper.pid, Ncpu=2)}
    status = {"Ncpu": 2, "RAM": 100, "HDmemory": 0}
    charge, status = Mutil.endjob(charge, status, str(tmp_path / "messages"))
    assert charge["1"]["status"] == "run"
    assert status["Ncpu"] == 2


def test_endjob_releases_finished_job(tmp_path):
    log = tmp_path / "messages"
    charge = {"1": job(status="run", pid=dead_pid(), Ncpu=2, RAM=300),
              "2": job(status="que", script="/jobs/b.sh")}
    status = {"Ncpu": 2, "RAM": 300, "HDmemory": 0}
    charge, status = Mutil.endjob(charge, status, str(log))
    assert list(charge) == ["2"]
    assert status == {"Ncpu": 0, "RAM": 0, "HDmemory": 0}
    assert "Job /jobs/a.sh ended" in log.read_text()


def test_endjob_reaps_finished_child(tmp_path):
    # A finished child that nobody waited for is a zombie: it still exists,
    # but the job is over.
    child = subprocess.Popen(["true"])
    assert wait_until(lambda: open(f"/proc/{child.pid}/stat").read()
                      .rsplit(")", 1)[1].split()[0] == "Z")
    charge = {"1": job(status="run", pid=child.pid)}
    status = {"Ncpu": 1, "RAM": 100, "HDmemory": 0}
    charge, status = Mutil.endjob(charge, status, str(tmp_path / "messages"))
    assert charge == {}
    assert not os.path.exists(f"/proc/{child.pid}")


# ---------------------------------------------------------------------------
# daemon start/stop
# ---------------------------------------------------------------------------

def test_cleanstatus_resets_the_node(sandbox, sleeper):
    sandbox.write("charge", {"1": job(status="run", pid=sleeper.pid),
                             "2": job(status="que")})
    sandbox.request("subjob123", {})
    sandbox.request("remove456", {})
    sandbox.request("unrelated", {})
    status = {"status": "down", "Ncpu": 3, "RAM": 500, "HDmemory": 1}

    # Called as Minosse.py does: the conf file is passed as statusf.
    status = Mutil.cleanstatus(status, sandbox.mdir, sandbox.base("charge"),
                               sandbox.base("conf"))

    assert status == {"status": "up", "Ncpu": 0, "RAM": 0, "HDmemory": 0}
    assert sandbox.read("charge") == {}
    assert sandbox.read("conf") == {"status": "up"}
    assert sandbox.pending("subjob") == sandbox.pending("remove") == []
    assert (sandbox.requests / "unrelated.mns").exists()
    assert sleeper.wait(timeout=5) == -signal.SIGTERM
    assert "All jobs killed" in sandbox.messages()
    assert "status machine cleaned" in sandbox.messages()


def checkdemon(box):
    """Call checkdemon as Minosse.py does."""
    Mutil.checkdemon(box.base("conf"), box.base("charge"), box.base("status"),
                     box.base("messages"))


def test_checkdemon_keeps_running_while_up(sandbox):
    sandbox.write("conf", {"status": "up"})
    assert checkdemon(sandbox) is None


def test_checkdemon_stops_on_request(sandbox, sleeper):
    sandbox.write("conf", {"status": "stop"})
    sandbox.write("charge", {"1": job(status="run", pid=sleeper.pid,
                                      Ncpu=2)})
    sandbox.write("status", {**sandbox.read("status"), "Ncpu": 2})
    with pytest.raises(SystemExit) as exit_:
        checkdemon(sandbox)
    assert exit_.value.code == 0
    assert sandbox.read("conf") == {"status": "down"}
    assert sandbox.read("charge") == {}
    assert sandbox.read("status")["Ncpu"] == 0
    assert sleeper.wait(timeout=5) == -signal.SIGTERM
    assert "---MINOSSE STOPS---" in sandbox.messages()


# ---------------------------------------------------------------------------
# incoming requests: writejob / checkdeletedjob
# ---------------------------------------------------------------------------

def writejob(box, prefix, target):
    Mutil.writejob(box.rdir, prefix, box.base(target), box.base("messages"))


def test_writejob_collects_submissions(sandbox):
    sandbox.request("subjob11", {"11": job(user=ME)})
    sandbox.request("subjob22", {"22": job(user=ME, script="/jobs/b.sh")})
    (sandbox.requests / "notes.txt").write_text("not a request")
    writejob(sandbox, "subjob", "charge")
    assert sandbox.read("charge") == {
        "11": job(user=ME), "22": job(user=ME, script="/jobs/b.sh")}
    assert sandbox.pending("subjob") == []
    assert (sandbox.requests / "notes.txt").exists()


def test_writejob_keeps_tracked_jobs(sandbox):
    sandbox.write("charge", {"11": job(user=ME, status="run", pid=99)})
    sandbox.request("subjob22", {"22": job(user=ME)})
    writejob(sandbox, "subjob", "charge")
    assert sandbox.read("charge") == {
        "11": job(user=ME, status="run", pid=99), "22": job(user=ME)}


def test_writejob_collects_delete_requests(sandbox):
    request = {"script": None, "id": "11", "all": False, "user": ME}
    sandbox.request("remove77", {"77": request})
    writejob(sandbox, "remove", "delete")
    assert sandbox.read("delete") == {"77": request}
    assert sandbox.pending("remove") == []


@needs_server
@pytest.mark.parametrize("prefix, target", [("subjob", "charge"),
                                            ("remove", "delete")])
def test_writejob_takes_the_user_from_the_file_owner(sandbox, prefix, target):
    sandbox.request(f"{prefix}11", {"11": job(user="root")}, owner="alice")
    writejob(sandbox, prefix, target)
    assert sandbox.read(target)["11"]["user"] == "alice"


@pytest.mark.parametrize("content", [
    "{not json", '{"12": {}}', "[]", '{"11": "a string"}'])
def test_writejob_rejects_malformed_requests(sandbox, content):
    (sandbox.requests / "subjob11.mns").write_text(content)
    writejob(sandbox, "subjob", "charge")
    assert sandbox.read("charge") == {}
    assert sandbox.pending("subjob") == []
    assert "WARNING:request subjob11.mns rejected" in sandbox.messages()


def test_writejob_rejects_links(sandbox):
    # A link to a file of another user would make the daemon read it.
    target = sandbox.dir / "victim.mns"
    target.write_text('{"11": {"script": "/x"}}')
    (sandbox.requests / "subjob11.mns").symlink_to(target)
    writejob(sandbox, "subjob", "charge")
    assert sandbox.read("charge") == {}
    assert sandbox.pending("subjob") == []
    assert "rejected" in sandbox.messages()


def test_writejob_does_not_block_on_fifos(sandbox):
    os.mkfifo(sandbox.requests / "subjob11.mns")
    writejob(sandbox, "subjob", "charge")
    assert sandbox.read("charge") == {}
    assert "rejected" in sandbox.messages()


@pytest.mark.xfail(reason="DESIGN: job ids are random in 1..1e6; on a "
                          "collision the new submission is silently ignored "
                          "and its file is left behind forever")
def test_writejob_does_not_drop_colliding_submission(sandbox):
    sandbox.write("charge", {"11": job(user=ME, status="run", pid=99)})
    sandbox.request("subjob11", {"11": job(user=ME, script="/jobs/new.sh")})
    writejob(sandbox, "subjob", "charge")
    scripts = [j["script"] for j in sandbox.read("charge").values()]
    assert "/jobs/new.sh" in scripts
    assert sandbox.pending("subjob") == []


def checkdeletedjob(box):
    """Collect the delete requests and handle them, as Minosse.py does."""
    writejob(box, "remove", "delete")
    Mutil.checkdeletedjob(box.base("delete"), box.base("charge"),
                          box.base("status"), box.base("messages"))


def mdel_request(box, id=None, script=None):
    """Drop a request file as Mdel.py writes it."""
    box.request("remove555", {"555": {"script": script, "id": id,
                                      "all": False, "user": ME}})


def test_checkdeletedjob_without_requests_is_a_noop(sandbox):
    sandbox.write("charge", {"1": job(user=ME)})
    checkdeletedjob(sandbox)
    assert sandbox.read("charge") == {"1": job(user=ME)}


@pytest.mark.parametrize("jobid", ["1", 1])
def test_checkdeletedjob_deletes_queued_job_by_id(sandbox, jobid):
    sandbox.write("charge", {"1": job(user=ME),
                             "2": job(user=ME, script="/jobs/b.sh")})
    mdel_request(sandbox, id=jobid)
    checkdeletedjob(sandbox)
    assert list(sandbox.read("charge")) == ["2"]
    assert sandbox.read("delete") == {}
    assert "job 1 /jobs/a.sh deleted" in sandbox.messages()


def test_checkdeletedjob_deletes_queued_job_by_script(sandbox):
    sandbox.write("charge", {"1": job(user=ME),
                             "2": job(user=ME, script="/jobs/b.sh"),
                             "3": job(user=ME, script="/jobs/b.sh")})
    mdel_request(sandbox, script="/jobs/b.sh")
    checkdeletedjob(sandbox)
    assert list(sandbox.read("charge")) == ["1"]


def test_checkdeletedjob_kills_running_job_and_frees_resources(sandbox,
                                                              sleeper):
    sandbox.write("charge", {"1": job(user=ME, status="run",
                                      pid=sleeper.pid, Ncpu=2, RAM=300)})
    sandbox.write("status", {"Ncpu": 2, "RAM": 300, "HDmemory": 0,
                             "status": "up"})
    mdel_request(sandbox, id="1")
    checkdeletedjob(sandbox)
    assert sleeper.wait(timeout=5) == -signal.SIGTERM
    assert sandbox.read("charge") == {}
    assert sandbox.read("status")["Ncpu"] == 0
    assert sandbox.read("status")["RAM"] == 0


def test_checkdeletedjob_refuses_other_users_jobs(sandbox):
    sandbox.write("charge", {"1": job(user="alice")})
    mdel_request(sandbox, id="1")
    checkdeletedjob(sandbox)
    assert list(sandbox.read("charge")) == ["1"]
    assert f"WARNING:{ME} tried to delete job 1 of alice" in sandbox.messages()


def test_checkdeletedjob_warns_about_unknown_jobs(sandbox):
    sandbox.write("charge", {"1": job(user=ME)})
    mdel_request(sandbox, id="99")
    checkdeletedjob(sandbox)
    assert list(sandbox.read("charge")) == ["1"]
    assert "job 99, which does not exist" in sandbox.messages()


# ---------------------------------------------------------------------------
# process helpers
# ---------------------------------------------------------------------------

def start_fake_daemon(path):
    path.write_text("import time\ntime.sleep(60)\n")
    return subprocess.Popen([sys.executable, str(path)])


def test_ifrunning_without_daemon_exits(tmp_path, capsys):
    with pytest.raises(SystemExit):
        Mutil.ifrunning(f"{tmp_path}/")
    assert "no minosse demon running!" in capsys.readouterr().out


def test_ifrunning_with_daemon_returns(tmp_path):
    proc = start_fake_daemon(tmp_path / "Minosse.py")
    try:
        assert wait_until(lambda: Mutil.ifrunning(f"{tmp_path}/") is None)
    finally:
        proc.kill()
        proc.wait()


def test_ifrunning_with_two_daemons_exits(tmp_path, capsys):
    procs = [start_fake_daemon(tmp_path / "Minosse.py") for _ in range(2)]
    try:
        with pytest.raises(SystemExit):
            Mutil.ifrunning(f"{tmp_path}/")
        assert "more than one minosse demon running!" in capsys.readouterr().out
    finally:
        for proc in procs:
            proc.kill()
            proc.wait()


@pytest.mark.skipif(not os.path.exists("/usr/bin/pstree"),
                    reason="pstree (psmisc) not installed")
def test_getpid_lists_process_tree():
    proc = subprocess.Popen(["bash", "-c", "sleep 60 & sleep 60; wait"])
    try:
        def children():
            out = subprocess.run(["ps", "--ppid", str(proc.pid), "-o", "pid="],
                                 capture_output=True, text=True).stdout
            pids = out.split()
            return pids if len(pids) == 2 else None
        kids = wait_until(children)
        assert kids
        assert set(Mutil.getpid(proc.pid, "all")) == {str(proc.pid), *kids}
        assert set(Mutil.getpid(proc.pid, "leaves")) == set(kids)
    finally:
        subprocess.run(["pkill", "-P", str(proc.pid)])
        proc.kill()
        proc.wait()
