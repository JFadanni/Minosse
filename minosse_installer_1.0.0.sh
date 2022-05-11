#!/bin/bash

## installing script

echo '
Copyright 2007,2008 Piero Altoè

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

Minosse version 1.0.0, 6th May 2022
---------------------------------------------------------'

function fatal { 
	echo ' '
	echo '#################################'
	echo '###### INSTALLATION ABORT #######'
	echo '#################################'
	echo ' '
	echo '---------------------------------------------------------'
	exit 
}

function check() {
	if [[ -z $1 ]]; then
		echo "variable not defined!!!"
		fatal
	fi
}

if [[ $USER != 'root' ]]; then
	echo -e '\nPermission denied, you are not superuser'
	fatal
fi

run=$(ps -eo args | grep Minosse.py | grep python | awk '{print($2)}' | sed 's/Minosse.py//' )  
if [[ -n $run ]]; then
	echo -e '\nAn older version of Minosse is running'
	echo -e '\n########## ATTENTION ##########\n'
	echo 'Do you want to stop and delete it?[yes/No]'
	read sto
	if [[ -z $sto ]]; then
		sto='N'
	fi
	if [ $sto = 'Yes' -o $sto = 'Y' -o $sto = 'y' -o $sto = 'yes' ] ; then
		minosse stop
                lrun=$(grep '  link' $run/minosse_uninst.sh | sed 's/link=/ /' | awk '{print($1)}')
		rm -r $run $lrun/minosse $lrun/minosse_uninst $lrun/mstat $lrun/msub $lrun/mdel
                echo -e 'Older version removed\n'
	else
		fatal
	fi
fi

echo 'insert the Minosse installation directory [/usr/local/Minosse]'
read instdir
if [[ -z $instdir ]]; then
	instdir='/usr/local/Minosse'
fi

if [[ -e $instdir ]]; then
	if [[ -d $instdir ]]; then
		echo -e "\n$instdir already exists delete the contents?[Yes/no]"
		read var
		if [[ -z $var ]]; then
			var='Y'
		fi
		if [ $var = 'Yes' -o $var = 'Y' -o $var = 'y' -o $var = 'yes' ] ; then
			rm -rf $instdir/*
			echo 'contents deleted'
		else
			fatal
		fi
	else
		echo -e "\n$instdir is a file cannot create the $instdir directory"
		fatal
	fi
else
	echo "$instdir does not exist do you want to create it?[Yes/no]"
	read var
	if [[ -z $var ]]; then
		var='Y'
	fi
	if [ $var = 'Yes' -o $var = 'Y' -o $var = 'y' -o $var = 'yes' ]; then
		mkdir $instdir
	else
		fatal
	fi
fi

echo -e '\ninsert the Minosse working partition [/scratch]'
read workdir
if [[ -z $workdir ]]; then
	workdir='/scratch'
fi

check $workdir
partition=$(df | fgrep -w $workdir | awk '{printf "%i", $2/1048576}')
partname=$(df | fgrep -w $workdir | awk '{print $6}')
devname=$(df | fgrep -w $workdir | awk '{print $1}')
check $partition
check $partname
check $devname

cpus=$(grep 'processor' /proc/cpuinfo -c)
if [[ -z $cpus ]]; then	
	echo -e '\ninsert the number of cpus'
	read cpus
fi
check $cpus

memory=$(free | grep 'Mem:' | awk '{printf "%i", $2/1024}')
if [[ -z $memory ]]; then                       
	echo -e '\ninsert the ram memory'
	read memory
fi
check $memory

echo 'insert the ram memory left to the operative system (MB) [300]'
read sysmem
if [[ -z $sysmem ]]; then
	sysmem=300
fi
check $sysmem

totmem=$(($memory-$sysmem))
if [[ -n "$(hdparm -i $devname | grep ATA)" ]]; then
	echo -e '\neide/sata disk identified'
	HDtype='eide'
elif [[ -n "$(hdparm -i $devname | grep SCSI)" ]]; then 
	echo -e '\nscsi disk identified'
	HDtype='scsi'
else
	echo -e '\ndisk type unidentified, please insert manually [Eide/scsi]'
	read HDtype
fi

if [[ -z $HDtype ]]; then
	HDtype='eide'
fi

check $HDtype

echo -e '\ninsert the node priority'
read prior

if [[ -z $prior ]]; then
	prior='50'
fi
check $prior

echo -e '\nDo you agree with the following configuration?'
echo -e "hostname	$HOSTNAME		"
echo -e "Ncpus		$cpus			"
echo -e "RAM(MB)\t	$totmem			"
echo -e "HDtype		$HDtype			"
echo -e "HDmemory(GB)	$partition		"
echo -e "architecture	$HOSTTYPE		"
echo -e "priority	$prior			\n"
echo '[Yes/no]'
read var2
echo ''
if [[ -z $var2 ]]; then
	var2='Y'
fi

if [ $var2 = 'Yes' -o $var2 = 'Y' -o $var2 = 'y' -o $var2 = 'yes' ]; then
	echo -e 'OK\n'
else
	fatal
fi

cd $instdir

echo -e '\nwrite Minosse files:'
echo 'charge.mns'
cat <<END> charge.mns
!start
!end
END

echo 'conf.mns'
cat <<END> conf.mns
!start
status: up
!end
END

echo 'delete.mns'
cat <<END> delete.mns
!start
!end
END

echo 'node.mns'
cat <<END> nodes.mns
!start
NODE: none
hostname: $HOSTNAME
Ncpu: $cpus 
RAM: $totmem
HDtype: $HDtype
HDmemory: $partition
architecture: $HOSTTYPE
status: up
priority: $prior
!end
END

echo 'defaults.mns'
cat <<END> defaults.mns
!start
hostname: $HOSTNAME
Ncpu: $Dcpus
RAM: $Dmemory
HDtype: $HDtype
HDmemory: $DHD
architecture: $HOSTTYPE
status: que
priority: $Dprior
!end
END

echo 'status.mns'
cat <<END> status.mns
!start
NODE: none
hostname: $HOSTNAME
Ncpu: 0
RAM: 0
HDtype: $HDtype
HDmemory: 0
architecture: $HOSTTYPE
status: up
priority: $prior
!end
END

cat <<END> Mheader.py
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

END

cat Mheader.py > Minosse.py
cat <<"END">> Minosse.py
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

ifrunning()
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
            subpro=Popen(["runuser -u"+user+" "+script],shell=True)
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
END

cat Mheader.py > Mutil.py
cat <<"END">> Mutil.py
##------------------------------------------------------------------------------
## Imports
##------------------------------------------------------------------------------

import os
import sys
import time
from   signal import SIGTERM 

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
    if len(a) != 1 :
        sys.exit(0)
    if status == 'down':
        print ('\n','-'*40)
        print ('no minosse demon running!')
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
END

cat Mheader.py > Msub.py
cat <<"END">> Msub.py
##------------------------------------------------------------------------------
## Imports
##------------------------------------------------------------------------------

from   optparse   import OptionParser
import getpass
import socket
import random
import time

##------------------------------------------------------------------------------
## Flags
##------------------------------------------------------------------------------

parser = OptionParser(usage="%prog", version="%prog 1.0.0")

parser.add_option("-c", "--cpus",
                  action="store", dest="cpus", default="1", type="int", 
                  help="nomber of cpus required [default=1]")
parser.add_option("-m", "--memory",
                  action="store", dest="memory", default="700", type="int",
                  help="RAM memory requirement [default=700 MB]")
parser.add_option("-d", "--harddisck",
                  action="store", dest="HD", default="00", type="int",
                  help="HD scratch space required [default=00 GB]")
parser.add_option("-p", "--priority",
                  action="store", dest="priority", default="70", type="int",
                  help="set the priority of a job [default=70]")
parser.add_option("-f", "--file",
                  action="store", dest="file",
                  help="set the name of the job script")
parser.add_option("-l", "--link",
                  action="store", dest="chain", default="none",
                  help="set the name of the chained job [default=none]")

(options, args) = parser.parse_args()

##------------------------------------------------------------------------------
## Main program
##------------------------------------------------------------------------------

ifrunning()

id=str(random.randint(1, 1000000))

subjob=[varnames,
        [socket.gethostname(),options.cpus,options.memory,'eide',options.HD,'x86_64','que',
         options.priority,'','',options.file ,getpass.getuser(),id,options.chain,time.strftime("%m/%d/%y %H.%M.%S", time.localtime()),'']]

writeallfile(Mdir+file5+id,subjob)
END

cat Mheader.py > Mstat.py
cat <<"END">> Mstat.py
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
END

cat Mheader.py > Mdel.py
cat <<"END">> Mdel.py
##------------------------------------------------------------------------------
## Imports
##------------------------------------------------------------------------------

from   optparse   import OptionParser
import random
import getpass

##------------------------------------------------------------------------------
## Flags
##------------------------------------------------------------------------------

parser = OptionParser(usage="%prog", version="%prog 1.0.0")

parser.add_option("-j", "--job",
                  action="store", dest="job",  default="none",
                  help="id number")

parser.add_option("-s", "--script",
                  action="store", dest="script", default="none",
                  help="script name")

parser.add_option("-a", "--all",
                  action="store_true", dest="all", default=False,
                  help="kill all processes from the top script to the last child")

(options, args) = parser.parse_args()

##------------------------------------------------------------------------------
## Main program
##------------------------------------------------------------------------------

ifrunning()

RND=str(random.randint(1, 1000000))

if options.all == True :
   opt='all'
else:
   opt='none'

deljob=[['script','id','priority','user'],
        [options.script,options.job,opt,getpass.getuser()]]


writeallfile(Mdir+file8+RND,deljob)
END

rm Mheader.py

cat <<END> minosse
#! /bin/bash

#--------------------------------------------------------------------------------
#This file is part of Minosse.
#
#Minosse is free software: you can redistribute it and/or modify
#it under the terms of the GNU General Public License as published by
#the Free Software Foundation, either version 3 of the License, or
#(at your option) any later version.
#
#Minosse is distributed in the hope that it will be useful,
#but WITHOUT ANY WARRANTY; without even the implied warranty of
#MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#GNU General Public License for more details.
#
#You should have received a copy of the GNU General Public License
#along with Minosse.  If not, see <http://www.gnu.org/licenses/>.
#
#Minosse version 1.0.0, 6th May 2022
#---------------------------------------------------------------------------------

case "\$1" in
	start)
		run=\$(ps -eo args | grep Minosse.py | grep python)
		if [[ -n \$run ]]; then
			echo -e '\nMinosse is already running\n'
			exit
		else 
			nohup $instdir/Minosse.py > /dev/null 2>&1 &
			echo 'Starting Minosse ...'
			sleep 2
			echo 'Minosse demon started'
		fi
	;;
	stop)
		sed s/up/stop/ $instdir/conf.mns > $instdir/1
		mv $instdir/1 $instdir/conf.mns
		echo 'Stopping Minosse ...' 
		sleep 2
		echo 'Minosse demon stopped'
	;;
	*)
		echo -e "\nUsage: minosse start/stop"
		echo -e '  start or stop the minosse queue demon\n'
		exit
	;;
esac
END

cat <<"END"> README

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

Minosse version 1.0.0, 6th May 2022
--------------------------------------------------------------------------------

In this file you can find almost everything you need to install and run Minosse
batch system (it is a tiny program!).

If you are reading this file it means that the installer script works properly.
In order to run Minosse you must have installed python 3.* or newer on you 
machine.
Minosse installer does not support non default values for the machine 
specification.
In order to change them you need to left the default during the installation, 
and then edit the nodes.mns file and  change manually the values (if you 
can avoid, don't do it!).
Here an example of the nodes.mns:
!start
NODE: none		(number of node, not yet used)
hostname: dyn12		(name of the computer)
Ncpu: 4			(n° of cores)
RAM: 16138		(amount of ram memory MB)
HDtype: eide		(HD type)
HDmemory: 1846		(dimension of the working partition GB)
architecture: x86_64	(architecture type)
status: up		(status of the node, not yet used)
priority: 50		(priority of the node, not yet used)
!end

You can change each one of these values and then start Minosse.
ATTENTION do not specify values bigger than the physical values of the machine.

If you find problems installing or running this program please mail me
(piero.altoe@gmail.com), I will be happy to find a solution to your problem.

This release of Minosse works only for single workstation/server with N° SHM
processors.
There are no limits for the number of processors, RAM memory, or disk space 
which are supported by Minosse.

Minosse administrates your jobs through a simple scheme looking at the free 
resources of your system, so no real queues are created.
For example if you have 4 cpus but only 2 GB of RAM, two jobs requiring 
1.5 GB RAM (each one) cannot run at the same time, and Minosse queue up
one of these two.

During the installation, the script asks you in which directory you want 
to create the links. If this directory is not in your $PATH 
(like: /usr/local/bin or /urs/bin/) you cannot use the minosse commands simply 
typing the name of the command, but you need to specify the entire the path.

How to use:
Start/stop the demon (only root can do it):
 
minosse start/stop

Uninstall(only root can do it):

minosse_uninst

The flag -h gives you the usage for all the next commands.
Checking the queue status:

mstat or mstat -v (verbose) 

Submit a job:

msub -f "path/scriptname" -c "n° of cpu" -m "ram memory" 

delete a job:

mdel -j "job id" or -s "path/scriptname"

Here an example of a Gaussian03 submitting script:
#!/bin/bash

## to be sure is used correctly 
if [ -z $3 ]; then
   echo - '\nUsage: mg03 inputfile ncpu memory'
   echo -e '\n  Submit a Gaussian03 job to the Minosse queue system'
   exit
fi

## check if you are using .com extension or not
if [ $1 == ${1%.*}.com ]; then
job=${1%.*}
else
job=$1
fi

echo -e "\nSubmitting Gaussian-03 batch job $job to Minosse queue system\n"

## define where we are
PTH=$PWD

## from here to 'END3' is defined the script which minosse executes
cat <<END3> $job.nqs
#!/bin/bash

## check if the checkpoint exists
if [ -f $PTH/$job.chk ]; then
        cp $PTH/$job.chk /scratch/$USER/
fi

## check if the checkpoint is compressed
if [ -f $PTH/$job.chk.gz ]; then
        cp $PTH/$job.chk.gz /scratch/$USER/
        gzip -fd /scratch/$USER/$job.chk.gz
fi

## move to the working directory
cd /scratch/$USER/

## create the header of the Gaussian input file
cat <<END2 > $job.com_nqs
%chk=/scratch/$USER/$job
%int=/scratch/$USER/$job
%d2e=/scratch/$USER/$job
%rwf=/scratch/$USER/$job
%mem=$3MB
%nproc=$2
END2

cat $PTH/$job.com >> $job.com_nqs
## just to be sure put an empty line at the end of the input
echo ' ' >> $job.com_nqs

## run gaussian
g03 < $job.com_nqs > $PTH/$job.log 2>&1

## compress the checkpoint 
if [ -f $job.chk ]; then
        gzip -f $job.chk
fi

##remove some useless files 
rm Gau-*.scr
rm $job.com_nqs
rm $job.d2e $job.int $job.rwf
mv $job.chk.gz $PTH/

END3

## make executable the script
chmod a+x $job.nqs

## submit on Minosse
msub -f $PTH/$job.nqs -c $2 -m $3
END

echo -e '\nDo you want to see the README file?[Yes/no]'
read re

if [[ -z $re ]]; then
	re='Y'
fi

if [ $re = 'Yes' -o $re = 'Y' -o $re = 'y' -o $re = 'yes' ] ; then
	more README
	echo '-------------------------------------'
	echo 'END OF THE README FILE'
fi

cat << "EOF" > COPYING
 
                    GNU GENERAL PUBLIC LICENSE
                       Version 3, 29 June 2007

 Copyright (C) 2007 Free Software Foundation, Inc. <http://fsf.org/>
 Everyone is permitted to copy and distribute verbatim copies
 of this license document, but changing it is not allowed.

                            Preamble

  The GNU General Public License is a free, copyleft license for
software and other kinds of works.

  The licenses for most software and other practical works are designed
to take away your freedom to share and change the works.  By contrast,
the GNU General Public License is intended to guarantee your freedom to
share and change all versions of a program--to make sure it remains free
software for all its users.  We, the Free Software Foundation, use the
GNU General Public License for most of our software; it applies also to
any other work released this way by its authors.  You can apply it to
your programs, too.

  When we speak of free software, we are referring to freedom, not
price.  Our General Public Licenses are designed to make sure that you
have the freedom to distribute copies of free software (and charge for
them if you wish), that you receive source code or can get it if you
want it, that you can change the software or use pieces of it in new
free programs, and that you know you can do these things.

  To protect your rights, we need to prevent others from denying you
these rights or asking you to surrender the rights.  Therefore, you have
certain responsibilities if you distribute copies of the software, or if
you modify it: responsibilities to respect the freedom of others.

  For example, if you distribute copies of such a program, whether
gratis or for a fee, you must pass on to the recipients the same
freedoms that you received.  You must make sure that they, too, receive
or can get the source code.  And you must show them these terms so they
know their rights.

  Developers that use the GNU GPL protect your rights with two steps:
(1) assert copyright on the software, and (2) offer you this License
giving you legal permission to copy, distribute and/or modify it.

  For the developers' and authors' protection, the GPL clearly explains
that there is no warranty for this free software.  For both users' and
authors' sake, the GPL requires that modified versions be marked as
changed, so that their problems will not be attributed erroneously to
authors of previous versions.

  Some devices are designed to deny users access to install or run
modified versions of the software inside them, although the manufacturer
can do so.  This is fundamentally incompatible with the aim of
protecting users' freedom to change the software.  The systematic
pattern of such abuse occurs in the area of products for individuals to
use, which is precisely where it is most unacceptable.  Therefore, we
have designed this version of the GPL to prohibit the practice for those
products.  If such problems arise substantially in other domains, we
stand ready to extend this provision to those domains in future versions
of the GPL, as needed to protect the freedom of users.

  Finally, every program is threatened constantly by software patents.
States should not allow patents to restrict development and use of
software on general-purpose computers, but in those that do, we wish to
avoid the special danger that patents applied to a free program could
make it effectively proprietary.  To prevent this, the GPL assures that
patents cannot be used to render the program non-free.

  The precise terms and conditions for copying, distribution and
modification follow.

                       TERMS AND CONDITIONS

  0. Definitions.

  "This License" refers to version 3 of the GNU General Public License.

  "Copyright" also means copyright-like laws that apply to other kinds of
works, such as semiconductor masks.

  "The Program" refers to any copyrightable work licensed under this
License.  Each licensee is addressed as "you".  "Licensees" and
"recipients" may be individuals or organizations.

  To "modify" a work means to copy from or adapt all or part of the work
in a fashion requiring copyright permission, other than the making of an
exact copy.  The resulting work is called a "modified version" of the
earlier work or a work "based on" the earlier work.

  A "covered work" means either the unmodified Program or a work based
on the Program.

  To "propagate" a work means to do anything with it that, without
permission, would make you directly or secondarily liable for
infringement under applicable copyright law, except executing it on a
computer or modifying a private copy.  Propagation includes copying,
distribution (with or without modification), making available to the
public, and in some countries other activities as well.

  To "convey" a work means any kind of propagation that enables other
parties to make or receive copies.  Mere interaction with a user through
a computer network, with no transfer of a copy, is not conveying.

  An interactive user interface displays "Appropriate Legal Notices"
to the extent that it includes a convenient and prominently visible
feature that (1) displays an appropriate copyright notice, and (2)
tells the user that there is no warranty for the work (except to the
extent that warranties are provided), that licensees may convey the
work under this License, and how to view a copy of this License.  If
the interface presents a list of user commands or options, such as a
menu, a prominent item in the list meets this criterion.

  1. Source Code.

  The "source code" for a work means the preferred form of the work
for making modifications to it.  "Object code" means any non-source
form of a work.

  A "Standard Interface" means an interface that either is an official
standard defined by a recognized standards body, or, in the case of
interfaces specified for a particular programming language, one that
is widely used among developers working in that language.

  The "System Libraries" of an executable work include anything, other
than the work as a whole, that (a) is included in the normal form of
packaging a Major Component, but which is not part of that Major
Component, and (b) serves only to enable use of the work with that
Major Component, or to implement a Standard Interface for which an
implementation is available to the public in source code form.  A
"Major Component", in this context, means a major essential component
(kernel, window system, and so on) of the specific operating system
(if any) on which the executable work runs, or a compiler used to
produce the work, or an object code interpreter used to run it.

  The "Corresponding Source" for a work in object code form means all
the source code needed to generate, install, and (for an executable
work) run the object code and to modify the work, including scripts to
control those activities.  However, it does not include the work's
System Libraries, or general-purpose tools or generally available free
programs which are used unmodified in performing those activities but
which are not part of the work.  For example, Corresponding Source
includes interface definition files associated with source files for
the work, and the source code for shared libraries and dynamically
linked subprograms that the work is specifically designed to require,
such as by intimate data communication or control flow between those
subprograms and other parts of the work.

  The Corresponding Source need not include anything that users
can regenerate automatically from other parts of the Corresponding
Source.

  The Corresponding Source for a work in source code form is that
same work.

  2. Basic Permissions.

  All rights granted under this License are granted for the term of
copyright on the Program, and are irrevocable provided the stated
conditions are met.  This License explicitly affirms your unlimited
permission to run the unmodified Program.  The output from running a
covered work is covered by this License only if the output, given its
content, constitutes a covered work.  This License acknowledges your
rights of fair use or other equivalent, as provided by copyright law.

  You may make, run and propagate covered works that you do not
convey, without conditions so long as your license otherwise remains
in force.  You may convey covered works to others for the sole purpose
of having them make modifications exclusively for you, or provide you
with facilities for running those works, provided that you comply with
the terms of this License in conveying all material for which you do
not control copyright.  Those thus making or running the covered works
for you must do so exclusively on your behalf, under your direction
and control, on terms that prohibit them from making any copies of
your copyrighted material outside their relationship with you.

  Conveying under any other circumstances is permitted solely under
the conditions stated below.  Sublicensing is not allowed; section 10
makes it unnecessary.

  3. Protecting Users' Legal Rights From Anti-Circumvention Law.

  No covered work shall be deemed part of an effective technological
measure under any applicable law fulfilling obligations under article
11 of the WIPO copyright treaty adopted on 20 December 1996, or
similar laws prohibiting or restricting circumvention of such
measures.

  When you convey a covered work, you waive any legal power to forbid
circumvention of technological measures to the extent such circumvention
is effected by exercising rights under this License with respect to
the covered work, and you disclaim any intention to limit operation or
modification of the work as a means of enforcing, against the work's
users, your or third parties' legal rights to forbid circumvention of
technological measures.

  4. Conveying Verbatim Copies.

  You may convey verbatim copies of the Program's source code as you
receive it, in any medium, provided that you conspicuously and
appropriately publish on each copy an appropriate copyright notice;
keep intact all notices stating that this License and any
non-permissive terms added in accord with section 7 apply to the code;
keep intact all notices of the absence of any warranty; and give all
recipients a copy of this License along with the Program.

  You may charge any price or no price for each copy that you convey,
and you may offer support or warranty protection for a fee.

  5. Conveying Modified Source Versions.

  You may convey a work based on the Program, or the modifications to
produce it from the Program, in the form of source code under the
terms of section 4, provided that you also meet all of these conditions:

    a) The work must carry prominent notices stating that you modified
    it, and giving a relevant date.

    b) The work must carry prominent notices stating that it is
    released under this License and any conditions added under section
    7.  This requirement modifies the requirement in section 4 to
    "keep intact all notices".

    c) You must license the entire work, as a whole, under this
    License to anyone who comes into possession of a copy.  This
    License will therefore apply, along with any applicable section 7
    additional terms, to the whole of the work, and all its parts,
    regardless of how they are packaged.  This License gives no
    permission to license the work in any other way, but it does not
    invalidate such permission if you have separately received it.

    d) If the work has interactive user interfaces, each must display
    Appropriate Legal Notices; however, if the Program has interactive
    interfaces that do not display Appropriate Legal Notices, your
    work need not make them do so.

  A compilation of a covered work with other separate and independent
works, which are not by their nature extensions of the covered work,
and which are not combined with it such as to form a larger program,
in or on a volume of a storage or distribution medium, is called an
"aggregate" if the compilation and its resulting copyright are not
used to limit the access or legal rights of the compilation's users
beyond what the individual works permit.  Inclusion of a covered work
in an aggregate does not cause this License to apply to the other
parts of the aggregate.

  6. Conveying Non-Source Forms.

  You may convey a covered work in object code form under the terms
of sections 4 and 5, provided that you also convey the
machine-readable Corresponding Source under the terms of this License,
in one of these ways:

    a) Convey the object code in, or embodied in, a physical product
    (including a physical distribution medium), accompanied by the
    Corresponding Source fixed on a durable physical medium
    customarily used for software interchange.

    b) Convey the object code in, or embodied in, a physical product
    (including a physical distribution medium), accompanied by a
    written offer, valid for at least three years and valid for as
    long as you offer spare parts or customer support for that product
    model, to give anyone who possesses the object code either (1) a
    copy of the Corresponding Source for all the software in the
    product that is covered by this License, on a durable physical
    medium customarily used for software interchange, for a price no
    more than your reasonable cost of physically performing this
    conveying of source, or (2) access to copy the
    Corresponding Source from a network server at no charge.

    c) Convey individual copies of the object code with a copy of the
    written offer to provide the Corresponding Source.  This
    alternative is allowed only occasionally and noncommercially, and
    only if you received the object code with such an offer, in accord
    with subsection 6b.

    d) Convey the object code by offering access from a designated
    place (gratis or for a charge), and offer equivalent access to the
    Corresponding Source in the same way through the same place at no
    further charge.  You need not require recipients to copy the
    Corresponding Source along with the object code.  If the place to
    copy the object code is a network server, the Corresponding Source
    may be on a different server (operated by you or a third party)
    that supports equivalent copying facilities, provided you maintain
    clear directions next to the object code saying where to find the
    Corresponding Source.  Regardless of what server hosts the
    Corresponding Source, you remain obligated to ensure that it is
    available for as long as needed to satisfy these requirements.

    e) Convey the object code using peer-to-peer transmission, provided
    you inform other peers where the object code and Corresponding
    Source of the work are being offered to the general public at no
    charge under subsection 6d.

  A separable portion of the object code, whose source code is excluded
from the Corresponding Source as a System Library, need not be
included in conveying the object code work.

  A "User Product" is either (1) a "consumer product", which means any
tangible personal property which is normally used for personal, family,
or household purposes, or (2) anything designed or sold for incorporation
into a dwelling.  In determining whether a product is a consumer product,
doubtful cases shall be resolved in favor of coverage.  For a particular
product received by a particular user, "normally used" refers to a
typical or common use of that class of product, regardless of the status
of the particular user or of the way in which the particular user
actually uses, or expects or is expected to use, the product.  A product
is a consumer product regardless of whether the product has substantial
commercial, industrial or non-consumer uses, unless such uses represent
the only significant mode of use of the product.

  "Installation Information" for a User Product means any methods,
procedures, authorization keys, or other information required to install
and execute modified versions of a covered work in that User Product from
a modified version of its Corresponding Source.  The information must
suffice to ensure that the continued functioning of the modified object
code is in no case prevented or interfered with solely because
modification has been made.

  If you convey an object code work under this section in, or with, or
specifically for use in, a User Product, and the conveying occurs as
part of a transaction in which the right of possession and use of the
User Product is transferred to the recipient in perpetuity or for a
fixed term (regardless of how the transaction is characterized), the
Corresponding Source conveyed under this section must be accompanied
by the Installation Information.  But this requirement does not apply
if neither you nor any third party retains the ability to install
modified object code on the User Product (for example, the work has
been installed in ROM).

  The requirement to provide Installation Information does not include a
requirement to continue to provide support service, warranty, or updates
for a work that has been modified or installed by the recipient, or for
the User Product in which it has been modified or installed.  Access to a
network may be denied when the modification itself materially and
adversely affects the operation of the network or violates the rules and
protocols for communication across the network.

  Corresponding Source conveyed, and Installation Information provided,
in accord with this section must be in a format that is publicly
documented (and with an implementation available to the public in
source code form), and must require no special password or key for
unpacking, reading or copying.

  7. Additional Terms.

  "Additional permissions" are terms that supplement the terms of this
License by making exceptions from one or more of its conditions.
Additional permissions that are applicable to the entire Program shall
be treated as though they were included in this License, to the extent
that they are valid under applicable law.  If additional permissions
apply only to part of the Program, that part may be used separately
under those permissions, but the entire Program remains governed by
this License without regard to the additional permissions.

  When you convey a copy of a covered work, you may at your option
remove any additional permissions from that copy, or from any part of
it.  (Additional permissions may be written to require their own
removal in certain cases when you modify the work.)  You may place
additional permissions on material, added by you to a covered work,
for which you have or can give appropriate copyright permission.

  Notwithstanding any other provision of this License, for material you
add to a covered work, you may (if authorized by the copyright holders of
that material) supplement the terms of this License with terms:

    a) Disclaiming warranty or limiting liability differently from the
    terms of sections 15 and 16 of this License; or

    b) Requiring preservation of specified reasonable legal notices or
    author attributions in that material or in the Appropriate Legal
    Notices displayed by works containing it; or

    c) Prohibiting misrepresentation of the origin of that material, or
    requiring that modified versions of such material be marked in
    reasonable ways as different from the original version; or

    d) Limiting the use for publicity purposes of names of licensors or
    authors of the material; or

    e) Declining to grant rights under trademark law for use of some
    trade names, trademarks, or service marks; or

    f) Requiring indemnification of licensors and authors of that
    material by anyone who conveys the material (or modified versions of
    it) with contractual assumptions of liability to the recipient, for
    any liability that these contractual assumptions directly impose on
    those licensors and authors.

  All other non-permissive additional terms are considered "further
restrictions" within the meaning of section 10.  If the Program as you
received it, or any part of it, contains a notice stating that it is
governed by this License along with a term that is a further
restriction, you may remove that term.  If a license document contains
a further restriction but permits relicensing or conveying under this
License, you may add to a covered work material governed by the terms
of that license document, provided that the further restriction does
not survive such relicensing or conveying.

  If you add terms to a covered work in accord with this section, you
must place, in the relevant source files, a statement of the
additional terms that apply to those files, or a notice indicating
where to find the applicable terms.

  Additional terms, permissive or non-permissive, may be stated in the
form of a separately written license, or stated as exceptions;
the above requirements apply either way.

  8. Termination.

  You may not propagate or modify a covered work except as expressly
provided under this License.  Any attempt otherwise to propagate or
modify it is void, and will automatically terminate your rights under
this License (including any patent licenses granted under the third
paragraph of section 11).

  However, if you cease all violation of this License, then your
license from a particular copyright holder is reinstated (a)
provisionally, unless and until the copyright holder explicitly and
finally terminates your license, and (b) permanently, if the copyright
holder fails to notify you of the violation by some reasonable means
prior to 60 days after the cessation.

  Moreover, your license from a particular copyright holder is
reinstated permanently if the copyright holder notifies you of the
violation by some reasonable means, this is the first time you have
received notice of violation of this License (for any work) from that
copyright holder, and you cure the violation prior to 30 days after
your receipt of the notice.

  Termination of your rights under this section does not terminate the
licenses of parties who have received copies or rights from you under
this License.  If your rights have been terminated and not permanently
reinstated, you do not qualify to receive new licenses for the same
material under section 10.

  9. Acceptance Not Required for Having Copies.

  You are not required to accept this License in order to receive or
run a copy of the Program.  Ancillary propagation of a covered work
occurring solely as a consequence of using peer-to-peer transmission
to receive a copy likewise does not require acceptance.  However,
nothing other than this License grants you permission to propagate or
modify any covered work.  These actions infringe copyright if you do
not accept this License.  Therefore, by modifying or propagating a
covered work, you indicate your acceptance of this License to do so.

  10. Automatic Licensing of Downstream Recipients.

  Each time you convey a covered work, the recipient automatically
receives a license from the original licensors, to run, modify and
propagate that work, subject to this License.  You are not responsible
for enforcing compliance by third parties with this License.

  An "entity transaction" is a transaction transferring control of an
organization, or substantially all assets of one, or subdividing an
organization, or merging organizations.  If propagation of a covered
work results from an entity transaction, each party to that
transaction who receives a copy of the work also receives whatever
licenses to the work the party's predecessor in interest had or could
give under the previous paragraph, plus a right to possession of the
Corresponding Source of the work from the predecessor in interest, if
the predecessor has it or can get it with reasonable efforts.

  You may not impose any further restrictions on the exercise of the
rights granted or affirmed under this License.  For example, you may
not impose a license fee, royalty, or other charge for exercise of
rights granted under this License, and you may not initiate litigation
(including a cross-claim or counterclaim in a lawsuit) alleging that
any patent claim is infringed by making, using, selling, offering for
sale, or importing the Program or any portion of it.

  11. Patents.

  A "contributor" is a copyright holder who authorizes use under this
License of the Program or a work on which the Program is based.  The
work thus licensed is called the contributor's "contributor version".

  A contributor's "essential patent claims" are all patent claims
owned or controlled by the contributor, whether already acquired or
hereafter acquired, that would be infringed by some manner, permitted
by this License, of making, using, or selling its contributor version,
but do not include claims that would be infringed only as a
consequence of further modification of the contributor version.  For
purposes of this definition, "control" includes the right to grant
patent sublicenses in a manner consistent with the requirements of
this License.

  Each contributor grants you a non-exclusive, worldwide, royalty-free
patent license under the contributor's essential patent claims, to
make, use, sell, offer for sale, import and otherwise run, modify and
propagate the contents of its contributor version.

  In the following three paragraphs, a "patent license" is any express
agreement or commitment, however denominated, not to enforce a patent
(such as an express permission to practice a patent or covenant not to
sue for patent infringement).  To "grant" such a patent license to a
party means to make such an agreement or commitment not to enforce a
patent against the party.

  If you convey a covered work, knowingly relying on a patent license,
and the Corresponding Source of the work is not available for anyone
to copy, free of charge and under the terms of this License, through a
publicly available network server or other readily accessible means,
then you must either (1) cause the Corresponding Source to be so
available, or (2) arrange to deprive yourself of the benefit of the
patent license for this particular work, or (3) arrange, in a manner
consistent with the requirements of this License, to extend the patent
license to downstream recipients.  "Knowingly relying" means you have
actual knowledge that, but for the patent license, your conveying the
covered work in a country, or your recipient's use of the covered work
in a country, would infringe one or more identifiable patents in that
country that you have reason to believe are valid.

  If, pursuant to or in connection with a single transaction or
arrangement, you convey, or propagate by procuring conveyance of, a
covered work, and grant a patent license to some of the parties
receiving the covered work authorizing them to use, propagate, modify
or convey a specific copy of the covered work, then the patent license
you grant is automatically extended to all recipients of the covered
work and works based on it.

  A patent license is "discriminatory" if it does not include within
the scope of its coverage, prohibits the exercise of, or is
conditioned on the non-exercise of one or more of the rights that are
specifically granted under this License.  You may not convey a covered
work if you are a party to an arrangement with a third party that is
in the business of distributing software, under which you make payment
to the third party based on the extent of your activity of conveying
the work, and under which the third party grants, to any of the
parties who would receive the covered work from you, a discriminatory
patent license (a) in connection with copies of the covered work
conveyed by you (or copies made from those copies), or (b) primarily
for and in connection with specific products or compilations that
contain the covered work, unless you entered into that arrangement,
or that patent license was granted, prior to 28 March 2007.

  Nothing in this License shall be construed as excluding or limiting
any implied license or other defenses to infringement that may
otherwise be available to you under applicable patent law.

  12. No Surrender of Others' Freedom.

  If conditions are imposed on you (whether by court order, agreement or
otherwise) that contradict the conditions of this License, they do not
excuse you from the conditions of this License.  If you cannot convey a
covered work so as to satisfy simultaneously your obligations under this
License and any other pertinent obligations, then as a consequence you may
not convey it at all.  For example, if you agree to terms that obligate you
to collect a royalty for further conveying from those to whom you convey
the Program, the only way you could satisfy both those terms and this
License would be to refrain entirely from conveying the Program.

  13. Use with the GNU Affero General Public License.

  Notwithstanding any other provision of this License, you have
permission to link or combine any covered work with a work licensed
under version 3 of the GNU Affero General Public License into a single
combined work, and to convey the resulting work.  The terms of this
License will continue to apply to the part which is the covered work,
but the special requirements of the GNU Affero General Public License,
section 13, concerning interaction through a network will apply to the
combination as such.

  14. Revised Versions of this License.

  The Free Software Foundation may publish revised and/or new versions of
the GNU General Public License from time to time.  Such new versions will
be similar in spirit to the present version, but may differ in detail to
address new problems or concerns.

  Each version is given a distinguishing version number.  If the
Program specifies that a certain numbered version of the GNU General
Public License "or any later version" applies to it, you have the
option of following the terms and conditions either of that numbered
version or of any later version published by the Free Software
Foundation.  If the Program does not specify a version number of the
GNU General Public License, you may choose any version ever published
by the Free Software Foundation.

  If the Program specifies that a proxy can decide which future
versions of the GNU General Public License can be used, that proxy's
public statement of acceptance of a version permanently authorizes you
to choose that version for the Program.

  Later license versions may give you additional or different
permissions.  However, no additional obligations are imposed on any
author or copyright holder as a result of your choosing to follow a
later version.

  15. Disclaimer of Warranty.

  THERE IS NO WARRANTY FOR THE PROGRAM, TO THE EXTENT PERMITTED BY
APPLICABLE LAW.  EXCEPT WHEN OTHERWISE STATED IN WRITING THE COPYRIGHT
HOLDERS AND/OR OTHER PARTIES PROVIDE THE PROGRAM "AS IS" WITHOUT WARRANTY
OF ANY KIND, EITHER EXPRESSED OR IMPLIED, INCLUDING, BUT NOT LIMITED TO,
THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR
PURPOSE.  THE ENTIRE RISK AS TO THE QUALITY AND PERFORMANCE OF THE PROGRAM
IS WITH YOU.  SHOULD THE PROGRAM PROVE DEFECTIVE, YOU ASSUME THE COST OF
ALL NECESSARY SERVICING, REPAIR OR CORRECTION.

  16. Limitation of Liability.

  IN NO EVENT UNLESS REQUIRED BY APPLICABLE LAW OR AGREED TO IN WRITING
WILL ANY COPYRIGHT HOLDER, OR ANY OTHER PARTY WHO MODIFIES AND/OR CONVEYS
THE PROGRAM AS PERMITTED ABOVE, BE LIABLE TO YOU FOR DAMAGES, INCLUDING ANY
GENERAL, SPECIAL, INCIDENTAL OR CONSEQUENTIAL DAMAGES ARISING OUT OF THE
USE OR INABILITY TO USE THE PROGRAM (INCLUDING BUT NOT LIMITED TO LOSS OF
DATA OR DATA BEING RENDERED INACCURATE OR LOSSES SUSTAINED BY YOU OR THIRD
PARTIES OR A FAILURE OF THE PROGRAM TO OPERATE WITH ANY OTHER PROGRAMS),
EVEN IF SUCH HOLDER OR OTHER PARTY HAS BEEN ADVISED OF THE POSSIBILITY OF
SUCH DAMAGES.

  17. Interpretation of Sections 15 and 16.

  If the disclaimer of warranty and limitation of liability provided
above cannot be given local legal effect according to their terms,
reviewing courts shall apply local law that most closely approximates
an absolute waiver of all civil liability in connection with the
Program, unless a warranty or assumption of liability accompanies a
copy of the Program in return for a fee.

                     END OF TERMS AND CONDITIONS

            How to Apply These Terms to Your New Programs

  If you develop a new program, and you want it to be of the greatest
possible use to the public, the best way to achieve this is to make it
free software which everyone can redistribute and change under these terms.

  To do so, attach the following notices to the program.  It is safest
to attach them to the start of each source file to most effectively
state the exclusion of warranty; and each file should have at least
the "copyright" line and a pointer to where the full notice is found.

    <one line to give the program's name and a brief idea of what it does.>
    Copyright (C) <year>  <name of author>

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.

Also add information on how to contact you by electronic and paper mail.

  If the program does terminal interaction, make it output a short
notice like this when it starts in an interactive mode:

    <program>  Copyright (C) <year>  <name of author>
    This program comes with ABSOLUTELY NO WARRANTY; for details type `show w'.
    This is free software, and you are welcome to redistribute it
    under certain conditions; type `show c' for details.

The hypothetical commands `show w' and `show c' should show the appropriate
parts of the General Public License.  Of course, your program's commands
might be different; for a GUI interface, you would use an "about box".

  You should also get your employer (if you work as a programmer) or school,
if any, to sign a "copyright disclaimer" for the program, if necessary.
For more information on this, and how to apply and follow the GNU GPL, see
<http://www.gnu.org/licenses/>.

  The GNU General Public License does not permit incorporating your program
into proprietary programs.  If your program is a subroutine library, you
may consider it more useful to permit linking proprietary applications with
the library.  If this is what you want to do, use the GNU Lesser General
Public License instead of this License.  But first, please read
<http://www.gnu.org/philosophy/why-not-lgpl.html>.
EOF

echo -e '\nwhere do you want to create the executable links?[/usr/local/bin]'
read linkdir
if [[ -z $linkdir ]]; then
	linkdir='/usr/local/bin/'
fi

if [[ -d $linkdir ]]; then
	cd $linkdir
else
	echo "$linkdir not exists!!!"
	echo "Do you want to create $linkdir?[Yes/no]"
	read link
	if [[ -z $link ]]; then
		link='Y'
	fi
	if [ $link = 'Yes' -o $link = 'Y' -o $link = 'y' -o $link = 'yes' ]; then
		mkdir $linkdir
		cd $linkdir
	else
		fatal
	fi
fi

cat <<END> $instdir/minosse_uninst.sh
#!/bin/bash

#--------------------------------------------------------------------------------
#This file is part of Minosse.
#
#Minosse is free software: you can redistribute it and/or modify
#it under the terms of the GNU General Public License as published by
#the Free Software Foundation, either version 3 of the License, or
#(at your option) any later version.
#
#Minosse is distributed in the hope that it will be useful,
#but WITHOUT ANY WARRANTY; without even the implied warranty of
#MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#GNU General Public License for more details.
#
#You should have received a copy of the GNU General Public License
#along with Minosse.  If not, see <http://www.gnu.org/licenses/>.
#
#Minosse version 1.0.0, 6th May 2022
#---------------------------------------------------------------------------------

if [[ \$USER != 'root' ]]; then
        echo -e '\nPermission denied, you are not superuser\n'
        exit
fi


echo -e '\nDo you want really uninstall Minosse que system?[yes/No]'
echo 'All calculations submitted using Minosse will be stopped immediately'
read var

if [ \$var = 'Yes' -o \$var = 'Y' -o \$var = 'y' -o \$var = 'yes' ] ; then
        link=$linkdir
	run=\$(ps -eo args | grep Minosse.py | grep python | awk '{print(\$2)}')
	if [[ -n \$run ]]; then
		minosse stop
	fi
	rm -fr $instdir
	rm \$link/msub \$link/mdel \$link/mstat \$link/minosse \$link/minosse_uninst
	echo -e '\nMinosse uninstalled\n'
else
	exit
fi
END

chmod u+x $instdir/minosse
chmod u+x $instdir/Minosse.py
chmod u+x $instdir/minosse_uninst.sh
chmod a+x $instdir/Msub.py
chmod a+x $instdir/Mdel.py
chmod a+x $instdir/Mstat.py

ln -fs $instdir/minosse minosse
ln -fs $instdir/Msub.py msub
ln -fs $instdir/Mdel.py mdel
ln -fs $instdir/Mstat.py mstat
ln -fs $instdir/minosse_uninst.sh minosse_uninst

chmod a+wr $instdir
chmod a+wr $instdir/delete.mns
chmod a+r  $instdir/charge.mns

echo ''
echo 'INSTALLATION COMPLETE!!!'
echo '---------------------------------------------------------'
echo ''

echo 'Do you want to start the Minosse demon?[Yes/no]'
read start

if [[ -z $start ]]; then
        start='Y'
fi

if [ $start = 'Yes' -o $start = 'Y' -o $start = 'y' -o $start = 'yes' ]; then
	$instdir/minosse start
else
	echo 'Please, start manually the Minosse demon'
fi

exit
