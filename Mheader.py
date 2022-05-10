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
__version__ = '$Revision: 1.0.0 $'
__credits__ = """Guido van Rossum, for an excellent programming language."""

##------------------------------------------------------------------------------
## Common Imports
##------------------------------------------------------------------------------

from    Mutil      import *

##------------------------------------------------------------------------------
## Files names
##------------------------------------------------------------------------------

Mdir="Minosse_test/"# the current directory
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

