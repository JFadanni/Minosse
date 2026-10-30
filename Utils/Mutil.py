#! /usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import time
import json
import math
import pwd
from   stat   import S_ISREG
from   signal import SIGTERM

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
## write messages
##------------------------------------------------------------------------------

def writeinitializationmessage(mess):
    """write the opening string in the messages file""" 
    with open(mess,'w') as log:
        log.write(time.asctime()+'   ---MINOSSE START---\n')
    return

def writemessage(wrote,mess):
    """write a string in the messages file"""
    with open(mess,'a') as log:
        log.write(time.asctime()+'   '+wrote+'\n')
    return

def writewarning(wrote,mess):
    """write a WARNING message"""
    writemessage('WARNING:'+wrote,mess)
    return

def writefatalerror(wrote,mess):
    """write an error message end exit from Minosse"""
    writemessage('FATAL:  '+wrote,mess)
    writemessage('--- MINOSSE STOPS ABNORMALLY ---',mess)
    sys.exit(0)
    return

##------------------------------------------------------------------------------
## read files
##------------------------------------------------------------------------------

def requestdir(Mdir):
    """The world-writable directory where users drop their requests

    It is kept apart from Mdir: Python imports modules from the directory of
    the scripts, so Mdir must not be writable by users."""
    return Mdir+'requests/'

def readallfile(filename):
    """Read an entire mns file and store it in a dictionary"""
    with open(filename+'.mns','r') as filein:
        allvar = json.load(filein)
    return allvar


##------------------------------------------------------------------------------
## write files
##------------------------------------------------------------------------------

def writeallfile(filename,allvar):
    """Write an entire mns file

    The file is written under a hidden temporary name and then renamed, so
    that readers never see it half written."""
    dirname, basename = os.path.split(filename)
    tmp = os.path.join(dirname, '.'+basename+'.tmp')
    with open(tmp,'w') as fileout:
        json.dump(allvar,fileout,indent=2)
    os.chmod(tmp,0o644)
    os.replace(tmp,filename+'.mns')
    return


##------------------------------------------------------------------------------
## Miscellaneous
##------------------------------------------------------------------------------
    
def isundefined(value):
    """True for a missing value: None or NaN"""
    return value is None or (isinstance(value,float) and math.isnan(value))

def applydefaults(charge,defaults): # May be useless
    """Apply the default settings if left undefined"""
    for jobid in charge:
        job = charge[jobid]
        for key in ('RAM','Ncpu','HDmemory','priority'):
            if isundefined(job.get(key)):
                job[key] = defaults[key]
    return charge

def find_queued_jobs(charge): # New function
    """ find the jobs that are in "que" status"""
    que_jobs = {}
    for jobid in charge:
        job = charge[jobid]
        if job['status'] == 'que':
            que_jobs[jobid] = job
    return que_jobs

def sortbypriority(jobs): # New function
    """ Sort the jobs by priority """
    id_prior = []
    for jobid in jobs:
        job = jobs[jobid]
        id_prior.append([jobid, job['priority']])
    id_prior.sort(key=lambda x: x[1], reverse=True)
    return id_prior  

def find_available_resources(status,realvalue): # New function
    """Find the available resources"""
    used_cpu = status['Ncpu']
    used_ram = status['RAM']
    used_hd = status['HDmemory']
    free_cpu = realvalue['Ncpu'] - used_cpu
    free_ram = realvalue['RAM'] - used_ram
    free_hd = realvalue['HDmemory'] - used_hd
    if free_cpu > 0 and free_ram > 0 and free_hd > 0:
        free_space = True
    else:
        free_space = False
    available = {'free_space': free_space, 'Ncpu': free_cpu, 'RAM': free_ram, 'HDmemory': free_hd}
    return available

def check_for_submissions(available,priority_list,queue): # New function
    # It replaces the test... functions
    """Check for the jobs to be submitted

    Jobs start in priority order: a job that does not fit yet blocks the
    ones after it, otherwise a stream of small jobs could starve a big one."""
    free_cpu = available['Ncpu']
    free_ram = available['RAM']
    free_hd = available['HDmemory']
    to_be_submitted = []
    for i in range(len(priority_list)):
        jobid = priority_list[i][0]
        job = queue[jobid]
        if free_cpu >= job['Ncpu'] and free_ram >= job['RAM'] and free_hd >= job['HDmemory']:
            to_be_submitted.append(jobid)
            free_cpu -= job['Ncpu']
            free_ram -= job['RAM']
            free_hd -= job['HDmemory']
        else:
            break
    return to_be_submitted

def isrunning(pid):
    """Check if a process is alive

    Jobs are children of the demon: an ended child stays a zombie, which
    still looks alive, until it is reaped here."""
    try:
        ended, _ = os.waitpid(pid,os.WNOHANG)
        return ended == 0
    except ChildProcessError: # not a child, or already reaped
        pass
    try:
        os.kill(pid,0)
    except ProcessLookupError:
        return False
    except PermissionError:
        pass
    return True

def endjob(charge, status, messf): # New function
    """find the ended jobs"""
    for jobid in list(charge):
        job = charge[jobid]
        if job['status'] == 'run' and not isrunning(int(job['pid'])):
            writemessage(f"Job {job['script']} ended",messf)
            update_status(status,job,-1)
            delete(jobid,charge)
    return charge, status

def delete(jobid, jobs): # New function
    """delete a job"""
    deleted = jobs.pop(jobid,None)
    return deleted

def update_status(status,job,val): # New function
    """Update the machine status"""
    status['Ncpu'] = status['Ncpu'] + job['Ncpu'] * val
    status['RAM'] = status['RAM'] + job['RAM'] * val
    status['HDmemory'] = status['HDmemory'] + job['HDmemory'] * val

def cleanstatus(status,Mdir,chargef,statusf,messf="messages"): # New function
    """Clean up the machine status at startup

    Pending requests are kept: they are handled once the demon runs."""
    # clean the status file, keeping the job counter
    status["status"] = "up"
    status["RAM"] = 0
    status["Ncpu"] = 0
    status["HDmemory"] = 0
    # kill running jobs
    charge = readallfile(chargef)
    for jobid in charge:
        job = charge[jobid]
        if job['status'] == 'run':
            pid = job['pid']
            try:
                os.kill(int(pid),SIGTERM)
            except:
                pass
    writemessage('All jobs killed',mess=f"{Mdir}/{messf}")
    writeallfile(chargef,{})
    start = readallfile(statusf)
    start["status"] = "up"
    writeallfile(statusf,start)
    writemessage('status machine cleaned',mess=f"{Mdir}/{messf}")
    return status

def checkdemon(file6,file2,file3,mess): # Updated function
    """Check if the demon must run or stop"""
    stop = readallfile(file6)
    if stop['status'] == 'stop':
        Mdir = os.path.dirname(file6)+'/'
        status = cleanstatus(readallfile(file3),Mdir,file2,file6)
        writeallfile(file3,status)
        stop['status'] = 'down'
        writeallfile(file6,stop)
        writemessage('---MINOSSE STOPS---',mess)
        sys.exit(0)
    return

def checkdeletedjob(file7,file2,file3,mess): # Updated function
    """check the requests of deleting jobs, collected by writejob"""
    inp = readallfile(file7)
    if not inp:
        return
    alljobs = readallfile(file2)
    status = readallfile(file3)
    for delid in inp:
        delinst = inp[delid]
        duser = delinst['user']
        if delinst.get('id'):
            targets = [str(delinst['id'])]
        else:
            targets = [jobid for jobid in alljobs
                       if alljobs[jobid]['script'] == delinst.get('script')]
        for jobid in targets:
            job = alljobs.get(jobid)
            if job is None:
                writewarning(f"{duser} tried to delete job {jobid}, which does not exist",mess)
            elif job['user'] != duser:
                writewarning(f"{duser} tried to delete job {jobid} of {job['user']}",mess)
            else:
                if job['status'] == 'run':
                    try:
                        os.kill(int(job['pid']),SIGTERM)
                    except ProcessLookupError: # it has just ended
                        pass
                    update_status(status,job,-1)
                delete(jobid,alljobs)
                writemessage(f"job {jobid} {job['script']} deleted",mess)
    writeallfile(file2,alljobs)
    writeallfile(file3,status)
    writeallfile(file7,{})
    return

def readrequest(filename):
    """Read a request file written by a user, returning (owner, content)

    Request directories are world-writable, so links and special files are
    refused, and the owner of the file, not its content, names the user."""
    fd = os.open(filename,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
    with os.fdopen(fd) as filein:
        info = os.fstat(filein.fileno())
        if not S_ISREG(info.st_mode):
            raise ValueError('not a regular file')
        content = json.load(filein)
    return pwd.getpwuid(info.st_uid).pw_name, content

def requestname(prefix):
    """A unique name for a request file, sorting in submission order"""
    return f"{prefix}{time.time_ns()}_{os.getpid()}"

def collectrequests(Rdir,prefix,mess):
    """Read and remove the requests in Rdir, in submission order

    Returns {name: request}; the user of a request is the owner of its file."""
    requests = {}
    for f in sorted(os.listdir(Rdir)):
        if f.startswith(prefix) and f.endswith('.mns'):
            try:
                user, request = readrequest(Rdir + f)
                request['user'] = user
            except (OSError, ValueError, TypeError) as error:
                writewarning(f"request {f} rejected: {error}",mess)
            else:
                requests[f[len(prefix):-len('.mns')]] = request
            os.remove(Rdir + f)
    return requests

def writejob(Rdir,fileA,fileB,mess):
    """add the new requests to the tracked ones"""
    tracked = readallfile(fileB)
    tracked.update(collectrequests(Rdir,fileA,mess))
    writeallfile(fileB, tracked)

def invalidjob(job,node):
    """Why a submitted job can never run on the node, or None"""
    for key in ('Ncpu','RAM','HDmemory','priority'):
        value = job.get(key)
        if not isinstance(value,int) or isinstance(value,bool):
            return f"{key} must be an integer"
    if job['Ncpu'] < 1:
        return "at least one cpu is needed"
    for key in ('RAM','HDmemory'):
        if job[key] < 0:
            return f"{key} must not be negative"
    for key in ('Ncpu','RAM','HDmemory'):
        if job[key] > node[key]:
            return f"{key} {job[key]} exceeds the node ({node[key]})"
    script = job.get('script')
    if not isinstance(script,str) or not script.startswith('/'):
        return "the script must be an absolute path"
    return None

def submitjobs(Rdir,fileA,file2,file3,node,mess):
    """queue the new submitted jobs, giving them increasing ids

    The last id is kept in the status file, so ids are never reused."""
    charge = readallfile(file2)
    status = readallfile(file3)
    for job in collectrequests(Rdir,fileA,mess).values():
        error = invalidjob(job,node)
        if error:
            writewarning(f"job {job.get('script')} of {job['user']} rejected: {error}",mess)
            continue
        status['lastid'] = status.get('lastid',0) + 1
        while str(status['lastid']) in charge:
            status['lastid'] += 1
        jobid = str(status['lastid'])
        # only the demon decides these
        job.update(id=jobid, status='que', pid='', runtime='')
        charge[jobid] = job
        writemessage(f"Job {jobid} {job['script']} queued",mess)
    writeallfile(file2,charge)
    writeallfile(file3,status)
             
def getpid(pid,opt):
    """extract the pid of all child processes"""
    pppp,ppp,pall=[],[],[]
    ps=os.popen('pstree -lp '+str(pid)).readlines()
    for line in ps:
        a,b,pp=[],[],[]
        for j in range(len(line)):
            if '(' == line[j]:
                a.append(j)
            if ')' == line[j]:
                b.append(j)
        for j in range(len(a)):
            p=''
            for k in range(a[j]+1,b[j]):
                p=p+str((line[k]))
            pp.append(p)
            pall.append(p)
        ppp.append(pp)
    for i in range(len(ppp)):
        pppp.append(ppp[i][len(ppp[i])-1])
    if opt == 'all':
        get=pall
    else:
        get=pppp
    return get

def ifrunning(Mdir):
    """check if minosse is running"""
    ps=os.popen('ps -eo args | grep Minosse.py').readlines()
    status='down'
    a=[]
    for line in ps:
        path=line.split()[1]
        if path == f"{Mdir}Minosse.py":
            status='ok'
            a.append('ok')
    if len(a) > 1 :
        print('')
        print ('-'*40)
        print ('more than one minosse demon running!')
        print ('-'*40,'\n')
        sys.exit(0)
    if status == 'down':
        print('')
        print ('-'*40)
        print ('no minosse demon running!')
        print('activate minosse with:\t sudo minosse start')
        print ('-'*40,'\n')
        sys.exit(0)     
    return

def chainjob(charge):
    """check if the jobs are chained"""
    script=findall(charge,'script')
    chain=findall(charge,'chain')
    for i in range(len(chain)):
        if chain[i] != 'none':
            for j in range(len(script)):
                if chain[i] == script[j]:
                    charge=delete(charge,i,varnames)
    return charge
