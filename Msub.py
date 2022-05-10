#! /usr/bin/env python3
# -*- coding: utf-8 -*-
""" Minosse a python based batch system

Copyright 2007,2008 Piero Altoè

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

__author__ = "Piero Altoè <piero.altoe@gmail.com> Jacopo Fadanni"
__date__ = "6th May 2022"
__version__ = ': 1.0.0 $'
__credits__ = """Guido van Rossum, for an excellent programming language."""

##------------------------------------------------------------------------------
## Common Imports
##------------------------------------------------------------------------------

from    Mutil      import *

##------------------------------------------------------------------------------
## Files names
##------------------------------------------------------------------------------

Mdir="Minosse_test/" #the current direcotry
file1=Mdir+'nodes'
file2=Mdir+'charge'
file3=Mdir+'status'
file4=Mdir+'defaults'
file5='subjob'
file6=Mdir+'conf'
file7=Mdir+'delete'
file8='remove'
mess=Mdir+'messages'

##------------------------------------------------------------------------------
## Variable names
##------------------------------------------------------------------------------

varnames=['hostname','Ncpu','RAM','HDtype','HDmemory','architecture','status'
          ,'priority','pid','Njob','script','user','id','chain'
          ,'subtime','runtime']

##------------------------------------------------------------------------------
## Imports
##------------------------------------------------------------------------------

from   optparse   import OptionParser
import getpass
import socket
import random
import time

##------------------------------------------------------------------------------
## Flags
##------------------------------------------------------------------------------

parser = OptionParser(usage="%prog", version="%prog 1.0.0")

parser.add_option("-c", "--cpus",
                  action="store", dest="cpus", default="1", type="int", 
                  help="nomber of cpus required [default=1]")
parser.add_option("-m", "--memory",
                  action="store", dest="memory", default="700", type="int",
                  help="RAM memory requirement [default=700 MB]")
parser.add_option("-d", "--harddisck",
                  action="store", dest="HD", default="00", type="int",
                  help="HD scratch space required [default=00 GB]")
parser.add_option("-p", "--priority",
                  action="store", dest="priority", default="70", type="int",
                  help="set the priority of a job [default=70]")
parser.add_option("-f", "--file",
                  action="store", dest="file",
                  help="set the name of the job script")
parser.add_option("-l", "--link",
                  action="store", dest="chain", default="none",
                  help="set the name of the chained job [default=none]")

(options, args) = parser.parse_args()

##------------------------------------------------------------------------------
## Main program
##------------------------------------------------------------------------------

#ifrunning()

id=str(random.randint(1, 1000000))

subjob=[varnames,
        [socket.gethostname(),options.cpus,options.memory,'eide',options.HD,'x64','que',
         options.priority,'','',options.file ,getpass.getuser(),id,options.chain,time.strftime("%m/%d/%y %H.%M.%S", time.localtime()),'']]

writeallfile(Mdir+file5+id,subjob)
