
# **Minosse** version 2.0.0

[![CI](https://github.com/JFadanni/Minosse/actions/workflows/ci.yml/badge.svg)](https://github.com/JFadanni/Minosse/actions/workflows/ci.yml)

Minosse is a tiny batch system for a single Linux workstation or server.
Users submit job scripts; Minosse runs each one, as the user who submitted
it, as soon as the CPUs, RAM and disk it asks for are free.

Minosse is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

Minosse is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
[GNU General Public License](https://www.gnu.org/licenses/gpl-3.0.html) for more details.

You should have received a copy of the GNU General Public License
along with Minosse.  If not, see <http://www.gnu.org/licenses/>.

The changes between versions are listed in [CHANGELOG.md](CHANGELOG.md).
**Upgrading from 1.x?** Uninstall the old version and install 2.0.0 from
scratch, as described in [Upgrading from 1.x](#upgrading-from-1x).


## Requirements

- Linux, with `runuser` (util-linux) and `ps` (procps), present on every
  common distribution.
- Python 3.8 or later. No other packages are needed.
- Root access, to install Minosse and to run its demon.

This release works on a single workstation or server with any number of
processors (shared memory); there are no limits on the number of
processors, the RAM or the disk space.


## How to install

Two steps are needed, from the directory where you unpacked Minosse:

1. Run the configuration script, which describes your machine:

   ```sh
   ./minosse_config.sh
   ```

   It asks for:
   - the working partition, where the jobs write their temporary files,
     `/scratch` by default: its size is the disk space Minosse can give to
     jobs;
   - the RAM left to the operating system, 300 MB by default;
   - the priority of the node, 50 by default.

   The number of CPUs and the RAM are read from the machine.

2. Run the installer as root:

   ```sh
   sudo ./minosse_install.sh
   ```

   It asks for the installation directory (`/usr/local/Minosse` by
   default), the directory for the links to the commands (`/usr/local/bin`
   by default, which should be in the `$PATH` of the users) and whether to
   start the demon.

To uninstall Minosse, run `sudo minosse_uninst`: it stops the demon, which
kills the running jobs, and removes the installation directory and the
links.

### Upgrading from 1.x

The installation layout and the format of the Minosse files changed in
2.0.0, so:

1. wait for the running jobs to end, or note them down: they are killed;
2. uninstall the old version with `sudo minosse_uninst`;
3. configure and install 2.0.0 as above.

The jobs queued under 1.x are not carried over: submit them again.


## Configuration

The installation directory holds the description of the machine in
`nodes.mns`, written by `minosse_config.sh`, for example:

```json
{
  "NODE": "none",
  "hostname": "dyn12",
  "Ncpu": 4,
  "RAM": 16086,
  "HDmemory": 1846,
  "architecture": "x86_64",
  "status": "up",
  "priority": 50
}
```

`Ncpu` is the number of cores, `RAM` the memory for the jobs in MB and
`HDmemory` the size of the working partition in GB. You can change these
values and then restart Minosse.

 > ***ATTENTION*** *do not specify values bigger than the physical values of the machine.*

`defaults.mns` holds the values `msub` uses when a job does not specify
them. By default a job asks for 1 CPU and **all the RAM of the node**, so it
runs alone: users should give the RAM their jobs need with `msub -m`, or you
can lower the default `RAM` in `defaults.mns`.


## How to use

The flag `-h` gives the usage of every command, and `--version` its version.

### The demon (root only)

- Start or stop the demon:

  ```sh
  minosse start
  minosse stop
  ```

  Stopping kills the running jobs but keeps the queued ones. If jobs are
  still waiting from the last run (queued, or submitted while the demon was
  down), `minosse start` lists them and asks whether to keep them; use
  `minosse start --keep` or `minosse start --delete` to skip the question.

- Show the installed version:

  ```sh
  minosse version
  ```

The demon writes what it does in the `messages` file of the installation
directory.

### Submitting a job

```sh
msub -f path/scriptname -c ncpu -m ram
```

| Option | Meaning | Default |
|---|---|---|
| `-f`, `--file` | the job script (required) | |
| `-c`, `--cpus` | number of CPUs | from `defaults.mns` (1) |
| `-m`, `--memory` | RAM in MB | from `defaults.mns` (all the RAM) |
| `-p`, `--priority` | priority: higher runs first | from `defaults.mns` (50) |
| `-l`, `--link` | run the job after the earlier job with this script has ended | none |

The job script must be executable (`chmod u+x`) and start with an
interpreter line such as `#!/bin/bash`. Minosse runs it as you, in the
directory of the script. `msub` refuses a job that can never run, such as
one asking for more CPUs or RAM than the node has.

`msub` does not print the id of the job: the demon gives it when it queues
the job, and `mstat` shows it.

### Checking the queue

```sh
mstat        # one line for each job
mstat -v     # all the details
```

### Deleting a job

```sh
mdel -j id                  # by job id, as shown by mstat
mdel -s path/scriptname     # every job of yours with this script
```

You can delete only your own jobs. Deleting a running job kills all its
processes.


## How Minosse runs the jobs

Minosse looks at the free resources of the machine: no real queues are
created. For example, if you have 4 CPUs but only 2 GB of RAM, two jobs
requiring 1.5 GB of RAM each cannot run at the same time, and Minosse
queues one of them.

Jobs start in order of priority, and in order of submission at equal
priority. A job that does not fit yet is not overtaken by smaller jobs:
otherwise a stream of small jobs could keep a big one waiting forever. A job
chained with `msub -l` waits, without blocking the others, until the earlier
job it is chained to has ended.

The demon runs as root and starts each job with `runuser` as the user who
submitted it: the owner of the request file, which users cannot fake. Users
can write only in the `requests` directory of the installation.


## Development

The tests run in a container that simulates the server (requires podman):

```sh
Tests/run_tests.sh
```

See [Tests/README.md](Tests/README.md) for details. The same suite runs on
GitHub Actions on every push to `main` and `develop` and on every pull
request
([`.github/workflows/ci.yml`](.github/workflows/ci.yml)).

Minosse follows [Semantic Versioning](https://semver.org): the version is
kept only in the `VERSION` file, every change is listed in
[CHANGELOG.md](CHANGELOG.md), and each release is tagged `vX.Y.Z`.

If you find problems installing or running this program please use the
[Issues section on GitHub](https://github.com/JFadanni/Minosse/issues), I
will be happy to find a solution to your problem.

***
# Gaussian submitting script

Here is an example of a Gaussian (Gaussian16) submitting script using
Minosse. It writes a job script `input.nqs` next to the Gaussian input, which
runs the calculation in `/scratch/$USER`, and submits it:

```sh
#!/bin/bash

# to be sure it is used correctly
if [ -z "$3" ]; then
   echo -e '\nUsage: mg16 inputfile ncpu memory'
   echo -e '\n  Submit a Gaussian job to the Minosse queue system\n'
   exit 1
fi

# check if you are using the .com extension or not
job=${1%.com}

echo -e "\nSubmitting Gaussian batch job $job to Minosse queue system\n"

# define where we are
PTH=$PWD

# from here to 'END3' is defined the script which Minosse executes
cat <<END3 > $job.nqs
#!/bin/bash

mkdir -p /scratch/$USER

# check if the checkpoint exists
if [ -f $PTH/$job.chk ]; then
    cp $PTH/$job.chk /scratch/$USER/
fi

# check if the checkpoint is compressed
if [ -f $PTH/$job.chk.gz ]; then
    cp $PTH/$job.chk.gz /scratch/$USER/
    gzip -fd /scratch/$USER/$job.chk.gz
fi

# move to the working directory
cd /scratch/$USER/

# create the header of the Gaussian input file
cat <<END2 > $job.com_nqs
%chk=/scratch/$USER/$job
%int=/scratch/$USER/$job
%d2e=/scratch/$USER/$job
%rwf=/scratch/$USER/$job
%mem=$3MB
%nproc=$2
END2

cat $PTH/$job.com >> $job.com_nqs
# just to be sure put an empty line at the end of the input
echo ' ' >> $job.com_nqs

# run gaussian
g16 < $job.com_nqs > $PTH/$job.log 2>&1

# compress the checkpoint and bring it back
if [ -f $job.chk ]; then
    gzip -f $job.chk
    mv $job.chk.gz $PTH/
fi

# remove some useless files
rm -f Gau-*.scr
rm -f $job.com_nqs
rm -f $job.d2e $job.int $job.rwf
END3

# make the script executable
chmod u+x $job.nqs

# submit on Minosse
msub -f $PTH/$job.nqs -c $2 -m $3
```
