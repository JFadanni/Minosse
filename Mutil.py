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
__version__ = '$Revision: 1.0.0 $'
__credits__ = """Guido van Rossum, for an excellent programming language."""

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

varnames=['hostname','Ncpu','RAM','HDtype','HDmemory','architecture','status'
          ,'priority','pid','Njob','script','user','id','chain'
          ,'subtime','runtime']

##------------------------------------------------------------------------------
## Imports
##------------------------------------------------------------------------------

import os
import sys
import time
from   signal import SIGTERM 


##-------------------------------------------------------------------------------
## CLASSES 
##------------------------------------------------------------------------------
class server_status:
    def __init__(self,mode,hostname, HDtype,architecture,status):
        self.mode = mode
        self.hostname = hostname
        self.HDtype = HDtype
        self.architecture = architecture
        self.status = status
        self.Ncpu = 0 
        self.priority = 0
        self.RAM = 0
        self.HDmemory = 0

    def update_Ncpu(self,new_Ncpu):
        self.Ncpu = new_Ncpu

    def update_ram(self,new_RAM):
        self.RAM = new_RAM

    def update_priority(self,new_priority):
        self.priority = new_priority

    def update_HDmemory(self,new_HDmemory):
        self.HDmemory = new_HDmemory

    def toggle_status(self):
        status = self.status
        if status == 'up':
            self.status = 'down'
        elif status == 'down':
            self.status = 'up'
        else:
            self.status = 'down' 

    def get_server_status(self):
        status = {}
        status['mode'] = self.mode
        status['hostname'] = self.hostname
        status['HDtype'] = self.HDtype
        status['architecture'] = self.architecture
        status['status'] = self.status
        status['Ncpu'] = self.Ncpu
        status['priority'] = self.priority
        status['RAM'] = self.RAM
        status['HDmemory'] = self.HDmemory
        return status

    def __repr__(self):
        return f"{self.hostname}: {self.get_server_status()}"
        
class job:
    def __init__(self,ID,user,script,priority,Ncpu,RAM,Njob,chain,subtime):
       self.id = ID
       self.pid = None
       self.user = user
       self.script = script
       self.priority = priority
       self.Ncpu = Ncpu
       self.RAM = RAM
       self.Njob = Njob
       self.chain = chain
       self.status='que'
       self.subtime = subtime
       self.runtime = ''

    def get_job_info(self):
       job_info = {}
       job_info['id'] = self.id
       job_info['pid'] = self.pid
       job_info['user'] = self.user
       job_info['script'] = self.script
       job_info['priority'] = self.priority
       job_info['Ncpu'] = self.Ncpu
       job_info['RAM'] = self.RAM
       job_info['Njob'] = self.Njob
       job_info['chain'] = self.chain
       job_info['status'] = self.status
       job_info['subtime'] = self.subtime
       job_info['runtime'] = self.runtime
       return job_info

    def __repr__(self):
        return f"job {self.id}: {self.get_job_info()}" 

    def __str__(self):
        if self.status == 'que':
            return f"job: {self.id}: \npid: {self.pid}\nuser: {self.user}\nscript: {self.script}\nNcpu: {self.Ncpu}\n \
                RAM: {self.RAM}\nNjob: {self.Njob}\nchain: {self.chain}\nstatus: {self.status}\n \
                    subtime: {self.subtime}"
        else:
            return f"job: {self.id}: \npid: {self.pid}\nuser: {self.user}\nscript: {self.script}\nNcpu: {self.Ncpu}\n \
                RAM: {self.RAM}\nNjob: {self.Njob}\nchain: {self.chain}\nstatus: {self.status}\n \
                    subtime: {self.subtime}\nruntime:{self.runtime}"



    def apply_defaults(self, default_values):
        self.priority = default_values['priority']
        self.Ncpu = default_values['Ncpu']
        self.RAM = default_values['RAM']

    def set_pid(self,pid):
        self.pid = pid 

    def start_job(self):
        #mettere qui tutta la parte relativa alla sottomissione del job
        user = self.user
        script = self.script
        try:
            subpro=Popen(["runuser -u "+user+" "+script],shell=True)
            self.pid = subpro.pid
            self.status = 'running'
        except:
            writewarning(' Something wrong in the '+script+' script')
            writewarning(' Job aborted')
            self.status = 'aborted'
            
    def kill_job(self,signal):
        pass
        #mettere qui i comandi per killare il job


##------------------------------------------------------------------------------
## write messages
##------------------------------------------------------------------------------

def writeinitializationmessage():
    """write the opening string in the messages file""" 
    with open(mess,'w') as log:
        log.write(time.asctime()+'   ---MINOSSE START---\n')
    return

def writemessage(wrote):
    """write a string in the messages file"""
    with open(mess,'a') as log:
        log.write(time.asctime()+'   '+wrote+'\n')
    return

def writewarning(wrote):
    """write a WARNING message"""
    writemessage('WARNING:'+wrote)
    return

def writefatalerror(wrote):
    """write an error message end exit from Minosse"""
    writemessage('FATAL:  '+wrote)
    writemessage('--- MINOSSE STOPS ABNORMALLY ---')
    sys.exit(0)
    return


##------------------------------------------------------------------------------
##   Test for submission
##------------------------------------------------------------------------------

def check_resources(needed,available):
    """ check wether the needed resources are available """
    if needed > available:
        return False
    else:
        return True

def test_algebric_absolute(job,status,realvalues):
    """test for the matching between available and needed resources """
    for r_need, r_used, r_name in zip((job.RAM,job.Ncpu,job.HDmemory),(status.RAM,status.Ncpu,status.HDmemory),('RAM','Ncpu','HDmemory')):
        test = check_resources(r_need+r_used,resources[r_name])
        if not test:
            return False

def test_algebric_user(job,user_stuatus,user_resources):
    """test for the matching between available and needed resources for the submitting user """
    for r_need, r_used, r_name in zip((job.RAM,job.Ncpu,job.HDmemory),(user_status.RAM,user_status.Ncpu,user_status.HDmemory),('RAM','Ncpu','HDmemory')):
        test = check_resources(r_need+r_used,user_resources[r_name])
        if not test:
            return False



##------------------------------------------------------------------------------
## read files
##------------------------------------------------------------------------------

def readallfile(filename):
    """Read an entire mns file and store it in lists"""
    varname=[]
    varvalue=[]
    filecomplete='false'
    ## impose the completeness of the file
    while (filecomplete=='false'):     
        try:
            with open(filename+'.mns','r') as filein:
                output=filein.read()
        except:
            writefatalerror(filename+' file not found in your minosse directory!') 
        output=output.split('\n')
        for i in range(len(output)):
            if output[i].strip() == '!end':
                filecomplete='true'
    ## divide in two lists the first one with the variable name
    ## the second one with the variable value
    for i in range(len(output)):
        case=output[i].strip()
        if case == '' or case == '!start' or case == '!end':
            pass
        else:
            element=output[i].split(':')
            varname.append(element[0].strip())
            if element[1].strip() == '':
                element[1]='none'
            varvalue.append(element[1].strip())
    allvar=[varname,varvalue]
    return allvar 

##------------------------------------------------------------------------------
## write files
##------------------------------------------------------------------------------

def writeallfile(filename,allvar):
    """Write an entire mns file """
    with open(filename+'.mns','w') as fileout:
        fileout.write('!start'+'\n')
        for i in range(len(allvar[0])):
            fileout.write(str(allvar[0][i])+': '+str(allvar[1][i])+'\n')
        fileout.write('!end\n')
    return

##------------------------------------------------------------------------------
## find or find and replace
##------------------------------------------------------------------------------

def findall(allvar,findvarname):
    """find in a varialbe in a list"""
    varvalue=[]
    for i in range(len(allvar[0])):
        if allvar[0][i] == findvarname or allvar[0][i] == 'none':
            varvalue.append(allvar[1][i])
    return varvalue

def replace(allvar,value,varname,index):
    """change the value of a variable in a specified position"""
    cou=[]
    for i in range(len(allvar[0])):
        if allvar[0][i] == varname :
            cou.append(i)
    allvar[1][cou[index]]=value
    return allvar

##------------------------------------------------------------------------------
## Miscellaneous
##------------------------------------------------------------------------------
    
def applydefaults(allvar1,allvar2,varname):
    """Apply the default settings content in the default.mns file"""
    def1=findall(allvar2,varname)
    for i in range(len(allvar1[0])):
        if allvar1[0][i] == varname and allvar1[1][i] == 'none' :
            allvar1[1][i]=def1[0]
    return allvar1

def difference(allvar1,allvar2,varname):
    """Make the difference between two lists of variables"""
    diffvar=[]
    var1=findall(allvar1,varname)
    var2=findall(allvar2,varname)
    for i in range(len(var1)):
        diffvar.append(int(var1[i])-int(var2[i]))
    return diffvar

def testalgebric(allvar1,allvar2,allvar3,varname):
    """Make a test for numeric varible if allvar1-allvar3 <= allvar3"""
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

def testtext(allvar1,allvar2,varname):
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

def choice(tests,allvar1):
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

def prior(trial,allvar):
    """Test priority of the machines and calculations"""
    prio=[]
    ref=findall(allvar,'priority')
    for i in range(len(trial[1])):
        prio.append(int(ref[trial[1][i]]))
    Mprio=prio.index(max(prio))
    Fprio=trial[1][Mprio]
    return Fprio

def newstatus(allvar1,allvar2,varname,job):
    """Modify the status after the job choice"""
    def1=findall(allvar2,varname)
    for i in range(len(allvar1[0])):
        if allvar1[0][i] == varname :
            allvar1[1][i]=int(allvar1[1][i])+int(def1[job])
    return allvar1

def newstatus2(allvar1,allvar2,varname,job):
    """Modify the status after the job end"""
    def1=findall(allvar2,varname)
    for i in range(len(allvar1[0])):
        if allvar1[0][i] == varname :
            allvar1[1][i]=int(allvar1[1][i])-int(def1[job])
    return allvar1

def endjob(charge,subprocesses):
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

def delete(charge,ended,varnames):
    """delete a job"""
    index=[]
    for j in range(len(varnames)):
        n=0
        for i in range(len(charge[0])):
            if varnames[j] == charge[0][i]:
                if n == ended:
                    index.append(i)    
                n=n+1
    index.sort()
    for i in range(len(index)-1,-1,-1):
        charge[0].pop(index[i])
        charge[1].pop(index[i])
    return charge

def makelist(tot,a,b):
    """create a list from variables"""
    l1=tot[0]
    l2=tot[1]
    l1.append(a)
    l2.append(b)
    tot=[l1,l2]
    return tot

def cleanstatus(status):
    """Clean up the machine status at startup"""
    status=replace(status,'up','status',0)
    status=replace(status,'0','RAM',0)
    status=replace(status,'0','Ncpu',0)
    status=replace(status,'0','HDmemory',0)
    ls=os.listdir(Mdir)
    for i in range(len(ls)):
        if ls[i].startswith(file5) or ls[i].startswith(file8):
            infile=ls[i].split('.')[0]
            os.remove(Mdir+infile+'.mns')
    charge=readallfile(file2)
    pid=findall(charge,'pid')
    run=findall(charge,'status')
    for i in range(len(pid)):
        if run[i] == 'run':
            try:
                tokill=getpid(pid[i],'all')
                os.kill(int(pid[i]),SIGTERM)
                for j in range(len(tokill)):
                    os.kill(int(tokill[j]),SIGTERM)
            except:
                pass
    writemessage('All jobs killed')
    writeallfile(file2,[[],[]])
    start=readallfile(file6)
    start=replace(start,'up','status',0)
    writeallfile(file6,start)
    writemessage('status machine cleaned')
    return status

def checkdemon(file6):
    """Check if the demon must run or stop"""
    stop=readallfile(file6)
    if findall(stop,'status')[0] == 'stop':
        status=readallfile(file3)
        cleanstatus(status)
        stop=replace(stop,'down','status',0)
        writeallfile(file6,stop)
        writemessage('---MINOSSE STOPS---')
        sys.exit(0)
    return

def checkdeletedjob(file7,file2,varnames):
    """check the requests of deleting jobs"""
    writejob(Mdir,file8,file7)
    inp=readallfile(file7)
    if inp != [[],[]] :
        id=findall(inp,'id')
        script=findall(inp,'script')
        opt=findall(inp,'priority')
        user=findall(inp,'user')
        for i in range(len(id)):
            if id[i] != 'none' or script[i] != 'none' :
                charge=readallfile(file2)
                Ljob=findall(charge,'id')
                Lscript=findall(charge,'script')
                Luser=findall(charge,'user')
                for j in range(len(Ljob)):
                     if (Ljob[j] == id[i] or Lscript[j] == script[i]) and ( Luser[j] == user[i]  or user[i] == 'root'):
                          writemessage('killing job '+Lscript[j])
                          if findall(charge,'status')[j] == 'run':
                               try:
                                   pid=findall(charge,'pid')[j]
                                   tokill=getpid(pid,opt[i])
                                   if opt[i] == 'all':
                                      os.kill(int(pid),SIGTERM)
                                   for k in range(len(tokill)):
                                      os.kill(int(tokill[k]),SIGTERM)
                               except:
                                   pass
                                   ## patch 16 june 2008
                                   ##charge=delete(charge,j,varnames)
                                   ##writeallfile(file2,charge)
                                   ##inp=replace(inp,'none','id',i)
                                   ##writeallfile(file7,inp)
                          else:
                               charge=delete(charge,j,varnames)
                               writeallfile(file2,charge)
                               ##inp=replace(inp,'none','id',i)
                               ##writeallfile(file7,inp)
        inp=[[], []]
        writeallfile(file7,inp)
    return

def writejob(Mdir,fileA,fileB):
    """check the new submitted job"""
    ls=os.listdir(Mdir)
    for i in range(len(ls)):
        if ls[i].startswith(fileA):
            tmp=[]
            charge=[[],[]]
            infile=ls[i].split('.')[0]
            tmp=readallfile(Mdir+infile)
            scriptA=findall(tmp,'script')
            ch=readallfile(fileB)
            scriptB=findall(ch,'script')
            if scriptA[0] in scriptB :
               pass
            else:
               charge[0]=ch[0]+tmp[0]
               charge[1]=ch[1]+tmp[1]
               writeallfile(fileB,charge)
            os.remove(Mdir+infile+'.mns')
    return

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

def ifrunning():
    """check if minosse is running"""
    ps=os.popen('ps -eo args | grep Minosse.py').readlines()
    status='down'
    a=[]
    for line in ps:
        path=line.split()[1]
        if path == Mdir+'Minosse.py':
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
