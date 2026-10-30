#! /usr/bin/env python3
# -*- coding: utf-8 -*-
import pwd
import socket
import random
import time
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
__version__ = "Revision: 1.3.0"
__credits__ = """Piero Altoè for a nice queue manager."""
##------------------------------------------------------------------------------
## Files names
##------------------------------------------------------------------------------

Mdir="$instdir/"
file5='subjob'
file4=Mdir+'defaults'
mess=Mdir+'messages'

##------------------------------------------------------------------------------
## Variable names
##------------------------------------------------------------------------------

varnames=['hostname','Ncpu','RAM','architecture','status'
          ,'priority','pid','Njob','script','user','chain'
          ,'subtime','runtime','HDmemory','id']

##------------------------------------------------------------------------------
## Loads defaults
##------------------------------------------------------------------------------
defaults = readallfile(file4)
cpus = defaults['Ncpu']
RAM = defaults['RAM']
priority = defaults['priority']
HD = defaults['HDmemory']

##------------------------------------------------------------------------------
## Flags
##------------------------------------------------------------------------------

parser = OptionParser(usage="%prog", version=f"%prog {__version__}") # fix version

parser.add_option("-c", "--cpus",
                  action="store", dest="cpus", default=cpus, type="int", 
                  help=f"nomber of cpus required [default={cpus}]")
parser.add_option("-m", "--memory",
                  action="store", dest="memory", default=RAM, type="int",
                  help=f"RAM memory requirement [default={RAM} MB]")
#parser.add_option("-d", "--harddisck",
#                  action="store", dest="HD", default="00", type="int",
#                  help="HD scratch space required [default=00 GB]")
parser.add_option("-p", "--priority",
                  action="store", dest="priority", default=priority, type="int",
                  help=f"set the priority of a job [default={priority}]")
parser.add_option("-f", "--file",
                  action="store", dest="file",
                  help="set the name of the job script")
parser.add_option("-l", "--link",
                  action="store", dest="chain", default="none",
                  help="set the name of the chained job [default=none]")

(options, args) = parser.parse_args()

if not options.file:
    parser.error("the job script is required: -f path/scriptname")

##------------------------------------------------------------------------------
## Main program
##------------------------------------------------------------------------------

#ifrunning(Mdir)
architecture= os.uname()[-1]
id=str(random.randint(1, 1000000))
# the demon does not run in the submission directory
script = os.path.abspath(options.file)
# not getpass.getuser(): it trusts $LOGNAME and $USER
user = pwd.getpwuid(os.getuid()).pw_name

varvalues = [socket.gethostname(),options.cpus,options.memory,architecture,'que',
         options.priority,'','',script,user,options.chain,time.strftime("%m/%d/%y %H.%M.%S", time.localtime()),'',
         HD,id]

job_prop = {}
for vname, vval in zip(varnames, varvalues):
    job_prop[vname] = vval

subjob = {id: job_prop}

writeallfile(requestdir(Mdir)+file5+id,subjob)
