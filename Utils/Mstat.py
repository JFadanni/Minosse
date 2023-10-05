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
__date__ = "5th Oct 2023"
__version__ = '$Revision: 1.1.0 $'
__credits__ = """Piero Altoè for a nice queue manager."""
##------------------------------------------------------------------------------
## Common Imports
##------------------------------------------------------------------------------

from    Mutil      import *

##------------------------------------------------------------------------------
## Files names
##------------------------------------------------------------------------------

Mdir="$instdir/"
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

varnames=['hostname','Ncpu','RAM','HDmemory','architecture','status'
          ,'priority','pid','Njob','script','user','id','chain'
          ,'subtime','runtime']

##------------------------------------------------------------------------------
## Imports
##------------------------------------------------------------------------------

from   optparse   import OptionParser

##------------------------------------------------------------------------------
## Flags
##------------------------------------------------------------------------------

parser = OptionParser(usage="%prog", version="%prog 1.0.0")

parser.add_option("-v", "--verbose",
                  action="store_true", dest="verbose", default=False,
                  help="make lots of noise")

(options, args) = parser.parse_args()

##------------------------------------------------------------------------------
## Main program
##------------------------------------------------------------------------------

ifrunning()

print ('Minosse batch system v1.0.0')
print ('-'*60)

charge=readallfile(file2)
user=findall(charge,'user')

if options.verbose == True :
        status=findall(charge,'status')
        if status == []:
            print ('  System free: no job queued or running')
        else:

            for i in range(len(user)):
                for j in range(int(len(charge[0])/len(user))):
                     print ('%15s' % charge[0][j+int(len(charge[0])/len(user))*i],':',charge[1][j+int(len(charge[0])/len(user))*i])

else:
        status=findall(charge,'status')
        Ncpu=findall(charge,'Ncpu')
        RAM=findall(charge,'RAM')
        priority=findall(charge,'priority')
        id=findall(charge,'id')

        if status == []:
            print ('  System free: no job queued or running')
        else:
            print ('%15s' % 'user','%6s' % 'Ncpu','%8s' % 'RAM','%7s' % 'id','%7s' % 'status','%9s' % 'priority')
            print ('-'*60)
            for i in range(len(status)):
                print ('%15s' % user[i],'%6s' %Ncpu[i],'%8s' % RAM[i],'%7s' % id[i],'%7s' %status[i], '%9s' %priority[i])
print ('-'*60)
