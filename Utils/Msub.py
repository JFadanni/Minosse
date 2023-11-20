#! /usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Minosse a Python-based batch system

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

__version__ = "1.3.0"
__author__ = "Jacopo Fadanni"
__date__ = "12th Nov 2023"
__credits__ = """Piero Altoè for a nice queue manager."""

from   argparse import ArgumentParser
import getpass
import os
import random
import socket
import time

from    Mutil      import ifrunning, writeallfile


##------------------------------------------------------------------------------
## Files names
##------------------------------------------------------------------------------

MDIR="$instdir/"
FILE5='subjob'
MESS=MDIR+'messages'

##------------------------------------------------------------------------------
## Variable names
##------------------------------------------------------------------------------

varnames=['hostname','Ncpu','RAM','HDmemory','architecture','status'
          ,'priority','pid','Njob','script','user','id','chain'
          ,'subtime','runtime']

##------------------------------------------------------------------------------
## Flags
##------------------------------------------------------------------------------

parser = ArgumentParser(prog="%prog", description=f"%prog {__version__}")

parser.add_argument("-c", "--cpus",
                  action="store", dest="cpus", default=1, type=int,
                  help="nomber of cpus required [default=1]")
parser.add_argument("-m", "--memory",
                  action="store", dest="memory", default=700, type=int,
                  help="RAM memory requirement [default=700 MB]")
parser.add_argument("-d", "--harddisck",
                  action="store", dest="HD", default=00, type=int,
                  help="HD scratch space required [default=00 GB]")
parser.add_argument("-p", "--priority",
                  action="store", dest="priority", default=50, type=int,
                  help="set the priority of a job [default=50]")
parser.add_argument("-f", "--file",
                  action="store", dest="file",
                  help="set the name of the job script")
parser.add_argument("-l", "--link",
                  action="store", dest="chain", default="none",
                  help="set the name of the chained job [default=none]")

args = parser.parse_args()

##------------------------------------------------------------------------------
## Main program
##------------------------------------------------------------------------------

ifrunning()
architecture= os.uname()[-1]
ID=str(random.randint(1, 1000000))

subjob=[varnames,
        [socket.gethostname(),args.cpus,args.memory,args.HD,architecture,'que',
         args.priority,'','',args.file ,getpass.getuser(),ID,args.chain,
         time.strftime("%m/%d/%y %H.%M.%S", time.localtime()),'']]

writeallfile(MDIR+FILE5+ID,subjob)
