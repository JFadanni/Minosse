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

import sys
import os
from   subprocess import *
import time

##------------------------------------------------------------------------------
## variable names
##------------------------------------------------------------------------------

n=0
subprocesses=[[],[]]

##------------------------------------------------------------------------------
## Main program
##------------------------------------------------------------------------------

#ifrunning()
writeinitializationmessage()
status=readallfile(file3)
status=cleanstatus(status)
writeallfile(file3,status)

while 1:
    ## read files
    realvalue=readallfile(file1)
    charge=readallfile(file2)
    status=readallfile(file3)
    defaults=readallfile(file4)
    ## apply default settings if not specified in the request
    charge=applydefaults(charge,defaults,'RAM')
    charge=applydefaults(charge,defaults,'Ncpu')
    charge=applydefaults(charge,defaults,'HDmemory')
    charge=chainjob(charge)
    ## test free slots for the requests
    test0=testtext(defaults,charge,'status')
    test1=testalgebric(realvalue,status,charge,'RAM')
    test2=testalgebric(realvalue,status,charge,'Ncpu')
    test3=testalgebric(realvalue,status,charge,'HDmemory')
    tests=[test0,test1,test2,test3]
    ## calculate the free machine for each requests
    freemac=choice(tests,realvalue)
    if len(freemac[1]) == 0:
        pass
    else:
        n=n+1
        ## define the priority list
        job=prior(freemac,charge)
        ## modify the status
        writemessage('Refresh machine status')
        status=newstatus(status,charge,'RAM',job)
        status=newstatus(status,charge,'Ncpu',job)
        status=newstatus(status,charge,'HDmemory',job)
        ## set runnig job
        charge=replace(charge,'run','status',job)
        charge=replace(charge,time.strftime("%m/%d/%y %H.%M.%S", time.localtime()),'runtime',job)
        writemessage('Refresh queue status')
        ## submit calculation
        script=findall(charge,'script')[job]
        user=findall(charge,'user')[job]
        writemessage('Running job '+script)
        ##pid=os.spawnlp(os.P_NOWAIT, script)    prova
        try:
            subpro=Popen(["su - "+user+" -c "+script],shell=True)
            pid=subpro.pid
            subprocesses=makelist(subprocesses,subpro,n)
            writemessage('job pid '+str(pid))
            charge=replace(charge,pid,'pid',job)
            charge=replace(charge,n,'Njob',job)
            writeallfile(file3,status)
            writeallfile(file2,charge)
        except:
            writewarning(' Something wrong in the '+script+' script')
            writewarning(' Job aborted')
            charge=delete(charge,job,varnames)
            writeallfile(file2,charge)
    ## refresh the variables 
    charge=readallfile(file2)
    status=readallfile(file3)
    ## check ended jobs 
    result=endjob(charge,subprocesses)
    job=result[0]
    subprocesses=result[1]
    if job == 'no':
        pass
    else:
        writemessage('job '+str(findall(charge,'script')[job]+' ended'))
        ## refresh the status when a job ends
        writemessage('Refresh machine status')
        status=newstatus2(status,charge,'RAM',job)
        status=newstatus2(status,charge,'Ncpu',job)
        status=newstatus2(status,charge,'HDmemory',job)
        writeallfile(file3,status)
        ## delete from queue list the job ended
        writemessage('Refresh queue status')
        charge=delete(charge,job,varnames)
        writeallfile(file2,charge)
    ## check the stop file wich control the minosse  demon
    checkdemon(file6)
    ## check if a job has been deleted from the que system
    checkdeletedjob(file7,file2,varnames)
    ## write in the charge file the new submitted job
    writejob(Mdir,file5,file2)
    ## waiting time
    time.sleep(1)
