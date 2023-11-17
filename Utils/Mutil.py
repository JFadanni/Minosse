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
__date__ = "12th Nov 2023"
__version__ = '$Revision: 1.3.0 $'
__credits__ = """Piero Altoè for a nice queue manager."""

##------------------------------------------------------------------------------
## Imports
##------------------------------------------------------------------------------

import os
from   signal import SIGTERM
import sys
import time

##------------------------------------------------------------------------------
## Files names
##------------------------------------------------------------------------------

MDIR="$instdir/"
FILE1=MDIR+'nodes'
FILE2=MDIR+'charge'
FILE3=MDIR+'status'
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
## write messages
##------------------------------------------------------------------------------

def writeinitializationmessage():
    """write the opening string in the messages file""" 
    with open(MESS,'w',encoding='utf-8') as log:
        log.write(time.asctime()+'   ---MINOSSE START---\n')

def writemessage(wrote):
    """write a string in the messages file"""
    with open(MESS,'a',encoding='utf-8') as log:
        log.write(time.asctime()+'   '+wrote+'\n')

def writewarning(wrote):
    """write a WARNING message"""
    writemessage('WARNING:'+wrote)

def writefatalerror(wrote):
    """write an error message end exit from Minosse"""
    writemessage('FATAL:  '+wrote)
    writemessage('--- MINOSSE STOPS ABNORMALLY ---')
    sys.exit(0)

##------------------------------------------------------------------------------
## read files
##------------------------------------------------------------------------------

def readallfile(filename):
    """Read an entire mns file and store it in lists"""
    varname=[]
    varvalue=[]
    filecomplete='false'
    ## impose the completeness of the file
    while filecomplete=='false':
        try:
            with open(filename+'.mns','r',encoding='utf-8') as filein:
                output=filein.read()
        except:
            writefatalerror(filename+' file not found in your minosse directory!')
        output=output.split('\n')
        for outputi in output:
            if outputi.strip() == '!end':
                filecomplete='true'
    ## divide in two lists the first one with the variable name
    ## the second one with the variable value
    for outputi in output:
        case=outputi.strip()
        if case in("","!start","!end"):
            pass
        else:
            element=outputi.split(':')
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
    with open(filename+'.mns','w',encoding='utf-8') as fileout:
        fileout.write('!start'+'\n')
        for i in range(len(allvar[0])):
            fileout.write(str(allvar[0][i])+': '+str(allvar[1][i])+'\n')
        fileout.write('!end\n')

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
    for i,var1i in enumerate(var1):
        diffvar.append(int(var1i)-int(var2[i]))
    return diffvar

def testalgebric(allvar1,allvar2,allvar3,varname):
    """Make a test for numeric varible if allvar1-allvar3 <= allvar3"""
    free=[]
    index1=[]
    index2=[]
    ref=difference(allvar1,allvar2,varname)
    req=findall(allvar3,varname)
    for i,reqi in enumerate(req):
        for j,refj in enumerate(ref):
            if refj-int(reqi) >= 0:
                free.append(refj-int(reqi))
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
    for i,reqi in enumerate(req):
        for j, refj in enumerate(ref):
            if refj == reqi or refj == 'none' or reqi == 'none':
                free.append(refj)
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
    mprio=prio.index(max(prio))
    fprio=trial[1][mprio]
    return fprio

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
    for i,pi in enumerate(p):
        if pi is not None:
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

def delete(charge,ended,names):
    """delete a job"""
    index=[]
    for varname in names:
        n=0
        for i in range(len(charge[0])):
            if varname == charge[0][i]:
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
    ls=os.listdir(MDIR)
    for lsi in ls:
        if lsi.startswith(FILE5) or lsi.startswith(FILE8):
            infile=lsi.split('.')[0]
            os.remove(MDIR+infile+'.mns')
    charge=readallfile(FILE2)
    pid=findall(charge,'pid')
    run=findall(charge,'status')
    for i, pidi in enumerate(pid):
        if run[i] == 'run':
            try:
                tokill=getpid(pidi,'all')
                os.kill(int(pidi),SIGTERM)
                for kill in tokill:
                    os.kill(int(kill),SIGTERM)
            except:
                pass
    writemessage('All jobs killed')
    writeallfile(FILE2,[[],[]])
    start=readallfile(FILE6)
    start=replace(start,'up','status',0)
    writeallfile(FILE6,start)
    writemessage('status machine cleaned')
    return status

def checkdemon(file6):
    """Check if the demon must run or stop"""
    stop=readallfile(file6)
    if findall(stop,'status')[0] == 'stop':
        status=readallfile(FILE3)
        cleanstatus(status)
        stop=replace(stop,'down','status',0)
        writeallfile(file6,stop)
        writemessage('---MINOSSE STOPS---')
        sys.exit(0)

def checkdeletedjob(file7,file2,variables):
    """check the requests of deleting jobs"""
    writejob(MDIR,FILE8,file7)
    inp=readallfile(file7)
    if inp != [[],[]] :
        jid=findall(inp,'id')
        script=findall(inp,'script')
        opt=findall(inp,'priority')
        user=findall(inp,'user')
        for i, idi in enumerate(jid):
            if idi != 'none' or script[i] != 'none' :
                charge=readallfile(file2)
                ljob=findall(charge,'id')
                lscript=findall(charge,'script')
                luser=findall(charge,'user')
                for j, ljobj in enumerate(ljob):
                    if ((ljobj == idi or lscript[j] == script[i]) and
                        ( luser[j] == user[i]  or user[i] == 'root')):
                        writemessage('killing job '+lscript[j])
                        if findall(charge,'status')[j] == 'run':
                            try:
                                pid=findall(charge,'pid')[j]
                                tokill=getpid(pid,opt[i])
                                if opt[i] == 'all':
                                    os.kill(int(pid),SIGTERM)
                                for kill in tokill:
                                    os.kill(int(kill),SIGTERM)
                            except:
                                pass
                                ## patch 16 june 2008
                                ##charge=delete(charge,j,varnames)
                                ##writeallfile(file2,charge)
                                ##inp=replace(inp,'none','id',i)
                                ##writeallfile(file7,inp)
                        else:
                            charge=delete(charge,j,variables)
                            writeallfile(file2,charge)
                            ##inp=replace(inp,'none','id',i)
                            ##writeallfile(file7,inp)
        inp=[[], []]
        writeallfile(file7,inp)

def writejob(mdir,filea,fileb):
    """check the new submitted job"""
    lsoutput=os.listdir(mdir)
    for lsi in lsoutput:
        if lsi.startswith(filea):
            tmp=[]
            charge=[[],[]]
            infile=lsi.split('.')[0]
            tmp=readallfile(mdir+infile)
            scripta=findall(tmp,'script')
            inch=readallfile(fileb)
            scriptb=findall(inch,'script')
            if scripta[0] in scriptb :
                pass
            else:
                charge[0]=inch[0]+tmp[0]
                charge[1]=inch[1]+tmp[1]
                writeallfile(fileb,charge)
            os.remove(mdir+infile+'.mns')

def getpid(pid,opt):
    """extract the pid of all child processes"""
    pppp,ppp,pall=[],[],[]
    ps=os.popen('pstree -lp '+str(pid)).readlines()
    for line in ps:
        a,b,pp=[],[],[]
        for j, linej in enumerate(line):
            if '(' == linej:
                a.append(j)
            if ')' == linej:
                b.append(j)
        for j, aj in enumerate(a):
            p=''
            for k in range(aj+1,b[j]):
                p=p+str((line[k]))
            pp.append(p)
            pall.append(p)
        ppp.append(pp)
    for pppi in ppp:
        pppp.append(pppi[len(pppi)-1])
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
        if path == MDIR+'Minosse.py':
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

def chainjob(charge):
    """check if the jobs are chained"""
    script=findall(charge,'script')
    chain=findall(charge,'chain')
    for i, chaini in enumerate(chain):
        if chaini != 'none':
            for scriptj in script:
                if chaini == scriptj:
                    charge=delete(charge,i,varnames)
    return charge
