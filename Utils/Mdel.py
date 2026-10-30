#! /usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import pwd
from   argparse   import ArgumentParser

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

parser = ArgumentParser(description="Delete a job from the Minosse queue")

parser.add_argument("--version", action="version",
                    version=f"%(prog)s {__version__}")
parser.add_argument("-j", "--job",
                    action="store", dest="job", type=int, default=None,
                    help="id number")
parser.add_argument("-s", "--script",
                    action="store", dest="script", default=None,
                    help="script name")
parser.add_argument("-a", "--all",
                    action="store_true", dest="all", default=False,
                    help="kill all processes from the top script to the last "
                         "child (always done, kept for compatibility)")

options = parser.parse_args()

if options.job is None and options.script is None:
    parser.error("give the job to delete: -j id or -s path/scriptname")

##------------------------------------------------------------------------------
## Main program
##------------------------------------------------------------------------------

ifrunning(Mdir)

# job ids are the keys of charge.mns, which are strings
job = None if options.job is None else str(options.job)
# msub stores absolute paths
script = None if options.script is None else os.path.abspath(options.script)

delkeys = ['script','id','all','user']
delvalues = [script,job,options.all,pwd.getpwuid(os.getuid()).pw_name]
deljob = {}

for vname, vval in zip(delkeys, delvalues):
    deljob[vname] = vval


writeallfile(requestdir(Mdir)+requestname(file8),deljob)
