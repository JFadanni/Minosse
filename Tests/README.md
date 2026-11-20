# Minosse tests

## Running

```sh
Tests/run_tests.sh               # build the server image, run all tests
Tests/run_tests.sh -k daemon -x  # any pytest arguments
Tests/run_tests.sh shell         # root shell on the simulated server
```

Requires podman, or docker with `CONTAINER_ENGINE=docker`. The sources are
mounted read-only at `/src`, so edits are picked up without rebuilding the
image.

## Continuous integration

`.github/workflows/ci.yml` runs pylint, the unit and CLI tests on every
supported Python (3.8 and later), and the whole suite through `run_tests.sh`
on every push to `main` and `develop` and on every pull request.

## The simulated server

`container/Containerfile` describes a single Debian 12 workstation, the
setup Minosse targets:

- Python 3.11, `ps` (procps) and `runuser` (util-linux);
- the daemon runs as root, and the users `alice` and `bob` submit jobs;
- `/scratch` is a 2 GB tmpfs work partition for `minosse_config.sh`;
- `--init` gives the container an init that reaps orphans, as on a real
  machine.

## Layout

| File              | Covers                                                  | Needs server |
|-------------------|---------------------------------------------------------|--------------|
| `test_mutil.py`   | functions in `Utils/Mutil.py`                           | no           |
| `test_cli.py`     | `msub`, `mstat`, `mdel` run as subprocesses             | no           |
| `test_daemon.py`  | `Minosse.py` end to end: scheduling, deletion, stop, security | yes    |
| `test_install.py` | `minosse_config.sh`, `minosse_install.sh`, `minosse_uninst.sh` | yes   |

Tests that need the server are skipped elsewhere. Each test gets a *sandbox*
(`conftest.py`): a temporary directory laid out as the installer does it, with
the same `$instdir` substitution and the `.mns` files written by
`minosse_config.sh`. The sandbox node has 4 CPUs, 1000 MB of RAM and 10 GB of
disk.

## Known defects are `xfail`

A test marked `xfail` asserts the *intended* behaviour of code that is known
to be broken, and its reason names the defect (`BUG`, `DESIGN` or
`SECURITY`). `xfail_strict` is on, so once a defect is fixed its test reports
`XPASS(strict)` as a failure: remove the marker then.

`pytest --runxfail` ignores the markers and shows what still fails.
