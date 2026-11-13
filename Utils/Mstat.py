#! /usr/bin/env python3
# -*- coding: utf-8 -*-

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
file2=Mdir+'charge'
mess=Mdir+'messages'

##------------------------------------------------------------------------------
## Variable names
##------------------------------------------------------------------------------

varnames=['hostname','Ncpu','RAM','architecture','status'
          ,'priority','pid','Njob','script','user','id','chain'
          ,'subtime','runtime']

##------------------------------------------------------------------------------
## Flags
##------------------------------------------------------------------------------

parser = ArgumentParser(description="Show the jobs in the Minosse queue")

parser.add_argument("--version", action="version",
                    version=f"%(prog)s {__version__}")
parser.add_argument("-v", "--verbose",
                    action="store_true", dest="verbose", default=False,
                    help="make lots of noise")

options = parser.parse_args()

##------------------------------------------------------------------------------
## Main program
##------------------------------------------------------------------------------

#ifrunning()

print (f'Minosse batch system {__version__}')
print ('-'*60)

charge=readallfile(file2)

if options.verbose:
    if charge:
        print ("Queued or running jobs:\n","-"*60)
        for jobid in charge:
            job = charge[jobid]
            print(f"{jobid}:")
            print(f"  user: {job['user']}")
            print(f"  script: {job['script']}")
            print(f"  priority: {job['priority']}")
            print(f"  status: {job['status']}")
            print(f"  Ncpu: {job['Ncpu']}")
            print(f"  RAM: {job['RAM']}")
            print(f"  HDmemory: {job['HDmemory']}")
            print(f"  subtime: {job['subtime']}")
            if job['status'] == 'run':
                print(f"  runtime: {job['runtime']}")
                print(f"  pid: {job['pid']}")
            else:
                print("  runtime: -")
                print("  pid: -")
    else:
        print ('  System free: no job queued or running')

else:
    if charge:
        print ('%15s' % 'user','%6s' % 'Ncpu','%8s' % 'RAM','%7s' % 'id','%7s' % 'status','%9s' % 'priority')
        print ('-'*60)
        for jobid in charge:
            job = charge[jobid]
            user = job['user']
            script = job['script']
            status = job['status']
            Ncpu = job['Ncpu']
            RAM = job['RAM']
            priority = job['priority']

            print ('%15s' % user,'%6s' %Ncpu,'%8s' % RAM,'%7s' % jobid,'%7s' %status, '%9s' %priority)
    else:
        print ('  System free: no job queued or running')
print ('-'*60)
