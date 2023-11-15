#! /usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import time
import json
from   signal import SIGTERM
from   subprocess import check_output

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
    writemessage('WARNING:'+wrote)
    return

def writefatalerror(wrote,mess):
    """write an error message end exit from Minosse"""
    writemessage('FATAL:  '+wrote)
    writemessage('--- MINOSSE STOPS ABNORMALLY ---')
    sys.exit(0)
    return

##------------------------------------------------------------------------------
## read files
##------------------------------------------------------------------------------

def readallfile(filename):
    """Read an entire mns file and store it in a dictionary"""
    with open(filename+'.mns','r') as filein:
        allvar = json.load(filein)
    return allvar


##------------------------------------------------------------------------------
## write files
##------------------------------------------------------------------------------

def writeallfile(filename,allvar):
    """Write an entire mns file """
    with open(filename+'.mns','w') as fileout:
        json.dump(allvar,fileout,indent=2)
    return

##------------------------------------------------------------------------------
## find or find and replace
##------------------------------------------------------------------------------

def findall(allvar,findvarname): # Useless in new setup
    """find in a varialbe in a list"""
    return allvar[findvarname]

def replace(allvar,value,varname,index): # Useless in new setup
    """change the value of a variable in a specified position"""
    allvar[varname][index]=value
    return allvar

##------------------------------------------------------------------------------
## Miscellaneous
##------------------------------------------------------------------------------
    
def applydefaults(charge,defaults): # May be useless
    """Apply the default settings if left undefined"""
    for jobid in charge:
        job = charge[jobid]
        if job['RAM'] == float("NaN"):
            charge[jobid]['RAM'] = defaults['RAM']
        if job['Ncpu'] == float("NaN"):
            charge[jobid]['Ncpu'] = defaults['Ncpu']
        if job['HDmemory'] == float("NaN"):
            charge[jobid]['HDmemory'] = defaults['HDmemory']
        if job['priority'] == float("NaN"):
            charge[jobid]['priority'] = defaults['priority']
    return charge

def difference(allvar1,allvar2,varname): # Already replaced
    """Make the difference between two lists of variables"""
    diffvar=[]
    var1=findall(allvar1,varname)
    var2=findall(allvar2,varname)
    for i in range(len(var1)):
        diffvar.append(int(var1[i])-int(var2[i]))
    return diffvar

def testalgebric(allvar1,allvar2,allvar3,varname): # Already replaced
    """Make a test for numeric varible if allvar1-allvar2 <= allvar3"""
    free=[]
    index1=[]
    index2=[]
    ref=difference(allvar1,allvar2,varname)
    req=findall(allvar3,varname)
    for i in range(len(req)):
        for j in range(len(ref)):
                if ref[j]-int(req[i]) >= 0:
                    free.append(ref[j]-int(req[i]))
                    index1.append(i)
                    index2.append(j)
    freepos=[free,index1,index2]
    return freepos

def testtext(allvar1,allvar2,varname): # Already replaced
    """Make a test for test variable if allvar1[varname] == allvar2[varname]"""
    free=[]
    index1=[]
    index2=[]
    ref=findall(allvar1,varname)
    req=findall(allvar2,varname)
    for i in range(len(req)):
        for j in range(len(ref)):
                if ref[j] == req[i] or ref[j] == 'none' or req[i] == 'none':
                    free.append(ref[j])
                    index1.append(i)
                    index2.append(j)
    freepos=[free,index1,index2]
    return freepos

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
    """Check for the jobs to be submitted """
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
    return to_be_submitted

def choice(tests,allvar1): # Useless in new setup
    """Merge all the tests results finding the free machine"""
    a,b,c=[],[],[]
    trial=tests[0]
    for i in range(1,len(tests)):
        for j in range(len(trial[0])):
            for k in range(len(tests[i][0])):
                if trial[1][j] == tests[i][1][k] and trial[2][j] == tests[i][2][k]:
                    a.append(trial[0][j])
                    b.append(trial[1][j])
                    c.append(trial[2][j])
        trial=[a,b,c]
        a,b,c=[],[],[]
    ref=findall(allvar1,'hostname')
    for i in range(len(trial[0])):
        trial[0][i]=ref[trial[2][i]]
    return trial

def prior(trial,allvar): # Useless in new setup
    """Test priority of the machines and calculations"""
    prio=[]
    ref=findall(allvar,'priority')
    for i in range(len(trial[1])):
        prio.append(int(ref[trial[1][i]]))
    Mprio=prio.index(max(prio))
    Fprio=trial[1][Mprio]
    return Fprio

def newstatus(allvar1,allvar2,varname,job): # Useless in new setup
    """Modify the status after the job choice"""
    def1=findall(allvar2,varname)
    for i in range(len(allvar1[0])):
        if allvar1[0][i] == varname :
            allvar1[1][i]=int(allvar1[1][i])+int(def1[job])
    return allvar1

def newstatus2(allvar1,allvar2,varname,job): # Useless in new setup
    """Modify the status after the job end"""
    def1=findall(allvar2,varname)
    for i in range(len(allvar1[0])):
        if allvar1[0][i] == varname :
            allvar1[1][i]=int(allvar1[1][i])-int(def1[job])
    return allvar1

def endjob1(charge,subprocesses):## old function
    """find the ended jobs"""  
    p=[]
    ended='no'
    for i in range(len(subprocesses[0])):
        p.append(subprocesses[0][i].poll())
    for i in range(0,len(p)):
        if p[i] != None:
            ended=i
    if ended == 'no':
        job='no'
        result=[job,subprocesses]
    else:
        sta=findall(charge,'Njob')
        job=sta.index(str(subprocesses[1][ended]))
        subprocesses[0].pop(ended)
        subprocesses[1].pop(ended)        
        result=[job,subprocesses]
    return result

def endjob(charge, status,messf): # New function
    """find the ended jobs"""
    psaux = check_output("ps -aux | awk '{print $2}'", shell=True,text=True)
    running_processes = psaux.split('\n')[1:-1]
    for jobid in charge:
        job = charge[jobid]
        if job['status'] == 'run':
            pid = job['pid']
            if not(pid in running_processes):
                job['status'] = 'end'
                writemessage(f"Job {job['script']} ended",messf)
                update_status(charge,job,-1)
                ended  =  delete(jobid,charge)
    return charge, status

def delete(jobid,jobs): # New function
    """delete a job"""
    deleted = jobs.pop(jobid,None)
    return deleted

def update_status(status,job,val): # New function
    """Update the machine status"""
    status['Ncpu'] = status['Ncpu'] + job['Ncpu'] * val
    status['RAM'] = status['RAM'] + job['RAM'] * val
    status['HDmemory'] = status['HDmemory'] + job['HDmemory'] * val

def cleanstatus(status,Mdir,chargef,statusf,remove="remove",subjob="subjob",messf="messages"): # New function
    """Clean up the machine status at startup"""
    # clean the status file
    status["status"] = "up"
    status["RAM"] = 0
    status["Ncpu"] = 0
    status["HDmemory"] = 0
    # clean minosse directory
    ls=os.listdir(Mdir)
    for i in range(len(ls)):
        if ls[i].startswith(remove) or ls[i].startswith(subjob):
            infile=ls[i].split('.')[0]
            os.remove(Mdir+infile+'.mns')
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

def checkdemon(file6,file3,mess): # Updated function
    """Check if the demon must run or stop"""
    stop = readallfile(file6)
    if stop['status'] == 'stop':
        status = readallfile(file3)
        cleanstatus(status)
        stop['status'] = 'down'
        writeallfile(file6,stop)
        writemessage('---MINOSSE STOPS---',mess)
        sys.exit(0)
    return

def checkdeletedjob(file7,file2,file8,file3,mess): # Updated function
    """check the requests of deleting jobs"""
    writejob(Mdir,file8,file7)
    inp = readallfile(file7)
    status = readallfile(file3)
    if inp:
        alljobs = readallfile(file2)
        for delid in inp:
            delinst = inp[delid]
            script = delinst['script']
            id = delinst['id']
            opt = delinst['all']
            duser = delinst['user']
            if id:
                tbdel = alljobs[id]
                juser = tbdel['user']
                if juser == duser:
                    if tbdel['status'] == 'run':
                        pid = tbdel['pid']
                        try:
                            os.kill(pid,SIGTERM)
                            deleted = delete(id,alljobs)
                            update_status(status,tbdel,-1)
                        except:
                            writewarning(f"Unable to kill job {id}",mess)
                    else:
                        deleted = delete(id,alljobs)
                else:
                    writewarning(f"trying to delete a job of another user",mess)
            if script:
                for job in alljobs:
                    if job['script'] == script and job['user'] == duser:
                        if job['status'] == 'run':
                            pid = job['pid']
                            try:
                                os.kill(pid,SIGTERM)
                                deleted = delete(job['id'],alljobs)
                                update_status(status,job,-1)
                            except:
                                writewarning(f"Unable to kill job {script}",mess)
                        else:
                            deleted = delete(job['id'],alljobs)
            if deleted:
                writemessage(f"job {script} deleted",mess)
    writeallfile(file2,alljobs)
    inp = {}
    writeallfile(file7,inp)
    return

def writejob(Mdir,fileA,fileB):
    """check the new submitted jobs"""
    ls = os.listdir(Mdir)
    tracked_jobs = readallfile(fileB)
    for i, f in enumerate(ls):
        if f.startswith(fileA):
            subjname = f.split('.')[0]
            jobid = subjname[6:]
            if jobid in tracked_jobs:
                pass
            else:
                job = readallfile(Mdir + subjname)
                tracked_jobs[jobid] = job[jobid]
                os.remove(Mdir + f)
    writeallfile(fileB, tracked_jobs)
             
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
