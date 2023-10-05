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
#Minosse version 1.1.0, 5th Oct 2023
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
