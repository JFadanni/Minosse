#! /usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import pwd
from   argparse   import ArgumentParser, ArgumentTypeError

from    Mutil      import *
from    Mutil      import __version__

""" Minosse a Python-based batch system

Copyright 2022,2024 Jacopo Fadanni

This file is part of Minosse.

Minosse is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

Minosse is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with Minosse.  If not, see <http://www.gnu.org/licenses/>.
"""

__author__ = "Jacopo Fadanni"
__credits__ = """Piero Altoè for a nice queue manager."""

##------------------------------------------------------------------------------
## Files names
##------------------------------------------------------------------------------

Mdir="$instdir/"
file8='remove'
mess=Mdir+'messages'

##------------------------------------------------------------------------------
## Flags
##------------------------------------------------------------------------------

def jobids(text):
    """A job id or a range of ids, checked as the demon reads them"""
    try:
        parseids([text])
    except ValueError as error:
        raise ArgumentTypeError(str(error)) from None
    return text

parser = ArgumentParser(description="Delete jobs from the Minosse queue")

parser.add_argument("--version", action="version",
                    version=f"%(prog)s {__version__}")
target = parser.add_mutually_exclusive_group(required=True)
target.add_argument("-j", "--job",
                    action="store", dest="job", nargs="+", type=jobids,
                    default=None, metavar="ID",
                    help="ids, as shown by mstat, or ranges of ids: "
                         "-j 3 4 7-10")
target.add_argument("-s", "--script",
                    action="store", dest="script", default=None,
                    help="script name")
target.add_argument("--all-jobs",
                    action="store_true", dest="alljobs", default=False,
                    help="delete all your jobs, queued and running")
target.add_argument("--flush",
                    action="store_true", dest="flush", default=False,
                    help="delete every job of every user (root only)")
parser.add_argument("-a", "--all",
                    action="store_true", dest="all", default=False,
                    help="kill all processes from the top script to the last "
                         "child (always done, kept for compatibility)")

options = parser.parse_args()

# the demon checks it again, but it is better to know it now
if options.flush and os.geteuid() != 0:
    parser.error("only root can delete the jobs of everybody")

##------------------------------------------------------------------------------
## Main program
##------------------------------------------------------------------------------

ifrunning(Mdir)

# msub stores absolute paths
script = None if options.script is None else os.path.abspath(options.script)

delkeys = ['script','id','all','user','alljobs','flush']
delvalues = [script,options.job,options.all,pwd.getpwuid(os.getuid()).pw_name,
             options.alljobs,options.flush]
deljob = {}

for vname, vval in zip(delkeys, delvalues):
    deljob[vname] = vval


writeallfile(requestdir(Mdir)+requestname(file8),deljob)
