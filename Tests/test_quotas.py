"""Tests of the cpu and RAM quotas of the users (quotas.mns): the functions
of Utils/Mutil.py, the checks of msub, mstat -q and, on the simulated
server, the daemon enforcing them.

The quotas map user names to the cpus and RAM their running jobs can use.
Without quotas nobody is limited; once some are set, a user left out of the
file has the smallest cpus and the smallest RAM in it.  On the sandbox node
(4 cpus, 1000 MB) a quota is at least 1 cpu and 250 MB.
"""

import json
import os
import pwd
import time

import pytest

import Mutil
from conftest import job, needs_server

ME = pwd.getpwuid(os.getuid()).pw_name
NODE = {"Ncpu": 4, "RAM": 1000, "HDmemory": 10}


def q(cpus, ram):
    return {"Ncpu": cpus, "RAM": ram}


def schedule(queue, quotas=None, used=None, available=NODE):
    return Mutil.check_for_submissions(
        available, Mutil.sortbypriority(queue), queue, quotas, used)


# ---------------------------------------------------------------------------
# the quotas file
# ---------------------------------------------------------------------------

def test_minimum_quota_is_one_cpu_and_its_ram():
    assert Mutil.minimumquota(NODE) == q(1, 250)


@pytest.mark.parametrize("quotas", [
    {}, {"alice": q(1, 250)}, {"alice": q(4, 1000), "bob": q(64, 99999)}])
def test_invalidquotas_accepts_valid_quotas(quotas):
    assert Mutil.invalidquotas(quotas, NODE) is None


@pytest.mark.parametrize("quotas, error", [
    ([], "it must map user names to quotas"),
    ({"alice": 2}, "the quota of alice must give Ncpu and RAM"),
    ({"alice": {"Ncpu": 2}}, "the quota of alice must give Ncpu and RAM"),
    ({"alice": {**q(2, 300), "ram": 1}}, "must give Ncpu and RAM, and nothing"),
    ({"alice": q(0, 300)}, "the Ncpu quota of alice must be at least 1"),
    ({"alice": q(1, 249)}, "the RAM quota of alice must be at least 250"),
    ({"alice": q(2.5, 300)}, "the Ncpu quota of alice must be an integer"),
    ({"alice": q("2", 300)}, "the Ncpu quota of alice must be an integer"),
    ({"alice": q(2, True)}, "the RAM quota of alice must be an integer"),
    ({"alice": q(2, None)}, "the RAM quota of alice must be an integer"),
])
def test_invalidquotas_rejects_malformed_quotas(quotas, error):
    assert error in Mutil.invalidquotas(quotas, NODE)


def test_readquotas_without_the_file_means_no_quotas(tmp_path):
    assert Mutil.readquotas(str(tmp_path / "quotas"), NODE) == {}


def test_readquotas(tmp_path):
    quotas = {"alice": q(2, 500), "bob": q(3, 600)}
    (tmp_path / "quotas.mns").write_text(json.dumps(quotas))
    assert Mutil.readquotas(str(tmp_path / "quotas"), NODE) == quotas


@pytest.mark.parametrize("text", [
    "{not json", "", '{"alice": 2}', '{"alice": {"Ncpu": 1, "RAM": 10}}'])
def test_readquotas_rejects_malformed_files(tmp_path, text):
    (tmp_path / "quotas.mns").write_text(text)
    with pytest.raises(ValueError):
        Mutil.readquotas(str(tmp_path / "quotas"), NODE)


# ---------------------------------------------------------------------------
# the quota of each user
# ---------------------------------------------------------------------------

def test_no_quotas_means_no_limit():
    assert Mutil.userquota("alice", {}) is None


def test_listed_user_has_their_quota():
    assert Mutil.userquota("bob", {"alice": q(2, 300),
                                   "bob": q(3, 800)}) == q(3, 800)


def test_new_user_inherits_the_smallest_cpus_and_the_smallest_ram():
    quotas = {"alice": q(2, 800), "bob": q(4, 300)}
    assert Mutil.userquota("carol", quotas) == q(2, 300)


def test_admin_changes_the_quota_of_a_new_user_by_listing_them():
    quotas = {"alice": q(2, 500), "carol": q(3, 900)}
    assert Mutil.userquota("carol", quotas) == q(3, 900)
    assert Mutil.userquota("dave", quotas) == q(2, 500)


def test_describequotas():
    assert Mutil.describequotas({}) == "no quotas"
    assert Mutil.describequotas({"alice": q(2, 800), "bob": q(4, 300)}) == \
        "alice 2 cpus 800 MB, bob 4 cpus 300 MB, other users 2 cpus 300 MB"


# ---------------------------------------------------------------------------
# used resources
# ---------------------------------------------------------------------------

def test_usedresources_counts_the_running_jobs_of_each_user():
    charge = {"1": job(user="alice", status="run", Ncpu=2, RAM=300),
              "2": job(user="alice", status="run", Ncpu=1, RAM=100),
              "3": job(user="bob", status="run", Ncpu=1, RAM=50),
              "4": job(user="bob", status="que", Ncpu=3),
              "5": job(user="carol", status="que", Ncpu=1)}
    assert Mutil.usedresources(charge) == {"alice": q(3, 400),
                                           "bob": q(1, 50)}


def test_usedresources_on_idle_node():
    assert Mutil.usedresources({}) == {}


# ---------------------------------------------------------------------------
# submission checks
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("fields, quotas, error", [
    ({"Ncpu": 4, "RAM": 1000}, {}, None),
    ({"Ncpu": 2, "RAM": 500}, {"alice": q(2, 500)}, None),
    ({"Ncpu": 3}, {"alice": q(2, 500)}, "Ncpu 3 exceeds the quota of alice (2)"),
    ({"RAM": 600}, {"alice": q(2, 500)}, "RAM 600 exceeds the quota of alice (500)"),
    ({"Ncpu": 3, "RAM": 900, "force": True}, {"alice": q(2, 500)}, None),
    ({"Ncpu": 3, "force": False}, {"alice": q(2, 500)}, "exceeds the quota"),
    # a new user has the smallest quota
    ({"Ncpu": 2}, {"bob": q(1, 900), "carol": q(3, 900)},
     "Ncpu 2 exceeds the quota of alice (1)"),
    ({"RAM": 400}, {"bob": q(1, 900), "carol": q(3, 300)},
     "RAM 400 exceeds the quota of alice (300)"),
])
def test_overquota(fields, quotas, error):
    result = Mutil.overquota(job(user="alice", **fields), quotas)
    if error is None:
        assert result is None
    else:
        assert error in result


@pytest.mark.parametrize("force", ["yes", 1, None])
def test_invalidjob_rejects_a_malformed_force_flag(force):
    request = job(force=force)
    assert Mutil.invalidjob(request, NODE) == "force must be true or false"


@pytest.mark.parametrize("fields", [{}, {"force": True}, {"force": False}])
def test_invalidjob_accepts_the_force_flag(fields):
    assert Mutil.invalidjob(job(**fields), NODE) is None


def submitjobs(box, quotas):
    Mutil.submitjobs(box.rdir, "subjob", box.base("charge"),
                     box.base("status"), box.read("nodes"),
                     box.base("messages"), quotas)


@pytest.mark.parametrize("fields, error", [
    ({"Ncpu": 3}, f"rejected: Ncpu 3 exceeds the quota of {ME} (2)"),
    ({"RAM": 600}, f"rejected: RAM 600 exceeds the quota of {ME} (500)"),
])
def test_submitjobs_rejects_jobs_over_the_quota(sandbox, fields, error):
    sandbox.request("subjob1", job(user="forged", **fields))
    submitjobs(sandbox, {ME: q(2, 500)})
    assert sandbox.read("charge") == {}
    assert sandbox.pending("subjob") == []
    assert error in sandbox.messages()


def test_submitjobs_queues_jobs_within_the_quota(sandbox):
    sandbox.request("subjob1", job(Ncpu=2, RAM=500))
    sandbox.request("subjob2", job(Ncpu=2, RAM=500))
    submitjobs(sandbox, {ME: q(2, 500)})
    assert list(sandbox.read("charge")) == ["1", "2"]


def test_submitjobs_queues_forced_jobs_over_the_quota(sandbox):
    sandbox.request("subjob1", job(Ncpu=4, RAM=1000, force=True))
    submitjobs(sandbox, {ME: q(2, 500)})
    assert sandbox.read("charge")["1"]["force"] is True


def test_submitjobs_new_user_has_the_smallest_quota(sandbox):
    sandbox.request("subjob1", job(Ncpu=1, RAM=400))
    submitjobs(sandbox, {"somebody": q(1, 900), "someoneelse": q(4, 300)})
    assert sandbox.read("charge") == {}
    assert "RAM 400 exceeds the quota" in sandbox.messages()


# ---------------------------------------------------------------------------
# scheduling
# ---------------------------------------------------------------------------

def test_scheduling_without_quotas_is_unchanged():
    queue = {"1": job(Ncpu=2), "2": job(Ncpu=2), "3": job(Ncpu=1)}
    assert schedule(queue) == ["1", "2"]
    assert schedule(queue, {}, {}) == ["1", "2"]


def test_running_jobs_do_not_exceed_the_cpu_quota():
    queue = {"1": job(Ncpu=1), "2": job(Ncpu=1), "3": job(Ncpu=1)}
    assert schedule(queue, {"alice": q(2, 1000)}) == ["1", "2"]


def test_running_jobs_do_not_exceed_the_ram_quota():
    queue = {"1": job(RAM=300), "2": job(RAM=300), "3": job(RAM=300)}
    assert schedule(queue, {"alice": q(4, 600)}) == ["1", "2"]


def test_quota_counts_the_jobs_already_running():
    queue = {"1": job(Ncpu=1, RAM=100), "2": job(Ncpu=1, RAM=100)}
    quotas = {"alice": q(2, 500)}
    assert schedule(queue, quotas, {"alice": q(1, 100)}) == ["1"]
    assert schedule(queue, quotas, {"alice": q(2, 100)}) == []
    assert schedule(queue, quotas, {"alice": q(0, 450)}) == []


def test_schedule_does_not_change_the_used_resources():
    used = {"alice": q(1, 100)}
    schedule({"1": job()}, {"alice": q(2, 500)}, used)
    assert used == {"alice": q(1, 100)}


def test_quota_ignores_the_jobs_of_other_users():
    queue = {"1": job(Ncpu=2, RAM=500)}
    assert schedule(queue, {"alice": q(2, 500)}, {"bob": q(2, 500)}) == ["1"]


def test_user_over_the_quota_does_not_block_the_others():
    # alice's job is first, but it waits for her own jobs, not for the node
    queue = {"1": job(user="alice", Ncpu=2, priority=90),
             "2": job(user="bob", Ncpu=2, priority=10)}
    quotas = {"alice": q(2, 500), "bob": q(2, 500)}
    assert schedule(queue, quotas, {"alice": q(1, 100)}) == ["2"]


@pytest.mark.parametrize("big, used", [
    ({"Ncpu": 2}, q(2, 0)),     # waiting for cpus
    ({"RAM": 400}, q(0, 400)),  # waiting for RAM
])
def test_job_waiting_for_the_quota_blocks_the_later_jobs_of_its_user(big, used):
    # Otherwise a stream of small jobs could starve the big one, as on the node.
    queue = {"big": job(priority=90, **big),
             "small": job(Ncpu=1, RAM=100, priority=10),
             "other": job(user="bob", Ncpu=1, priority=5)}
    quotas = {"alice": q(3, 700), "bob": q(3, 700)}
    assert schedule(queue, quotas, {"alice": used}) == ["other"]


def test_job_bigger_than_a_lowered_quota_does_not_hold_its_user():
    # Queued when the quota was larger: it waits until the admin raises it.
    queue = {"big": job(Ncpu=4, priority=90), "small": job(Ncpu=1),
             "fat": job(RAM=900, priority=80)}
    assert schedule(queue, {"alice": q(2, 500)}) == ["small"]


def test_new_user_is_scheduled_with_the_smallest_quota():
    queue = {"1": job(user="carol", RAM=300), "2": job(user="carol", RAM=300)}
    assert schedule(queue, {"alice": q(1, 900), "bob": q(3, 400)}) == ["1"]


def test_quota_larger_than_the_node_is_no_limit():
    queue = {"1": job(Ncpu=4, RAM=1000)}
    assert schedule(queue, {"alice": q(64, 99999)}) == ["1"]


def test_resources_still_block_the_jobs_after_a_waiting_one():
    queue = {"big": job(user="bob", Ncpu=4, priority=90),
             "small": job(Ncpu=1, priority=10)}
    assert schedule(queue, {"alice": q(2, 500), "bob": q(4, 1000)},
                    available={**NODE, "Ncpu": 3}) == []


def test_forced_job_ignores_the_quota():
    queue = {"forced": job(Ncpu=3, RAM=900, force=True)}
    assert schedule(queue, {"alice": q(1, 250)}, {"alice": q(1, 250)}) == \
        ["forced"]


def test_forced_job_runs_in_order_of_priority():
    queue = {"forced": job(Ncpu=3, force=True, priority=90),
             "other": job(user="bob", Ncpu=2, priority=10)}
    quotas = {"alice": q(1, 250), "bob": q(2, 500)}
    # the forced job comes first, and bob waits for the node
    assert schedule(queue, quotas) == ["forced"]
    queue["forced"]["priority"] = 5
    assert schedule(queue, quotas) == ["other"]


def test_forced_job_waiting_for_the_node_blocks_the_jobs_after_it():
    queue = {"forced": job(Ncpu=4, force=True, priority=90),
             "other": job(user="bob", Ncpu=1, priority=10)}
    assert schedule(queue, {"alice": q(1, 250), "bob": q(1, 250)},
                    available={**NODE, "Ncpu": 3}) == []


def test_forced_job_counts_in_the_resources_of_its_user():
    queue = {"forced": job(Ncpu=2, force=True, priority=90),
             "ordinary": job(Ncpu=1, priority=10)}
    assert schedule(queue, {"alice": q(2, 500)}) == ["forced"]


def test_force_needs_a_boolean():
    # A hand-written "force": "yes" must not bypass the quota.
    queue = {"1": job(Ncpu=3, force="yes")}
    assert schedule(queue, {"alice": q(2, 500)}) == []


# ---------------------------------------------------------------------------
# splitting the node
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("nusers, quota", [
    (1, q(4, 1000)),
    (2, q(2, 500)),
    # one cpu is left over; the RAM is still split equally
    (3, q(1, 333)),
    (4, q(1, 250)),
    # more users than cpus: each has the minimum
    (8, q(1, 250)),
])
def test_splitquotas_shares_the_node_equally(nusers, quota):
    users = [f"user{i}" for i in range(nusers)]
    quotas = Mutil.splitquotas(users, NODE)
    assert quotas == {user: quota for user in users}
    assert Mutil.invalidquotas(quotas, NODE) is None


def test_splitquotas_without_users():
    assert Mutil.splitquotas([], NODE) == {}


@pytest.mark.parametrize("cpus, nusers, ram", [
    (1, 2, 500),    # an equal share of the RAM
    (3, 2, 750),    # but at least the RAM of the cpus
    (1, 8, 250),    # which is at least the minimum
    (8, 2, 1000),   # and at most the node
])
def test_shareram(cpus, nusers, ram):
    assert Mutil.shareram(cpus, nusers, NODE) == ram


def test_machineusers_are_people_not_system_accounts():
    for user in Mutil.machineusers():
        entry = pwd.getpwnam(user)
        assert 1000 <= entry.pw_uid <= 60000
        assert not entry.pw_shell.endswith(("nologin", "false"))


@needs_server
def test_machineusers_lists_the_users_of_the_server():
    assert Mutil.machineusers() == ["alice", "bob"]


@needs_server
def test_machineusers_follows_login_defs(tmp_path):
    defs = tmp_path / "login.defs"
    bob = pwd.getpwnam("bob").pw_uid
    defs.write_text(f"# comment\nUID_MIN\t\t {bob}\nUID_MAX {bob}\n")
    assert Mutil.machineusers(str(defs)) == ["bob"]
    assert Mutil.machineusers(str(tmp_path / "missing")) == ["alice", "bob"]


# ---------------------------------------------------------------------------
# reloading the quotas in the daemon
# ---------------------------------------------------------------------------

def load(box, loaded=(None, {})):
    return Mutil.loadquotas(box.base("quotas"), box.read("nodes"), loaded,
                            box.base("messages"))


def test_loadquotas_reads_the_file(sandbox):
    sandbox.write("quotas", {"alice": q(2, 500)})
    assert load(sandbox)[1] == {"alice": q(2, 500)}
    assert "Quotas: alice 2 cpus 500 MB, other users 2 cpus 500 MB" in \
        sandbox.messages()


def test_loadquotas_without_the_file(sandbox):
    sandbox.path("quotas").unlink()
    assert load(sandbox)[1] == {}
    assert "Quotas: no quotas" in sandbox.messages()


def test_loadquotas_follows_the_changes_of_the_file(sandbox):
    sandbox.write("quotas", {"alice": q(2, 500)})
    loaded = load(sandbox)
    sandbox.write("quotas", {"alice": q(3, 500)})
    loaded = load(sandbox, loaded)
    assert loaded[1] == {"alice": q(3, 500)}
    sandbox.path("quotas").unlink()
    assert load(sandbox, loaded)[1] == {}


def test_loadquotas_reports_only_changes(sandbox):
    sandbox.write("quotas", {"alice": q(2, 500)})
    loaded = load(sandbox)
    for _ in range(3):
        loaded = load(sandbox, loaded)
    assert sandbox.messages().count("Quotas:") == 1


def test_loadquotas_keeps_the_previous_quotas_if_the_file_is_malformed(sandbox):
    sandbox.write("quotas", {"alice": q(2, 500)})
    loaded = load(sandbox)
    sandbox.path("quotas").write_text('{"alice": ')
    for _ in range(3):
        loaded = load(sandbox, loaded)
        assert loaded[1] == {"alice": q(2, 500)}
    assert sandbox.messages().count("WARNING:quotas.mns ignored") == 1
    sandbox.write("quotas", {"alice": q(1, 300)})
    assert load(sandbox, loaded)[1] == {"alice": q(1, 300)}


def test_loadquotas_refuses_quotas_below_the_minimum(sandbox):
    sandbox.write("quotas", {"alice": q(0, 500)})
    assert load(sandbox)[1] == {}
    assert "the Ncpu quota of alice must be at least 1" in sandbox.messages()


# ---------------------------------------------------------------------------
# msub and mstat
# ---------------------------------------------------------------------------

def submitted(box):
    files = box.pending("subjob")
    assert len(files) == 1, files
    return json.loads(files[0].read_text())


@pytest.mark.parametrize("args, error", [
    (["-c", 3, "-m", 100], f"Ncpu 3 exceeds the quota of {ME} (2)"),
    (["-c", 1, "-m", 600], f"RAM 600 exceeds the quota of {ME} (500)"),
])
def test_msub_refuses_a_job_over_the_quota(sandbox, args, error):
    sandbox.write("quotas", {ME: q(2, 500)})
    result = sandbox.run("Msub", "-f", "/jobs/a.sh", *args)
    assert result.returncode != 0
    assert error in result.stderr
    assert "--force" in result.stderr
    assert "Traceback" not in result.stderr
    assert sandbox.pending("subjob") == []


def test_msub_accepts_jobs_within_the_quota(sandbox):
    sandbox.write("quotas", {ME: q(2, 500)})
    result = sandbox.run("Msub", "-f", "/jobs/a.sh", "-c", 2, "-m", 500)
    assert result.returncode == 0, result.stderr
    assert submitted(sandbox)["force"] is False


def test_msub_default_ram_is_at_most_the_quota(sandbox):
    # The default is all the RAM of the node, which the quota would refuse.
    sandbox.write("quotas", {ME: q(2, 500)})
    result = sandbox.run("Msub", "-f", "/jobs/a.sh")
    assert result.returncode == 0, result.stderr
    assert submitted(sandbox)["RAM"] == 500


def test_msub_default_ram_of_a_forced_job_is_the_default(sandbox):
    sandbox.write("quotas", {ME: q(2, 500)})
    result = sandbox.run("Msub", "-f", "/jobs/a.sh", "--force")
    assert result.returncode == 0, result.stderr
    assert submitted(sandbox)["RAM"] == sandbox.read("defaults")["RAM"]


def test_msub_new_user_has_the_smallest_quota(sandbox):
    sandbox.write("quotas", {"somebody": q(1, 900), "someoneelse": q(4, 300)})
    result = sandbox.run("Msub", "-f", "/jobs/a.sh", "-c", 1, "-m", 400)
    assert f"RAM 400 exceeds the quota of {ME} (300)" in result.stderr


def test_msub_force_accepts_a_job_over_the_quota(sandbox):
    sandbox.write("quotas", {ME: q(2, 500)})
    result = sandbox.run("Msub", "-f", "/jobs/a.sh", "-c", 4, "-m", 1000,
                         "--force")
    assert result.returncode == 0, result.stderr
    assert submitted(sandbox)["force"] is True


def test_msub_force_does_not_accept_jobs_bigger_than_the_node(sandbox):
    result = sandbox.run("Msub", "-f", "/jobs/a.sh", "-c", 5, "--force")
    assert result.returncode != 0
    assert "Ncpu 5 exceeds the node (4)" in result.stderr


@pytest.mark.parametrize("text", ["{not json", '{"x": {"Ncpu": 0, "RAM": 1}}'])
def test_msub_leaves_a_malformed_quotas_file_to_the_daemon(sandbox, text):
    # The daemon keeps the previous quotas, which msub cannot know.
    sandbox.path("quotas").write_text(text)
    result = sandbox.run("Msub", "-f", "/jobs/a.sh", "-c", 4)
    assert result.returncode == 0, result.stderr


def test_msub_without_a_quotas_file(sandbox):
    # an installation upgraded from 2.0.0
    sandbox.path("quotas").unlink()
    result = sandbox.run("Msub", "-f", "/jobs/a.sh", "-c", 4)
    assert result.returncode == 0, result.stderr


def test_mstat_quotas_without_quotas(sandbox):
    result = sandbox.run("Mstat", "-q")
    assert result.returncode == 0, result.stderr
    assert "No quotas" in result.stdout


def test_mstat_quotas_shows_used_resources_and_quotas(sandbox):
    sandbox.write("quotas", {"alice": q(2, 500), "bob": q(3, 300)})
    sandbox.write("charge", {
        "1": job(user="alice", status="run", pid=1, Ncpu=2, RAM=400),
        "2": job(user="carol", status="run", pid=2, Ncpu=1, RAM=100),
        "3": job(user="bob", status="que", Ncpu=3)})
    result = sandbox.run("Mstat", "--quotas")
    assert result.returncode == 0, result.stderr
    rows = [line.split() for line in result.stdout.splitlines()]
    assert ["alice", "2/2", "400/500"] in rows
    assert ["bob", "0/3", "0/300"] in rows
    assert ["carol", "1/2", "100/300"] in rows
    assert ["other", "users", "-/2", "-/300"] in rows


def test_mstat_quotas_with_a_malformed_file(sandbox):
    sandbox.path("quotas").write_text("{not json")
    result = sandbox.run("Mstat", "-q")
    assert result.returncode == 0, result.stderr
    assert "The quotas file is malformed" in result.stdout


def test_mstat_verbose_shows_forced_jobs(sandbox):
    sandbox.write("charge", {"1": job(force=True), "2": job()})
    result = sandbox.run("Mstat", "-v")
    assert result.stdout.count("force: yes") == 1
    assert result.stdout.count("force: no") == 1


# ---------------------------------------------------------------------------
# the daemon
# ---------------------------------------------------------------------------

def msub(box, script, *args, user="alice"):
    result = box.run("Msub", "-f", script, *args, user=user)
    assert result.returncode == 0, result.stderr


@needs_server
def test_daemon_keeps_the_running_jobs_within_the_cpu_quota(sandbox, daemon):
    sandbox.write("quotas", {"alice": q(2, 1000), "bob": q(4, 1000)})
    for name in ("a1", "a2", "a3"):
        msub(sandbox, sandbox.job_script(name, 5), "-c", 1, "-m", 100)
    daemon.wait_for(lambda: sandbox.started_by("a1") and
                    sandbox.started_by("a2"), "two jobs of alice to start")
    # bob is not held up by the job alice has waiting
    msub(sandbox, sandbox.job_script("b", 3), "-c", 1, "-m", 100, user="bob")
    daemon.wait_for(lambda: sandbox.started_by("b"), "the job of bob to start")
    assert sandbox.started_by("a3") is None, "alice went over her quota"
    daemon.wait_for(lambda: sandbox.started_by("a3"),
                    "the third job of alice to start", timeout=15)
    assert sandbox.done("a1") or sandbox.done("a2")


@needs_server
def test_daemon_keeps_the_running_jobs_within_the_ram_quota(sandbox, daemon):
    sandbox.write("quotas", {"alice": q(4, 500), "bob": q(4, 1000)})
    msub(sandbox, sandbox.job_script("a1", 4), "-c", 1, "-m", 300)
    msub(sandbox, sandbox.job_script("a2", 0), "-c", 1, "-m", 300)
    daemon.wait_for(lambda: sandbox.started_by("a1"), "a1 to start")
    time.sleep(1)
    assert sandbox.started_by("a2") is None, "alice went over her RAM quota"
    daemon.wait_for(lambda: sandbox.started_by("a2"), "a2 to start",
                    timeout=15)


@needs_server
def test_daemon_gives_a_new_user_the_smallest_quota(sandbox, daemon):
    sandbox.write("quotas", {"bob": q(1, 1000), "carol": q(3, 1000)})
    msub(sandbox, sandbox.job_script("a1", 4), "-c", 1, "-m", 100)
    msub(sandbox, sandbox.job_script("a2", 0), "-c", 1, "-m", 100)
    daemon.wait_for(lambda: sandbox.started_by("a1"), "a1 to start")
    time.sleep(1)
    assert sandbox.started_by("a2") is None, "alice went over the quota"
    daemon.wait_for(lambda: sandbox.started_by("a2"), "a2 to start",
                    timeout=15)


@needs_server
def test_daemon_rejects_a_forged_request_over_the_quota(sandbox, daemon):
    sandbox.write("quotas", {"alice": q(1, 250)})
    sandbox.request("subjob1", {"script": "/bin/true", "Ncpu": 1, "RAM": 300,
                                "HDmemory": 0, "priority": 50},
                    owner="alice")
    daemon.wait_for(lambda: "rejected" in sandbox.messages(),
                    "the request to be rejected")
    assert sandbox.read("charge") == {}
    assert "RAM 300 exceeds the quota of alice (250)" in sandbox.messages()


@needs_server
def test_daemon_runs_a_forced_job_beyond_the_quota(sandbox, daemon):
    sandbox.write("quotas", {"alice": q(1, 250), "bob": q(4, 1000)})
    msub(sandbox, sandbox.job_script("forced", 3), "-c", 3, "-m", 800,
         "--force")
    daemon.wait_for(lambda: sandbox.started_by("forced"),
                    "the forced job to start")
    msub(sandbox, sandbox.job_script("b", 0), "-c", 1, "-m", 100, user="bob")
    daemon.wait_for(lambda: sandbox.started_by("b"), "the job of bob to start")


@needs_server
def test_daemon_follows_the_changes_of_the_quotas(sandbox, daemon):
    sandbox.write("quotas", {"alice": q(1, 250)})
    daemon.wait_for(lambda: "Quotas: alice 1 cpus 250 MB" in sandbox.messages(),
                    "the daemon to read the quotas")
    sandbox.request("subjob1", {"script": str(sandbox.job_script("a")),
                                "Ncpu": 2, "RAM": 100, "HDmemory": 0,
                                "priority": 50, "force": False},
                    owner="alice")
    daemon.wait_for(lambda: "exceeds the quota of alice (1)"
                    in sandbox.messages(), "the request to be rejected")
    sandbox.write("quotas", {"alice": q(2, 250)})
    daemon.wait_for(lambda: "Quotas: alice 2 cpus" in sandbox.messages(),
                    "the daemon to reread the quotas")
    msub(sandbox, sandbox.job_script("a"), "-c", 2, "-m", 100)
    daemon.wait_for(lambda: sandbox.started_by("a"), "job a to start")


@needs_server
def test_daemon_survives_a_malformed_quotas_file(sandbox, daemon):
    sandbox.write("quotas", {"alice": q(1, 1000)})
    daemon.wait_for(lambda: "Quotas: alice 1 cpus" in sandbox.messages(),
                    "the daemon to read the quotas")
    sandbox.path("quotas").write_text("{oops")
    daemon.wait_for(lambda: "quotas.mns ignored" in sandbox.messages(),
                    "the malformed file to be reported")
    msub(sandbox, sandbox.job_script("a1", 4), "-c", 1, "-m", 100)
    msub(sandbox, sandbox.job_script("a2", 0), "-c", 1, "-m", 100)
    daemon.wait_for(lambda: sandbox.started_by("a1"), "a1 to start")
    time.sleep(1)
    # the previous quota still holds
    assert sandbox.started_by("a2") is None
    assert daemon.alive()
