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

#Mdir="$instdir/"
Mdir = "/home/jacopo/Python_developing/Minosse_dev/Minosse_test/Minosse_mns/" # for developing only
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

import sys
import os
from   subprocess import *
import time
import json

##------------------------------------------------------------------------------
## variable names
##------------------------------------------------------------------------------


##------------------------------------------------------------------------------
## Main program
##------------------------------------------------------------------------------

#ifrunning()
writeinitializationmessage()
status=readallfile(file3)
#status=cleanstatus(status)
writeallfile(file3,status)
realvalue=readallfile(file1)
defaults=readallfile(file4)

while 1:
    ## read files
    status=readallfile(file3)
    writejob(Mdir,file5,file2)
    charge=readallfile(file2)
    ## apply default settings if not specified in the request
    charge=applydefaults(charge,defaults)
#    charge=chainjob(charge)
    ## test free slots for the requests
    available_resources = find_available_resources(status,realvalue)
    queue = find_queued_jobs(charge)
    if available_resources['free_space'] and queue:
        priority_list = sortbypriority(queue)
        jobs_to_submit = check_for_submissions(available_resources,priority_list,queue)

        for jobid in jobs_to_submit:
            job = charge[jobid]
            user = job['user']
            script = job['script']
            try:
                #subpro=Popen(["runuser -u "+user+" "+script],shell=True)
                subpro = Popen(script, shell=True)
                pid=subpro.pid
                errors=subpro.errors
                if (errors):
                    writewarning('submission error '+str(errors))
                job['pid'] = pid
                job['status'] = 'run'
                job['runtime'] = time.strftime("%m/%d/%y %H.%M.%S", time.localtime())
                writemessage('Job '+script+' submitted')
                update_status(status,job)
            except:
                writewarning(' Something wrong in the '+script+' script')
                deleted = delete(jobid,charge)
                if deleted:
                    writewarning('Job aborted')
                else:
                    writewarning('Unable to delete job')
        writeallfile(file2,charge)
        writeallfile(file3,status)
    else:
        pass
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
    ## waiting time
    time.sleep(1)
