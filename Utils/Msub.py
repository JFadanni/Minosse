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
file9=Mdir+'quotas'
mess=Mdir+'messages'

##------------------------------------------------------------------------------
## Variable names
##------------------------------------------------------------------------------

varnames=['hostname','Ncpu','RAM','architecture','status'
          ,'priority','pid','Njob','script','user','chain'
          ,'subtime','runtime','HDmemory','force']

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
                    action="store", dest="memory", default=None, type=int,
                    help=f"RAM memory requirement [default={RAM} MB, or "
                         "your RAM quota if smaller]")
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
parser.add_argument("--force",
                    action="store_true", dest="force", default=False,
                    help="ignore your cpu and RAM quota: the job runs, in "
                         "order of priority, as soon as the node has room")

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
node = readallfile(file1)
try:
    quotas = readquotas(file9,node)
except (OSError, ValueError): # the demon keeps the previous quotas
    quotas = {}
quota = None if options.force else userquota(user,quotas)
memory = options.memory
if memory is None:
    memory = RAM if quota is None else min(RAM,quota['RAM'])

varvalues = [socket.gethostname(),options.cpus,memory,architecture,'que',
         options.priority,'','',script,user,chain,time.strftime("%m/%d/%y %H.%M.%S", time.localtime()),'',
         HD,options.force]

job_prop = {}
for vname, vval in zip(varnames, varvalues):
    job_prop[vname] = vval

# the demon checks it again, but it is better to know it now
error = invalidjob(job_prop,node)
if error:
    parser.error(f"the job can never run: {error}")
error = overquota(job_prop,quotas)
if error:
    parser.error(f"{error}: ask for less, or use --force to ignore the quota")

# the demon gives the job its id
writeallfile(requestdir(Mdir)+requestname(file5),job_prop)
print(f"Job {script} submitted, see its id with mstat")
