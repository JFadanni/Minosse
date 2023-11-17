#! /usr/bin/env python3
# -*- coding: utf-8 -*-
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

from argparse import ArgumentParser
import getpass
import random

from Mutil import ifrunning, writeallfile

##------------------------------------------------------------------------------
## Files names
##------------------------------------------------------------------------------

MDIR="$instdir/"
FILE8='remove'
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

parser = ArgumentParser(usage="%prog", version="%prog 1.0.0")

parser.add_argument("-j", "--job",
                  action="store", dest="job",  default="none",
                  help="id number")

parser.add_argument("-s", "--script",
                  action="store", dest="script", default="none",
                  help="script name")

parser.add_argument("-a", "--all",
                  action="store_true", dest="all", default=False,
                  help="kill all processes from the top script to the last child")

(options, args) = parser.parse_args()

##------------------------------------------------------------------------------
## Main program
##------------------------------------------------------------------------------

ifrunning()

RND=str(random.randint(1, 1000000))

OPT ="all" if options.all else "none"

deljob=[['script','id','priority','user'],
        [options.script,options.job,OPT,getpass.getuser()]]


writeallfile(MDIR+FILE8+RND,deljob)
