"""Tests of minosse quota (Mquota.py), the tool root sets the quotas with.

The sandbox node has 4 cpus and 1000 MB of RAM, so a quota is at least
1 cpu and 250 MB.  On the simulated server the users of the machine are
alice and bob.
"""

import json
import subprocess

import pytest

from conftest import needs_server


def q(cpus, ram):
    return {"Ncpu": cpus, "RAM": ram}


def mquota(box, *args, answers="", user=None):
    cmd = [str(box.script("Mquota")), *map(str, args)]
    if user:
        cmd = ["runuser", "-u", user, "--", "python3", *cmd]
    else:
        cmd = ["python3", *cmd]
    return subprocess.run(cmd, input=answers, capture_output=True, text=True,
                          timeout=30)


def quotas_file(tmp_path, quotas):
    path = tmp_path / "quotas.json"
    path.write_text(json.dumps(quotas))
    return path


# ---------------------------------------------------------------------------
# without the users of the machine
# ---------------------------------------------------------------------------

def test_show_without_quotas(sandbox):
    result = mquota(sandbox, "--show")
    assert result.returncode == 0, result.stderr
    assert "No quotas" in result.stdout


def test_show(sandbox):
    sandbox.write("quotas", {"alice": q(2, 500), "bob": q(3, 300)})
    result = mquota(sandbox, "--show")
    rows = [line.split() for line in result.stdout.splitlines()]
    assert ["alice", "2", "500"] in rows
    assert ["other", "users", "2", "300"] in rows
    assert sandbox.read("quotas") == {"alice": q(2, 500), "bob": q(3, 300)}


def test_file(sandbox, tmp_path):
    quotas = {"alice": q(2, 500), "bob": q(1, 250)}
    result = mquota(sandbox, "--file", quotas_file(tmp_path, quotas),
                    "--yes")
    assert result.returncode == 0, result.stderr
    assert "Quotas written" in result.stdout
    assert sandbox.read("quotas") == quotas


@pytest.mark.parametrize("quotas, error", [
    ({"alice": q(0, 500)}, "the Ncpu quota of alice must be at least 1"),
    ({"alice": q(1, 100)}, "the RAM quota of alice must be at least 250"),
    ({"alice": 2}, "the quota of alice must give Ncpu and RAM"),
])
def test_file_with_invalid_quotas(sandbox, tmp_path, quotas, error):
    sandbox.write("quotas", {"bob": q(1, 250)})
    result = mquota(sandbox, "-f", quotas_file(tmp_path, quotas), "-y")
    assert result.returncode != 0
    assert error in result.stderr
    assert "no quotas written" in result.stderr
    assert sandbox.read("quotas") == {"bob": q(1, 250)}


def test_missing_file(sandbox, tmp_path):
    result = mquota(sandbox, "-f", tmp_path / "missing.json", "-y")
    assert result.returncode != 0
    assert "no quotas written" in result.stderr


def test_file_warns_about_unknown_users(sandbox, tmp_path):
    quotas = {"nosuchuser": q(1, 250)}
    result = mquota(sandbox, "-f", quotas_file(tmp_path, quotas), "-y")
    assert result.returncode == 0, result.stderr
    assert "Warning: nosuchuser is not a user of this machine" in result.stdout
    assert sandbox.read("quotas") == quotas


@pytest.mark.parametrize("answer, written", [
    ("\n", True), ("y\n", True), ("n\n", False), ("", False)])
def test_asks_before_writing(sandbox, tmp_path, answer, written):
    quotas = {"alice": q(2, 500)}
    result = mquota(sandbox, "-f", quotas_file(tmp_path, quotas),
                    answers=answer)
    assert "Write these quotas?" in result.stdout
    assert (sandbox.read("quotas") == quotas) is written
    assert (result.returncode == 0) is written


def test_clear(sandbox):
    sandbox.write("quotas", {"alice": q(2, 500)})
    result = mquota(sandbox, "--clear", "-y")
    assert result.returncode == 0, result.stderr
    assert sandbox.read("quotas") == {}


def test_written_quotas_are_readable_by_all(sandbox):
    mquota(sandbox, "--clear", "-y")
    assert sandbox.path("quotas").stat().st_mode & 0o777 == 0o644


def test_options_exclude_each_other(sandbox):
    result = mquota(sandbox, "--clear", "--split")
    assert result.returncode != 0
    assert "not allowed with" in result.stderr


# ---------------------------------------------------------------------------
# with the users of the machine
# ---------------------------------------------------------------------------

@needs_server
def test_only_root_can_set_the_quotas(sandbox):
    sandbox.write("quotas", {"alice": q(1, 250)})
    result = mquota(sandbox, "--clear", "-y", user="alice")
    assert result.returncode != 0
    assert "only root can set the quotas" in result.stderr
    assert sandbox.read("quotas") == {"alice": q(1, 250)}
    # but anybody can look at them
    result = mquota(sandbox, "--show", user="alice")
    assert result.returncode == 0, result.stderr


@needs_server
def test_split(sandbox):
    result = mquota(sandbox, "--split", "--yes")
    assert result.returncode == 0, result.stderr
    assert sandbox.read("quotas") == {"alice": q(2, 500), "bob": q(2, 500)}


@needs_server
def test_split_includes_users_given_a_quota_earlier(sandbox):
    # such as users of a network directory, which may not be listed
    sandbox.write("quotas", {"root": q(4, 1000), "nosuchuser": q(1, 250)})
    mquota(sandbox, "--split", "--yes")
    assert sandbox.read("quotas") == {
        "alice": q(1, 333), "bob": q(1, 333), "root": q(1, 333)}


@needs_server
def test_interactive_lists_the_users_and_splits_the_node(sandbox):
    result = mquota(sandbox, answers="\n\n")
    assert result.returncode == 0, result.stderr
    assert "Users of the machine: alice bob" in result.stdout
    assert "at least 1 cpu and 250 MB" in result.stdout
    assert "(2 cpus 500 MB each)" in result.stdout
    assert sandbox.read("quotas") == {"alice": q(2, 500), "bob": q(2, 500)}


@needs_server
def test_interactive_asks_the_quota_of_each_user(sandbox):
    # alice: 3 cpus, and the RAM that goes with them; bob: 1 cpu, 300 MB
    result = mquota(sandbox, answers="n\n3\n\n1\n300\n\n")
    assert result.returncode == 0, result.stderr
    assert "alice  RAM (MB) [750]" in result.stdout
    assert "bob  RAM (MB) [500]" in result.stdout
    assert sandbox.read("quotas") == {"alice": q(3, 750), "bob": q(1, 300)}


@needs_server
def test_interactive_asks_again_for_invalid_values(sandbox):
    result = mquota(sandbox, answers="n\n0\nabc\n2\n100\n\n\n\n\n")
    assert result.returncode == 0, result.stderr
    assert "at least 1, please" in result.stdout
    assert "a whole number, please" in result.stdout
    assert "at least 250, please" in result.stdout
    assert sandbox.read("quotas") == {"alice": q(2, 500), "bob": q(2, 500)}


@needs_server
def test_interactive_proposes_the_quotas_in_use(sandbox):
    sandbox.write("quotas", {"alice": q(3, 600)})
    result = mquota(sandbox, answers="n\n\n\n\n\n\n")
    assert "alice  cpus [3]" in result.stdout
    assert "alice  RAM (MB) [600]" in result.stdout
    assert sandbox.read("quotas") == {"alice": q(3, 600), "bob": q(2, 500)}


@needs_server
def test_interactive_stops_without_answers(sandbox):
    sandbox.write("quotas", {"alice": q(3, 600)})
    result = mquota(sandbox, answers="n\n2\n")
    assert result.returncode != 0
    assert "no quotas written" in result.stderr
    assert sandbox.read("quotas") == {"alice": q(3, 600)}
