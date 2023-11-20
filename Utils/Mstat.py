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
__version__ = '1.3.0'
__credits__ = """Piero Altoè for a nice queue manager."""

##------------------------------------------------------------------------------
## Common Imports
##------------------------------------------------------------------------------

from argparse import ArgumentParser

##------------------------------------------------------------------------------
## Local Imports
##------------------------------------------------------------------------------

from    Mutil      import ifrunning, readallfile, findall


##------------------------------------------------------------------------------
## Files names
##------------------------------------------------------------------------------

MDIR="$instdir/"
FILE2=MDIR+'charge'
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

parser.add_argument("-v", "--verbose",
                  action="store_true", dest="verbose", default=False,
                  help="make lots of noise")

args = parser.parse_args()

##------------------------------------------------------------------------------
## Main program
##------------------------------------------------------------------------------

ifrunning()

print (f'Minosse batch system v{__version__}')
print ('-'*60)

charge=readallfile(FILE2)
user=findall(charge,'user')

if args.verbose:
    status=findall(charge,'status')
    if not status:
        print ('  System free: no job queued or running')
    else:

        for i in range(len(user)):
            for j in range(int(len(charge[0])/len(user))):
                print(f"{charge[0][j+int(len(charge[0])/len(user))*i]:15s}:"
                f"{charge[1][j+int(len(charge[0])/len(user))*i]}")

else:
    status=findall(charge,'status')
    Ncpu=findall(charge,'Ncpu')
    RAM=findall(charge,'RAM')
    priority=findall(charge,'priority')
    jid=findall(charge,'id')

    if not status:
        print ('  System free: no job queued or running')
    else:
        print(f"{'user':15s} {'Ncpu':6s} {'RAM':8s} {'id':7s} {'status':7s} {'priority':9s}")
        print ('-'*60)
        for i, j in enumerate(jid):
            print (f"{user[i]:15s}{Ncpu[i]:6s}{RAM[i]:8s}{j:7s}{status[i]:7s}{priority[i]:9s}")
print ('-'*60)
