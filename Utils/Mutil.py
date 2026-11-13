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
__credits__ = """Piero Altoè for a nice queue manager."""

def readversion():
    """The version of Minosse, from the VERSION file installed next to the
    scripts (or at the top of the source tree)"""
    here = os.path.dirname(os.path.abspath(__file__))
    for path in (os.path.join(here,'VERSION'), os.path.join(here,os.pardir,'VERSION')):
        try:
            with open(path,encoding='utf-8') as filein:
                return filein.read().strip()
        except OSError:
            pass
    return 'unknown'

__version__ = readversion()

##------------------------------------------------------------------------------
## write messages
##------------------------------------------------------------------------------

def writeinitializationmessage(mess):
    """write the opening string in the messages file""" 
    with open(mess,'w',encoding='utf-8') as log:
        log.write(time.asctime()+'   ---MINOSSE START---\n')
    return

def writemessage(wrote,mess):
    """write a string in the messages file"""
    with open(mess,'a',encoding='utf-8') as log:
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
    sys.exit(1)

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
    with open(filename+'.mns','r',encoding='utf-8') as filein:
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
    with open(tmp,'w',encoding='utf-8') as fileout:
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

def holdchained(queue,charge):
    """Leave out of the queue the jobs chained to an earlier job (msub -l):
    they wait while a job with that script is queued or running"""
    order = list(charge)
    ready = {}
    for jobid in queue:
        chain = queue[jobid].get('chain','none')
        earlier = order[:order.index(jobid)]
        if chain != 'none' and any(charge[other]['script'] == chain for other in earlier):
            continue
        ready[jobid] = queue[jobid]
    return ready

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
    # every job needs a cpu; whether it also fits in RAM and disk is
    # checked job by job: a node without disk (HDmemory 0) still runs jobs
    free_space = free_cpu > 0
    available = {'free_space': free_space, 'Ncpu': free_cpu, 'RAM': free_ram, 'HDmemory': free_hd}
    return available

def check_for_submissions(available,priority_list,queue,quotas=None,used=None): # New function
    # It replaces the test... functions
    """Check for the jobs to be submitted

    Jobs start in priority order: a job that does not fit yet blocks the
    ones after it, otherwise a stream of small jobs could starve a big one.

    With quotas, used gives the cpus and RAM each user's running jobs hold.
    A job that would take its user over the quota waits without blocking
    the other users, but it blocks the later jobs of its user, for the same
    reason.  A forced job (msub --force) ignores the quota."""
    quotas = quotas or {}
    used = {user: dict(usage) for user, usage in (used or {}).items()}
    free = {key: available[key] for key in ('Ncpu','RAM','HDmemory')}
    held = set()     # users with a job waiting for their quota
    to_be_submitted = []
    for jobid, _ in priority_list:
        job = queue[jobid]
        user = job['user']
        quota = userquota(user,quotas)
        if quota is not None and job.get('force') is not True:
            if user in held or not withinquota(job,quota,used.get(user)):
                # a job bigger than a quota lowered after its submission
                # waits for the quota to rise again, without holding the user
                if withinquota(job,quota):
                    held.add(user)
                continue
        if not all(free[key] >= job[key] for key in free):
            break
        to_be_submitted.append(jobid)
        for key in free:
            free[key] -= job[key]
        usage = used.setdefault(user,dict.fromkeys(QUOTAKEYS,0))
        for key in QUOTAKEYS:
            usage[key] += job[key]
    return to_be_submitted

##------------------------------------------------------------------------------
## quotas
##------------------------------------------------------------------------------

QUOTAKEYS = ('Ncpu','RAM')

def minimumquota(node):
    """The smallest quota of a user: one cpu, and the RAM per cpu of the node,
    so that everybody can run at least a job of the node's average size"""
    return {'Ncpu': 1, 'RAM': node['RAM'] // node['Ncpu']}

def invalidquotas(quotas,node):
    """Why the content of quotas.mns is malformed, or None

    It maps user names to the cpus and the RAM their running jobs can use,
    as {"Ncpu": cpus, "RAM": MB}."""
    if not isinstance(quotas,dict):
        return "it must map user names to quotas"
    least = minimumquota(node)
    for user, quota in quotas.items():
        if not isinstance(quota,dict) or set(quota) != set(QUOTAKEYS):
            return f"the quota of {user} must give Ncpu and RAM, and nothing else"
        for key in QUOTAKEYS:
            if not isinstance(quota[key],int) or isinstance(quota[key],bool):
                return f"the {key} quota of {user} must be an integer"
            if quota[key] < least[key]:
                return f"the {key} quota of {user} must be at least {least[key]}"
    return None

def parsequotas(text,node):
    """The quotas in the text of quotas.mns; ValueError if malformed"""
    quotas = json.loads(text)
    error = invalidquotas(quotas,node)
    if error:
        raise ValueError(error)
    return quotas

def readquotas(filename,node):
    """Read the quotas of the users: none without the file

    Raises ValueError if the file is malformed."""
    try:
        with open(filename+'.mns','r',encoding='utf-8') as filein:
            return parsequotas(filein.read(),node)
    except FileNotFoundError:
        return {}

def smallestquota(quotas):
    """The quota of the users left out of the file: the smallest cpus and
    the smallest RAM in it, so that, once quotas are enforced, nobody, not
    even a user new to the machine, escapes them"""
    return {key: min(quota[key] for quota in quotas.values()) for key in QUOTAKEYS}

def userquota(user,quotas):
    """The cpus and RAM the running jobs of a user can use, None without limit"""
    if user in quotas:
        return quotas[user]
    if quotas:
        return smallestquota(quotas)
    return None

def withinquota(job,quota,used=None):
    """True if the job, with the running jobs that use used, fits in quota"""
    used = used or {}
    return all(used.get(key,0) + job[key] <= quota[key] for key in QUOTAKEYS)

def formatquota(quota):
    """A quota in a few words"""
    return f"{quota['Ncpu']} cpus {quota['RAM']} MB"

def describequotas(quotas):
    """The quotas in one line, for the messages file"""
    if not quotas:
        return "no quotas"
    listed = ', '.join(f"{user} {formatquota(quota)}" for user, quota in quotas.items())
    return f"{listed}, other users {formatquota(smallestquota(quotas))}"

def loadquotas(filename,node,loaded,mess):
    """Reread the quotas, since the admin changes them while the demon runs

    loaded is (text of the file, quotas) from the previous call, (None, {})
    the first time: the text, not the time of the file, tells a change, since
    an editor can write the file twice within the same clock tick.  A
    malformed file is reported once, and the previous quotas are kept."""
    unreadable = None
    try:
        with open(filename+'.mns','r',encoding='utf-8') as filein:
            text = filein.read()
    except FileNotFoundError:
        text = '{}'
    except (OSError, ValueError) as error:
        text = unreadable = str(error)
    if text == loaded[0]:
        return loaded
    try:
        if unreadable:
            raise ValueError(unreadable)
        quotas = parsequotas(text,node)
    except ValueError as error:
        writewarning(f"quotas.mns ignored, the previous quotas are kept: {error}",mess)
        return text, loaded[1]
    writemessage(f"Quotas: {describequotas(quotas)}",mess)
    return text, quotas

def usedresources(charge):
    """The cpus and RAM held by the running jobs of each user"""
    used = {}
    for job in charge.values():
        if job['status'] == 'run':
            usage = used.setdefault(job['user'],dict.fromkeys(QUOTAKEYS,0))
            for key in QUOTAKEYS:
                usage[key] += job[key]
    return used

def overquota(job,quotas):
    """Why a job, unless forced, is bigger than the quota of its user, or None"""
    quota = userquota(job['user'],quotas)
    if quota is None or job.get('force') is True:
        return None
    for key in QUOTAKEYS:
        if job[key] > quota[key]:
            return f"{key} {job[key]} exceeds the quota of {job['user']} ({quota[key]})"
    return None

def shareram(cpus,nusers,node):
    """The RAM quota going with cpus when nusers share the node

    An equal share of the RAM, but never less than the RAM per cpu of the
    node times cpus, so that the user can fill their cpus with jobs of the
    node's average size, nor more than the node."""
    percpu = node['RAM'] // node['Ncpu']
    return min(node['RAM'], max(node['RAM'] // nusers, cpus * percpu))

def splitquotas(users,node):
    """Share the node equally among the users: the same cpus for each, at
    least one, and the RAM going with them"""
    if not users:
        return {}
    cpus = max(1, node['Ncpu'] // len(users))
    return {user: {'Ncpu': cpus, 'RAM': shareram(cpus,len(users),node)}
            for user in users}

def machineusers(logindefs='/etc/login.defs'):
    """The people using the machine: the users with a login shell and a uid
    in the range login.defs gives to people, not to system accounts"""
    limits = {'UID_MIN': 1000, 'UID_MAX': 60000}
    try:
        with open(logindefs,encoding='utf-8') as filein:
            for line in filein:
                fields = line.split()
                if len(fields) > 1 and fields[0] in limits and fields[1].isdigit():
                    limits[fields[0]] = int(fields[1])
    except OSError:
        pass
    return sorted(entry.pw_name for entry in pwd.getpwall()
                  if limits['UID_MIN'] <= entry.pw_uid <= limits['UID_MAX']
                  and not entry.pw_shell.endswith(('nologin','false')))

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

def jobcommand(job):
    """The command line the demon runs a job with"""
    return ["runuser","-u",job['user'],"--",job['script']]

def isjobprocess(job):
    """True if the pid of a job still belongs to it

    After a crash or a reboot the pid may belong to another process."""
    try:
        with open(f"/proc/{int(job['pid'])}/cmdline",'rb') as filein:
            cmdline = filein.read().split(b'\0')[:-1]
    except (OSError, ValueError):
        return False
    return cmdline == [arg.encode() for arg in jobcommand(job)]

def killjob(job):
    """Terminate a running job with all its processes

    Each job runs in its own session led by runuser: the whole process group
    is signalled, since killing runuser alone leaves the job running."""
    try:
        os.killpg(int(job['pid']),SIGTERM)
    except (OSError, ValueError): # it has just ended
        pass

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

def cleanstatus(status,Mdir,chargef,statusf,remove="remove",subjob="subjob",messf="messages",keep=True): # New function
    """Clean up the machine status at startup and stop

    Running jobs are killed.  The pending jobs, queued or submitted while
    the demon was down, are kept for the next run unless keep is False."""
    mess = f"{Mdir}/{messf}"
    # clean the status file, keeping the job counter
    status["status"] = "up"
    status["RAM"] = 0
    status["Ncpu"] = 0
    status["HDmemory"] = 0
    # kill running jobs
    charge = readallfile(chargef)
    for jobid in list(charge):
        job = charge[jobid]
        if job['status'] == 'run':
            if isjobprocess(job):
                killjob(job)
            delete(jobid,charge)
        elif not keep:
            delete(jobid,charge)
    writeallfile(chargef,charge)
    writemessage('All running jobs killed',mess)
    if keep:
        writemessage(f"{len(pendingjobs(Mdir,chargef,subjob))} pending jobs kept",mess)
    else:
        Rdir = requestdir(Mdir)
        for f in os.listdir(Rdir):
            if f.startswith(remove) or f.startswith(subjob):
                os.remove(Rdir+f)
        writemessage('Pending jobs deleted',mess)
    start = readallfile(statusf)
    start["status"] = "up"
    writeallfile(statusf,start)
    writemessage('status machine cleaned',mess=f"{Mdir}/{messf}")
    return status

def pendingjobs(Mdir,chargef,subjob="subjob"):
    """The jobs waiting to run, as (user, script): the queued ones and the
    submissions not read yet"""
    pending = [(job['user'],job['script']) for job in readallfile(chargef).values()
               if job['status'] == 'que']
    Rdir = requestdir(Mdir)
    for f in sorted(os.listdir(Rdir)):
        if f.startswith(subjob) and f.endswith('.mns'):
            try:
                user, job = readrequest(Rdir+f)
                pending.append((user,job.get('script')))
            except (OSError, ValueError, AttributeError): # rejected later
                pass
    return pending

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
                    killjob(job)
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
    with os.fdopen(fd,encoding='utf-8') as filein:
        info = os.fstat(filein.fileno())
        if not S_ISREG(info.st_mode):
            raise ValueError('not a regular file')
        content = json.load(filein)
    try:
        return pwd.getpwuid(info.st_uid).pw_name, content
    except KeyError: # a deleted user, for example
        raise ValueError(f"unknown owner {info.st_uid}") from None

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
    if not isinstance(job.get('force',False),bool):
        return "force must be true or false"
    return None

def submitjobs(Rdir,fileA,file2,file3,node,mess,quotas=None):
    """queue the new submitted jobs, giving them increasing ids

    The last id is kept in the status file, so ids are never reused."""
    charge = readallfile(file2)
    status = readallfile(file3)
    for job in collectrequests(Rdir,fileA,mess).values():
        error = invalidjob(job,node) or overquota(job,quotas or {})
        if error:
            writewarning(f"job {job.get('script')} of {job['user']} rejected: {error}",mess)
            continue
        status['lastid'] = status.get('lastid',0) + 1
        while str(status['lastid']) in charge:
            status['lastid'] += 1
        jobid = str(status['lastid'])
        # only the demon decides these
        job.update(id=jobid, status='que', pid='', runtime='')
        job.setdefault('subtime',time.strftime("%m/%d/%y %H.%M.%S", time.localtime()))
        charge[jobid] = job
        writemessage(f"Job {jobid} {job['script']} queued",mess)
    writeallfile(file2,charge)
    writeallfile(file3,status)
             
def demonpids(Mdir):
    """The pids of the Minosse demons running from Mdir

    Read from /proc: depending on the environment, ps cuts long command
    lines."""
    demon = f"{Mdir}Minosse.py".encode()
    pids = []
    for pid in os.listdir('/proc'):
        if not pid.isdigit():
            continue
        try:
            with open(f"/proc/{pid}/cmdline",'rb') as filein:
                args = filein.read().split(b'\0')
        except OSError: # it has just ended
            continue
        # a Python interpreter running the demon, not an editor opening it
        if len(args) > 1 and b'python' in os.path.basename(args[0]) and args[1] == demon:
            pids.append(int(pid))
    return pids

def ifrunning(Mdir):
    """check if minosse is running"""
    running = demonpids(Mdir)
    if len(running) > 1 :
        print('')
        print ('-'*40)
        print ('more than one minosse demon running!')
        print ('-'*40,'\n')
        sys.exit(0)
    if not running:
        print('')
        print ('-'*40)
        print ('no minosse demon running!')
        print('activate minosse with:\t sudo minosse start')
        print ('-'*40,'\n')
        sys.exit(0)     
    return
