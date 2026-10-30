#! /usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import time
import json
from   subprocess import *
from   optparse   import OptionParser

from    Mutil      import *

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

varnames=['hostname','Ncpu','RAM','architecture','status'
          ,'priority','pid','Njob','script','user','id','chain'
          ,'subtime','runtime']

##------------------------------------------------------------------------------
## Flags
##------------------------------------------------------------------------------

parser = OptionParser(usage="%prog [--delete-pending]")

parser.add_option("--delete-pending",
                  action="store_true", dest="delete", default=False,
                  help="delete the jobs still waiting from the last run")

(options, args) = parser.parse_args()

##------------------------------------------------------------------------------
## Main program
##------------------------------------------------------------------------------

ifrunning(Mdir)
writeinitializationmessage(mess)
status=readallfile(file3)
status=cleanstatus(status,Mdir,file2,file6,keep=not options.delete)
writeallfile(file3,status)
realvalue=readallfile(file1)
defaults=readallfile(file4)

while 1:
    ## read files
    status=readallfile(file3)
    charge=readallfile(file2)
    ## test free slots for the requests
    available_resources = find_available_resources(status,realvalue)
    queue = holdchained(find_queued_jobs(charge),charge)
    if available_resources['free_space'] and queue:
        priority_list = sortbypriority(queue)
        jobs_to_submit = check_for_submissions(available_resources,priority_list,queue)

        for jobid in jobs_to_submit:
            job = charge[jobid]
            script = job['script']
            try:
                # no shell: the script name must not be able to run commands as root;
                # a session of its own, so that the whole job can be killed;
                # the directory of the script, since users cannot write in Mdir
                subpro=Popen(jobcommand(job),start_new_session=True,
                             cwd=os.path.dirname(script))
                job['pid'] = subpro.pid
                job['status'] = 'run'
                job['runtime'] = time.strftime("%m/%d/%y %H.%M.%S", time.localtime())
                writemessage(f"Job {script} submitted",mess)
                update_status(status,job,1)
            except OSError:
                writewarning(f"Unable to run, something wrong in the {script} script",mess)
                deleted = delete(jobid,charge)
                if deleted:
                    writewarning('Job aborted',mess)
                else:
                    writewarning('Unable to run or delete job',mess)
        writeallfile(file2,charge)
        writeallfile(file3,status)
    else:
        pass
    ## refresh the variables 
    charge=readallfile(file2)
    status=readallfile(file3)
    ## check ended jobs
    charge, status = endjob(charge,status,mess)
    writeallfile(file3,status)
    writeallfile(file2,charge)
    ## check for jobs to be deleted
    writejob(requestdir(Mdir),file8,file7,mess)
    checkdeletedjob(file7,file2,file3,mess)
    ## check the stop file wich control the minosse  demon
    checkdemon(file6,file2,file3,mess)
    ## write in the charge file the new submitted job
    submitjobs(requestdir(Mdir),file5,file2,file3,realvalue,mess)
    ## waiting time
    time.sleep(1)
