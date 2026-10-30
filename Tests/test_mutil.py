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


def test_check_for_submissions_does_not_let_small_jobs_overtake():
    # Otherwise a stream of small jobs could starve the big one forever.
    queue = {"big": job(Ncpu=4, priority=90), "small": job(Ncpu=1, priority=10)}
    available = {"Ncpu": 3, "RAM": 1000, "HDmemory": 10}
    assert schedule(available, queue) == []


def test_check_for_submissions_starts_jobs_ahead_of_a_waiting_one():
    queue = {"low": job(Ncpu=1, priority=10), "mid": job(Ncpu=4, priority=50),
             "high": job(Ncpu=1, priority=90)}
    available = {"Ncpu": 3, "RAM": 1000, "HDmemory": 10}
    assert schedule(available, queue) == ["high"]


def test_check_for_submissions_equal_priority_is_first_come_first_served():
    queue = {"1": job(Ncpu=4), "2": job(Ncpu=1)}
    available = {"Ncpu": 3, "RAM": 1000, "HDmemory": 10}
    assert schedule(available, queue) == []


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
                             "2": job(status="que", script="/jobs/b.sh")})
    sandbox.request("subjob123", {"script": "/jobs/c.sh"})
    sandbox.request("remove456", {"id": "2"})
    status = {"status": "down", "Ncpu": 3, "RAM": 500, "HDmemory": 1,
              "lastid": 41}

    # Called as Minosse.py does: the conf file is passed as statusf.
    status = Mutil.cleanstatus(status, sandbox.mdir, sandbox.base("charge"),
                               sandbox.base("conf"))

    assert status == {"status": "up", "Ncpu": 0, "RAM": 0, "HDmemory": 0,
                      "lastid": 41}
    assert sandbox.read("conf") == {"status": "up"}
    assert sleeper.wait(timeout=5) == -signal.SIGTERM
    # By default the pending jobs wait for the next run.
    assert sandbox.read("charge") == {"2": job(status="que",
                                               script="/jobs/b.sh")}
    assert len(sandbox.pending("subjob")) == len(sandbox.pending("remove")) == 1
    assert "All running jobs killed" in sandbox.messages()
    assert "2 pending jobs kept" in sandbox.messages()
    assert "status machine cleaned" in sandbox.messages()


def test_cleanstatus_can_delete_pending_jobs(sandbox, sleeper):
    sandbox.write("charge", {"1": job(status="run", pid=sleeper.pid),
                             "2": job(status="que")})
    sandbox.request("subjob123", {"script": "/jobs/c.sh"})
    sandbox.request("remove456", {"id": "2"})
    (sandbox.requests / "notes.txt").write_text("not a request")
    Mutil.cleanstatus({"Ncpu": 1, "RAM": 1, "HDmemory": 0}, sandbox.mdir,
                      sandbox.base("charge"), sandbox.base("conf"),
                      keep=False)
    assert sleeper.wait(timeout=5) == -signal.SIGTERM
    assert sandbox.read("charge") == {}
    assert sandbox.pending("subjob") == sandbox.pending("remove") == []
    assert (sandbox.requests / "notes.txt").exists()
    assert "Pending jobs deleted" in sandbox.messages()


def test_pendingjobs_lists_queued_and_unread_submissions(sandbox):
    sandbox.write("charge", {"1": job(status="run", pid=99),
                             "2": job(status="que", script="/jobs/b.sh")})
    sandbox.request("subjob1", {"script": "/jobs/c.sh"})
    (sandbox.requests / "subjob2.mns").write_text("{garbage")
    sandbox.request("remove1", {"id": "2"})
    assert Mutil.pendingjobs(sandbox.mdir, sandbox.base("charge")) == [
        ("alice", "/jobs/b.sh"), (ME, "/jobs/c.sh")]


def test_pendingjobs_on_idle_node(sandbox):
    assert Mutil.pendingjobs(sandbox.mdir, sandbox.base("charge")) == []


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
                                      Ncpu=2),
                             "2": job(status="que")})
    sandbox.write("status", {**sandbox.read("status"), "Ncpu": 2})
    with pytest.raises(SystemExit) as exit_:
        checkdemon(sandbox)
    assert exit_.value.code == 0
    assert sandbox.read("conf") == {"status": "down"}
    # The queued job waits for the next start.
    assert sandbox.read("charge") == {"2": job(status="que")}
    assert sandbox.read("status")["Ncpu"] == 0
    assert sleeper.wait(timeout=5) == -signal.SIGTERM
    assert "---MINOSSE STOPS---" in sandbox.messages()


# ---------------------------------------------------------------------------
# incoming requests: collectrequests / writejob / submitjobs / checkdeletedjob
# ---------------------------------------------------------------------------

def collect(box, prefix):
    return Mutil.collectrequests(box.rdir, prefix, box.base("messages"))


def writejob(box, prefix, target):
    Mutil.writejob(box.rdir, prefix, box.base(target), box.base("messages"))


def submitjobs(box):
    Mutil.submitjobs(box.rdir, "subjob", box.base("charge"),
                     box.base("status"), box.read("nodes"),
                     box.base("messages"))


def submission(**fields):
    """A request as msub writes it."""
    request = job(**fields)
    for key in ("pid", "runtime"):
        request[key] = ""
    return request


def test_requestname_is_unique_and_sorts_in_submission_order():
    names = [Mutil.requestname("subjob") for _ in range(100)]
    assert len(set(names)) == 100
    assert sorted(names) == names
    assert all(n.startswith("subjob") for n in names)


def test_collectrequests_reads_and_removes_requests_in_order(sandbox):
    sandbox.request("subjob2", {"script": "/b"})
    sandbox.request("subjob1", {"script": "/a"})
    sandbox.request("remove1", {"id": "1"})
    (sandbox.requests / "notes.txt").write_text("not a request")
    assert list(collect(sandbox, "subjob").items()) == [
        ("1", {"script": "/a", "user": ME}),
        ("2", {"script": "/b", "user": ME})]
    assert sandbox.pending("subjob") == []
    assert len(sandbox.pending("remove")) == 1
    assert (sandbox.requests / "notes.txt").exists()


@needs_server
def test_collectrequests_takes_the_user_from_the_file_owner(sandbox):
    sandbox.request("remove1", {"id": "1", "user": "root"}, owner="alice")
    assert collect(sandbox, "remove")["1"]["user"] == "alice"


@pytest.mark.parametrize("content", ["{not json", "[]", '"a string"'])
def test_collectrequests_rejects_malformed_requests(sandbox, content):
    (sandbox.requests / "subjob11.mns").write_text(content)
    assert collect(sandbox, "subjob") == {}
    assert sandbox.pending("subjob") == []
    assert "WARNING:request subjob11.mns rejected" in sandbox.messages()


def test_collectrequests_rejects_links(sandbox):
    # A link to a file of another user would make the daemon read it.
    target = sandbox.dir / "victim.mns"
    target.write_text('{"script": "/x"}')
    (sandbox.requests / "subjob11.mns").symlink_to(target)
    assert collect(sandbox, "subjob") == {}
    assert sandbox.pending("subjob") == []
    assert "rejected" in sandbox.messages()


def test_collectrequests_does_not_block_on_fifos(sandbox):
    os.mkfifo(sandbox.requests / "subjob11.mns")
    assert collect(sandbox, "subjob") == {}
    assert "rejected" in sandbox.messages()


def test_writejob_collects_delete_requests(sandbox):
    sandbox.write("delete", {"5": {"id": "1"}})
    request = {"script": None, "id": "11", "all": False, "user": ME}
    sandbox.request("remove77", request)
    writejob(sandbox, "remove", "delete")
    assert sandbox.read("delete") == {"5": {"id": "1"}, "77": request}
    assert sandbox.pending("remove") == []


def test_submitjobs_numbers_jobs_in_submission_order(sandbox):
    sandbox.write("charge", {"7": job(status="run", pid=99)})
    sandbox.request("subjob1", submission(script="/jobs/a.sh"))
    sandbox.request("subjob2", submission(script="/jobs/b.sh"))
    submitjobs(sandbox)
    charge = sandbox.read("charge")
    assert list(charge) == ["7", "1", "2"]
    assert charge["1"] == {**submission(script="/jobs/a.sh"), "id": "1",
                           "user": ME}
    assert charge["2"]["script"] == "/jobs/b.sh"
    assert sandbox.read("status")["lastid"] == 2
    assert sandbox.pending("subjob") == []
    assert "Job 1 /jobs/a.sh queued" in sandbox.messages()


def test_submitjobs_never_reuses_ids(sandbox):
    # The counter survives restarts, so a stale mdel cannot hit a new job.
    sandbox.write("status", {**sandbox.read("status"), "lastid": 41})
    sandbox.request("subjob1", submission())
    submitjobs(sandbox)
    assert list(sandbox.read("charge")) == ["42"]


def test_submitjobs_skips_ids_in_use(sandbox):
    sandbox.write("charge", {"1": job(status="run", pid=99)})
    sandbox.request("subjob1", submission(script="/jobs/new.sh"))
    submitjobs(sandbox)
    assert sandbox.read("charge")["2"]["script"] == "/jobs/new.sh"


def test_submitjobs_accepts_simultaneous_submissions(sandbox):
    for _ in range(20):
        sandbox.request(Mutil.requestname("subjob"), submission())
    submitjobs(sandbox)
    assert list(sandbox.read("charge")) == [str(i) for i in range(1, 21)]


def test_submitjobs_ignores_daemon_fields_in_requests(sandbox, sleeper):
    # Otherwise a forged "running" job would make root kill any pid.
    sandbox.request("subjob1", submission(status="run", pid=sleeper.pid,
                                          runtime="now", id="99"))
    submitjobs(sandbox)
    entry = sandbox.read("charge")["1"]
    assert (entry["status"], entry["pid"], entry["runtime"], entry["id"]) == (
        "que", "", "", "1")


@pytest.mark.parametrize("fields, error", [
    ({"Ncpu": 5}, "Ncpu 5 exceeds the node (4)"),
    ({"RAM": 1001}, "RAM 1001 exceeds the node (1000)"),
    ({"HDmemory": 11}, "HDmemory 11 exceeds the node (10)"),
    ({"Ncpu": 0}, "at least one cpu is needed"),
    ({"RAM": -1}, "RAM must not be negative"),
    ({"Ncpu": "2"}, "Ncpu must be an integer"),
    ({"Ncpu": True}, "Ncpu must be an integer"),
    ({"priority": None}, "priority must be an integer"),
    ({"script": "job.sh"}, "the script must be an absolute path"),
    ({"script": None}, "the script must be an absolute path"),
])
def test_submitjobs_rejects_jobs_that_can_never_run(sandbox, fields, error):
    sandbox.request("subjob1", submission(**fields))
    submitjobs(sandbox)
    assert sandbox.read("charge") == {}
    assert sandbox.pending("subjob") == []
    assert error in sandbox.messages()


def test_submitjobs_rejects_requests_without_fields(sandbox):
    sandbox.request("subjob1", {})
    submitjobs(sandbox)
    assert sandbox.read("charge") == {}
    assert "rejected: Ncpu must be an integer" in sandbox.messages()


def checkdeletedjob(box):
    """Collect the delete requests and handle them, as Minosse.py does."""
    writejob(box, "remove", "delete")
    Mutil.checkdeletedjob(box.base("delete"), box.base("charge"),
                          box.base("status"), box.base("messages"))


def mdel_request(box, id=None, script=None):
    """Drop a request file as Mdel.py writes it."""
    box.request("remove555", {"script": script, "id": id, "all": False,
                              "user": ME})


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


def test_checkdeletedjob_ignores_incomplete_requests(sandbox):
    sandbox.write("charge", {"1": job(user=ME)})
    sandbox.request("remove1", {})
    checkdeletedjob(sandbox)
    assert list(sandbox.read("charge")) == ["1"]
    assert sandbox.read("delete") == {}


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
