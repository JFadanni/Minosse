"""Shared fixtures for the Minosse test suite.

The tests are meant to run inside the simulated server built from
Tests/container/Containerfile (see Tests/run_tests.sh).  Unit and CLI tests
also run on any Linux host with pytest; daemon and installer tests need
root, runuser and the test users, and are skipped elsewhere.
"""

import json
import os
import pwd
import shutil
import signal
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import pytest

SRC = Path(__file__).resolve().parent.parent
UTILS = SRC / "Utils"
sys.path.insert(0, str(UTILS))

TOOLS = ("Minosse", "Msub", "Mstat", "Mdel", "Mutil")
TEST_USERS = ("alice", "bob")
NODE = {"Ncpu": 4, "RAM": 1000, "HDmemory": 10}


def _user_exists(name):
    try:
        pwd.getpwnam(name)
    except KeyError:
        return False
    return True


ON_SERVER = (os.geteuid() == 0 and shutil.which("runuser") is not None
             and all(_user_exists(u) for u in TEST_USERS))

needs_server = pytest.mark.skipif(
    not ON_SERVER,
    reason="needs the simulated server (root, runuser, test users): "
           "run Tests/run_tests.sh")


def job(**fields):
    """A charge.mns entry with the fields the daemon reads."""
    base = {"user": "alice", "script": "/jobs/a.sh", "status": "que",
            "priority": 50, "Ncpu": 1, "RAM": 100, "HDmemory": 0,
            "pid": "", "runtime": "", "subtime": "01/01/26 00.00.00"}
    base.update(fields)
    return base


def process_alive(pid):
    """True if pid exists and is not a zombie."""
    try:
        with open(f"/proc/{pid}/stat") as stat:
            return stat.read().rsplit(")", 1)[1].split()[0] != "Z"
    except FileNotFoundError:
        return False


def wait_until(predicate, timeout=10.0, interval=0.1):
    """Poll predicate until it returns a truthy value or timeout expires."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        result = predicate()
        if result:
            return result
        time.sleep(interval)
    return predicate()


class Sandbox:
    """A Minosse installation in a world-writable temporary directory.

    Mirrors what minosse_config.sh + minosse_install.sh produce: the Utils
    scripts with "$instdir" substituted, and the initial .mns files.
    """

    def __init__(self, root, node=NODE):
        self.dir = Path(root)
        self.mdir = f"{self.dir}/"
        self.requests = self.dir / "requests"
        self.requests.mkdir()
        self.jobs = self.dir / "jobs"
        self.jobs.mkdir()
        os.chmod(self.dir, 0o755)
        os.chmod(self.requests, 0o1777)
        os.chmod(self.jobs, 0o777)
        for tool in TOOLS:
            text = (UTILS / f"{tool}.py").read_text()
            target = self.script(tool)
            target.write_text(text.replace("$instdir", str(self.dir)))
            os.chmod(target, 0o755)
        hostname = os.uname().nodename
        arch = os.uname().machine
        self.write("charge", {})
        self.write("conf", {"status": "down"})
        self.write("delete", {})
        self.write("nodes", {"NODE": "none", "hostname": hostname,
                             "Ncpu": node["Ncpu"], "RAM": node["RAM"],
                             "HDmemory": node["HDmemory"],
                             "architecture": arch, "status": "up",
                             "priority": 50})
        self.write("defaults", {"hostname": hostname, "Ncpu": 1,
                                "RAM": node["RAM"], "HDmemory": 0,
                                "architecture": arch, "status": "que",
                                "priority": 50})
        self.write("status", {"NODE": "none", "hostname": hostname,
                              "Ncpu": 0, "RAM": 0, "HDmemory": 0,
                              "architecture": arch, "status": "up",
                              "priority": 50})

    def path(self, name):
        return self.dir / f"{name}.mns"

    def base(self, name):
        """Path without extension, as Mutil.readallfile/writeallfile expect."""
        return f"{self.dir}/{name}"

    def read(self, name):
        # The daemon rewrites files in place, so a read can see a
        # half-written file; retry briefly before giving up.
        for _ in range(20):
            try:
                return json.loads(self.path(name).read_text())
            except json.JSONDecodeError:
                time.sleep(0.05)
        return json.loads(self.path(name).read_text())

    def write(self, name, data):
        self.path(name).write_text(json.dumps(data, indent=2))

    def script(self, tool):
        return self.dir / f"{tool}.py"

    def messages(self):
        log = self.dir / "messages"
        return log.read_text() if log.exists() else ""

    @property
    def rdir(self):
        """The request directory, as Mutil.writejob expects it."""
        return f"{self.requests}/"

    def request(self, name, data, owner=None):
        """Drop a request file, as msub/mdel do, owned by owner."""
        path = self.requests / f"{name}.mns"
        path.write_text(json.dumps(data))
        if owner:
            os.chown(path, pwd.getpwnam(owner).pw_uid, -1)
        return path

    def pending(self, prefix):
        """The subjob*/remove* request files waiting to be picked up."""
        return sorted(self.requests.glob(f"{prefix}*.mns"))

    def run(self, tool, *args, user=None, env=None):
        cmd = [sys.executable, str(self.script(tool)), *map(str, args)]
        if user:
            cmd = ["runuser", "-u", user, "--", *cmd]
        return subprocess.run(cmd, capture_output=True, text=True,
                              timeout=30, env=env)

    def job_script(self, name, seconds=0):
        """A job that records who ran it, sleeps, then records completion."""
        script = self.jobs / f"{name}.sh"
        script.write_text(
            "#!/bin/bash\n"
            f"echo $$ > {self.jobs}/{name}.pid\n"
            f"id -un > {self.jobs}/{name}.started\n"
            f"sleep {seconds}\n"
            f"touch {self.jobs}/{name}.done\n")
        os.chmod(script, 0o755)
        return script

    def started_by(self, name):
        marker = self.jobs / f"{name}.started"
        return marker.read_text().strip() if marker.exists() else None

    def done(self, name):
        return (self.jobs / f"{name}.done").exists()

    def job_pid(self, name):
        marker = self.jobs / f"{name}.pid"
        return int(marker.read_text()) if marker.exists() else None

    def find_job(self, script):
        """The (id, entry) of the charge.mns job running script, if any."""
        for jobid, entry in self.read("charge").items():
            if entry["script"] == str(script):
                return jobid, entry
        return None

    def kill_everything(self):
        """Kill any process (daemon, jobs, fakes) whose command line
        mentions this sandbox."""
        subprocess.run(["pkill", "-KILL", "-f", str(self.dir)],
                       capture_output=True)


@pytest.fixture
def sandbox():
    root = tempfile.mkdtemp(prefix="minosse-")
    box = Sandbox(root)
    yield box
    box.kill_everything()
    shutil.rmtree(root, ignore_errors=True)


@pytest.fixture
def fake_daemon(sandbox):
    """A sleeping process that ifrunning() recognises as the daemon of the
    sandbox, so that tools guarded by ifrunning() can be exercised."""
    # ifrunning() matches "<Mdir>Minosse.py", so the fake replaces it.
    script = sandbox.script("Minosse")
    script.write_text("import time\ntime.sleep(120)\n")
    proc = subprocess.Popen([sys.executable, str(script)])
    yield proc
    proc.kill()
    proc.wait()


class Daemon:
    """The real Minosse.py daemon running on a sandbox."""

    def __init__(self, box, *args):
        self.box = box
        self.log = box.dir / "daemon.log"
        with open(self.log, "w") as log:
            self.proc = subprocess.Popen(
                [sys.executable, str(box.script("Minosse")), *args],
                cwd=box.dir, stdout=log, stderr=subprocess.STDOUT,
                start_new_session=True)

    def alive(self):
        return self.proc.poll() is None

    def wait_for(self, predicate, what, timeout=10.0):
        """Wait for predicate; fail fast with the daemon log if it dies."""
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            result = predicate()
            if result:
                return result
            if not self.alive():
                result = predicate()
                if result:
                    return result
                pytest.fail(f"daemon died while waiting for {what}:\n"
                            f"{self.log.read_text()}")
            time.sleep(0.2)
        pytest.fail(f"timed out waiting for {what}\n"
                    f"daemon log:\n{self.log.read_text()}\n"
                    f"messages:\n{self.box.messages()}")

    def stop(self):
        if self.alive():
            os.killpg(self.proc.pid, signal.SIGKILL)
        self.proc.wait()


@pytest.fixture
def daemon(sandbox):
    """A daemon that has finished its start-up clean-up, which deletes any
    pending subjob files: submitting earlier would lose the job."""
    d = Daemon(sandbox)
    d.wait_for(lambda: sandbox.read("conf") == {"status": "up"},
               "the daemon to initialise")
    yield d
    d.stop()
