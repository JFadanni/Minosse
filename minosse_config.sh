#!/bin/bash
## configuration script
# 
 echo '
 Copyright 2022,2024 Jacopo Fadanni
 
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
 
 Minosse version 1.3.0
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

echo -e '\ninsert the node priority'
read prior

if [[ -z $prior ]]; then
	prior='50'
fi
check $prior

echo -e '\nDo you agree with the following configuration?'
echo -e "hostname	$HOSTNAME		"
echo -e "partition	$workdir		"
echo -e "Ncpus		$cpus			"
echo -e "RAM(MB)\t	$totmem			"
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


if [[ -d Tmp ]]; then
  echo -e '\n directory Tmp exists'
  rm Tmp/*
else
  mkdir Tmp/
fi

cd Tmp

echo -e '\nwrite Minosse files:'
echo 'charge.mns'
cat <<END> charge.mns
{

}
END

echo 'conf.mns'
cat <<END> conf.mns
{
  "status": "down"
}
END

echo 'delete.mns'
cat <<END> delete.mns
{

}
END

echo 'node.mns'
cat <<END> nodes.mns
{
  "NODE": "none",
  "hostname": "$HOSTNAME",
  "Ncpu": $cpus ,
  "RAM": $totmem,
  "HDmemory": $partition,
  "architecture": "$HOSTTYPE",
  "status": "up",
  "priority": $prior
}
END

echo 'defaults.mns'
cat <<END> defaults.mns
{
  "hostname": "$HOSTNAME",
  "Ncpu": 1,
  "RAM": $totmem,
  "HDmemory": 0,
  "architecture": "$HOSTTYPE",
  "status": "que",
  "priority": $prior
}
END

echo 'status.mns'
cat <<END> status.mns
{
  "NODE": "none",
  "hostname": "$HOSTNAME",
  "Ncpu": 0,
  "RAM": 0,
  "HDmemory": 0,
  "architecture": "$HOSTTYPE",
  "status": "up",
  "priority": $prior
}
END

cd ..
