#! /usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import pwd
import random
from   optparse   import OptionParser

from    Mutil      import *

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
__date__ = "12th Nov 2023"
__version__ = '$Revision: 1.3.0 $'
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

parser = OptionParser(usage="%prog", version="%prog 1.0.0")

parser.add_option("-j", "--job",
                  action="store", dest="job", type="int", default=None,
                  help="id number")

parser.add_option("-s", "--script",
                  action="store", dest="script", type="string", default=None,
                  help="script name")

parser.add_option("-a", "--all",
                  action="store_true", dest="all", default=False,
                  help="kill all processes from the top script to the last child")

(options, args) = parser.parse_args()

if options.job is None and options.script is None:
    parser.error("give the job to delete: -j id or -s path/scriptname")

##------------------------------------------------------------------------------
## Main program
##------------------------------------------------------------------------------

ifrunning(Mdir)

RND=str(random.randint(1, 1000000))

# job ids are the keys of charge.mns, which are strings
job = None if options.job is None else str(options.job)
# msub stores absolute paths
script = None if options.script is None else os.path.abspath(options.script)

delkeys = ['script','id','all','user']
delvalues = [script,job,options.all,pwd.getpwuid(os.getuid()).pw_name]
deljob = {}

for vname, vval in zip(delkeys, delvalues):
   deljob[vname] = vval


writeallfile(requestdir(Mdir)+file8+RND,{RND :deljob})
