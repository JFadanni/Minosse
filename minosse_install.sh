#!/bin/bash
## installation script
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
 
 Minosse version 1.1.0
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

if [[ -d Tmp ]]; then
	if [[ -z $(ls -A Tmp) ]]; then
		echo " directory Tmp is empty"
		echo " run minosse_config.sh and try again"
		fatal
	fi
else
		echo "directory Tmp does not exist"
		echo " run minosse_config.sh and try again"
		fatal
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

cp COPYING $instdir
cp README.md $instdir

mv Tmp/conf.mns $instdir
mv Tmp/charge.mns $instdir
mv Tmp/delete.mns $instdir
mv Tmp/defaults.mns $instdir
mv Tmp/nodes.mns $instdir
mv Tmp/status.mns $instdir

rm -r Tmp

sed -e "s|\$instdir|$instdir|g" Utils/Minosse.py > $instdir/Minosse.py
sed -e "s|\$instdir|$instdir|g" Utils/Mstat.py > $instdir/Mstat.py
sed -e "s|\$instdir|$instdir|g" Utils/Msub.py > $instdir/Msub.py
sed -e "s|\$instdir|$instdir|g" Utils/Mdel.py > $instdir/Mdel.py
sed -e "s|\$instdir|$instdir|g" Utils/Mutil.py > $instdir/Mutil.py
sed -e "s|\$instdir|$instdir|g" minosse > $instdir/minosse
sed -e "s|\$instdir|$instdir|g" minosse_uninst.sh > $instdir/minosse_uninst.sh

chmod u+x $instdir/minosse
chmod u+x $instdir/Minosse.py
chmod u+x $instdir/minosse_uninst.sh
chmod a+x $instdir/Msub.py
chmod a+x $instdir/Mdel.py
chmod a+x $instdir/Mstat.py

cd $instdir
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
