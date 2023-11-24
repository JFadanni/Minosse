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
__date__ = "24th Nov 2023"
__version__ = '1.3.1 $'
__credits__ = """Piero Altoè for a nice queue manager."""

##------------------------------------------------------------------------------
## Imports
##------------------------------------------------------------------------------
#import sys
#import os
import time
from subprocess import Popen

import Mutil as util

##------------------------------------------------------------------------------
## Files names
##------------------------------------------------------------------------------

MDIR="$instdir/"
FILE1=MDIR+'nodes'
FILE2=MDIR+'charge'
FLIE3=MDIR+'status'
FILE4=MDIR+'defaults'
FILE5='subjob'
FILE6=MDIR+'conf'
FILE7=MDIR+'delete'
FILE8='remove'
MESS=MDIR+'messages'

##------------------------------------------------------------------------------
## Variable names
##------------------------------------------------------------------------------

varnames=['hostname','Ncpu','RAM','HDmemory','architecture','status'
          ,'priority','pid','Njob','script','user','id','chain'
          ,'subtime','runtime']


##------------------------------------------------------------------------------
## variable names
##------------------------------------------------------------------------------

N=0
subprocesses=[[],[]]

##------------------------------------------------------------------------------
## Main program
##------------------------------------------------------------------------------

util.ifrunning()
util.writeinitializationmessage()
status=util.readallfile(FLIE3)
status=util.cleanstatus(status)
util.writeallfile(FLIE3,status)

while 1:
    ## read files
    realvalue=util.readallfile(FILE1)
    charge=util.readallfile(FILE2)
    status=util.readallfile(FLIE3)
    defaults=util.readallfile(FILE4)
    ## apply default settings if not specified in the request
    charge=util.applydefaults(charge,defaults,'RAM')
    charge=util.applydefaults(charge,defaults,'Ncpu')
    charge=util.applydefaults(charge,defaults,'HDmemory')
    charge=util.chainjob(charge)
    ## test free slots for the requests
    test0=util.testtext(defaults,charge,'status')
    test1=util.testalgebric(realvalue,status,charge,'RAM')
    test2=util.testalgebric(realvalue,status,charge,'Ncpu')
    test3=util.testalgebric(realvalue,status,charge,'HDmemory')
    tests=[test0,test1,test2,test3]
    ## calculate the free machine for each requests
    freemac=util.choice(tests,realvalue)
    if len(freemac[1]) == 0:
        pass
    else:
        N=N+1
        ## define the priority list
        job=util.prior(freemac,charge)
        ## modify the status
        util.writemessage('Refresh machine status')
        status=util.newstatus(status,charge,'RAM',job)
        status=util.newstatus(status,charge,'Ncpu',job)
        status=util.newstatus(status,charge,'HDmemory',job)
        ## set runnig job
        charge=util.replace(charge,'run','status',job)
        charge=util.replace(charge,time.strftime("%m/%d/%y %H.%M.%S", time.localtime())
        ,'runtime',job)
        util.writemessage('Refresh queue status')
        ## submit calculation
        script=util.findall(charge,'script')[job]
        user=util.findall(charge,'user')[job]
        util.writemessage('Running job '+script)
        ##pid=os.spawnlp(os.P_NOWAIT, script)    prova
        try:
            #subpro=Popen(["runuser -u "+user+" "+script],shell=True)
            subpro = Popen(["runuser", "-u", user, script])
            PID=subpro.pid
#            errors=subpro.errors
#            if(errors):
#                    writewarning('submission error '+str(errors))
            subprocesses=util.makelist(subprocesses,subpro,N)
            util.writemessage('job pid '+str(PID))
            charge=util.replace(charge,PID,'pid',job)
            charge=util.replace(charge,N,'Njob',job)
            util.writeallfile(FLIE3,status)
            util.writeallfile(FILE2,charge)
        except:
            util.writewarning(' Something wrong in the '+script+' script')
            util.writewarning(' Job aborted')
            charge=util.delete(charge,job,varnames)
            util.writeallfile(FILE2,charge)
    ## refresh the variables
    charge=util.readallfile(FILE2)
    status=util.readallfile(FLIE3)
    ## check ended jobs
    result=util.endjob(charge,subprocesses)
    job=result[0]
    subprocesses=result[1]
    if job == 'no':
        pass
    else:
        util.writemessage('job '+str(util.findall(charge,'script')[job]+' ended'))
        ## refresh the status when a job ends
        util.writemessage('Refresh machine status')
        status=util.newstatus2(status,charge,'RAM',job)
        status=util.newstatus2(status,charge,'Ncpu',job)
        status=util.newstatus2(status,charge,'HDmemory',job)
        util.writeallfile(FLIE3,status)
        ## delete from queue list the job ended
        util.writemessage('Refresh queue status')
        charge=util.delete(charge,job,varnames)
        util.writeallfile(FILE2,charge)
    ## check the stop file wich control the minosse  demon
    util.checkdemon(FILE6)
    ## check if a job has been deleted from the que system
    util.checkdeletedjob(FILE7,FILE2,varnames)
    ## write in the charge file the new submitted job
    util.writejob(MDIR,FILE5,FILE2)
    ## waiting time
    time.sleep(1)
