#! /usr/bin/env python3
# -*- coding: utf-8 -*-
import pwd
import socket
import time
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
file1=Mdir+'nodes'
file5='subjob'
file4=Mdir+'defaults'
mess=Mdir+'messages'

##------------------------------------------------------------------------------
## Variable names
##------------------------------------------------------------------------------

varnames=['hostname','Ncpu','RAM','architecture','status'
          ,'priority','pid','Njob','script','user','chain'
          ,'subtime','runtime','HDmemory']

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

parser = ArgumentParser(description="Submit a job to the Minosse queue")

parser.add_argument("--version", action="version",
                    version=f"%(prog)s {__version__}")
parser.add_argument("-c", "--cpus",
                    action="store", dest="cpus", default=cpus, type=int,
                    help=f"number of cpus required [default={cpus}]")
parser.add_argument("-m", "--memory",
                    action="store", dest="memory", default=RAM, type=int,
                    help=f"RAM memory requirement [default={RAM} MB]")
#parser.add_argument("-d", "--harddisck",
#                    action="store", dest="HD", default=0, type=int,
#                    help="HD scratch space required [default=0 GB]")
parser.add_argument("-p", "--priority",
                    action="store", dest="priority", default=priority, type=int,
                    help=f"set the priority of a job [default={priority}]")
parser.add_argument("-f", "--file",
                    action="store", dest="file",
                    help="set the name of the job script")
parser.add_argument("-l", "--link",
                    action="store", dest="chain", default="none",
                    help="run the job after the earlier job with this script "
                         "ends [default=none]")

options = parser.parse_args()

if not options.file:
    parser.error("the job script is required: -f path/scriptname")

##------------------------------------------------------------------------------
## Main program
##------------------------------------------------------------------------------

#ifrunning(Mdir)
architecture= os.uname()[-1]
# the demon does not run in the submission directory
script = os.path.abspath(options.file)
chain = options.chain if options.chain == 'none' else os.path.abspath(options.chain)
# not getpass.getuser(): it trusts $LOGNAME and $USER
user = pwd.getpwuid(os.getuid()).pw_name

varvalues = [socket.gethostname(),options.cpus,options.memory,architecture,'que',
         options.priority,'','',script,user,chain,time.strftime("%m/%d/%y %H.%M.%S", time.localtime()),'',
         HD]

job_prop = {}
for vname, vval in zip(varnames, varvalues):
    job_prop[vname] = vval

# the demon checks it again, but it is better to know it now
error = invalidjob(job_prop,readallfile(file1))
if error:
    parser.error(f"the job can never run: {error}")

# the demon gives the job its id
writeallfile(requestdir(Mdir)+requestname(file5),job_prop)
print(f"Job {script} submitted, see its id with mstat")
