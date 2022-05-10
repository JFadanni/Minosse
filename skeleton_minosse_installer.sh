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
if [ -n $run ]; then
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
#Mheader.py.sh file
END

cat Mheader.py > Minosse.py
cat <<"END">> Minosse.py
#  Minosse.py.sh .shfile
END

cat Mheader.py > Mutil.py
cat <<"END">> Mutil.py
#Mutil.py.sh file
END 

cat Mheader.py > Msub.py
cat <<"END">> Msub.py
#Msub.py.sh file
END

cat Mheader.py > Mstat.py
cat <<"END">> Mstat.py
#Mstat.py.sh
END

cat Mheader.py > Mdel.py
cat <<"END">> Mdel.py
#Mdel.py.sh
END

#rm Mheader.py

cat <<END> minosse
#minosse
END

cat <<"END"> README
#README
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
#COPYING
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
#minosse_uninst.sh
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
