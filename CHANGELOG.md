# Changelog

All notable changes to Minosse are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and Minosse follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html):
the version is kept in the `VERSION` file and each release is tagged `vX.Y.Z`.

## [2.0.0] - 2026-10-30

A rewrite of the demon and of the user commands, with a test suite.

### Upgrading from 1.x

- Stop Minosse, uninstall it, then configure and install 2.0.0 again: the
  installation layout and the format of the `.mns` files changed. Jobs queued
  under 1.x are not carried over.
- Job ids are now given by the demon and shown by `mstat`; `msub` no longer
  prints a random id.
- Scripts that call `msub` should check its exit status: requests that can
  never run are now refused.

### Added

- `minosse start` lists the jobs still waiting from the last run (queued, or
  submitted while the demon was down) and asks whether to keep them;
  `--keep` and `--delete` skip the question.
- `minosse version`, and `--version` for every command.
- Job chaining: `msub -l script` runs the job after the earlier job with that
  script has ended.
- A test suite running in a container that simulates the server
  (`Tests/run_tests.sh`).

### Changed

- The `.mns` files are JSON.
- Jobs start in strict priority order, first come first served at equal
  priority: a job that does not fit yet is no longer overtaken by smaller
  ones.
- Job ids are sequential and never reused.
- Jobs run in the directory of their script, in a session of their own.
- `minosse stop` keeps the queued jobs for the next start.
- `msub` refuses jobs that can never run (more CPUs, RAM or disk than the
  node, no CPU) and stores absolute script paths; `-f` is required.
- `mdel` requires `-j` or `-s`; `-a` is always in effect.
- Requests go to `<install directory>/requests`, the only directory users
  can write to.
- The command line options are parsed with `argparse`.

### Fixed

- The demon crashed on its first loop, and `mdel` on every call.
- Killing a job (`mdel`, `minosse stop`) left the programs it ran going.
- Ended jobs were not noticed, so their resources were never freed.
- At startup, the processes that reused the pids of old jobs were killed.
- A node whose work partition is under 1 GB never ran a job.
- Submissions sent while the demon was starting were lost.
- Malformed or hand-written requests crashed the demon or `mstat -v`.

### Security

- Any user could run commands as root: through the script name, the
  `$USER` variable, forged request files, or Python modules planted in the
  world-writable installation directory. Jobs now run through `runuser`
  without a shell, as the owner of the request file, and the installation
  directory is no longer writable by users.
- A forged request could make root kill any process.

### Removed

- The unused `getpid` and `chainjob` functions, and `header_docstring.txt`.

## [1.3.1] - 2023-11-24

## [1.3.0] - 2023-11-12

## [1.2.0] - 2023-10-20

## [1.1.0] - 2023-10-10

## [1.0.0] - 2023-09-25

[2.0.0]: https://github.com/JFadanni/Minosse/compare/v1.3.1...v2.0.0
[1.3.1]: https://github.com/JFadanni/Minosse/compare/v1.3.0...v1.3.1
[1.3.0]: https://github.com/JFadanni/Minosse/compare/v1.2.0...v1.3.0
[1.2.0]: https://github.com/JFadanni/Minosse/compare/v1.1.0...v1.2.0
[1.1.0]: https://github.com/JFadanni/Minosse/compare/v1.0.0...v1.1.0
[1.0.0]: https://github.com/JFadanni/Minosse/releases/tag/v1.0.0
