
# **Minosse** version 1.3.0, 12th Nov 2023

Minosse is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

Minosse is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
[GNU General Public License](https://www.gnu.org/licenses/gpl-3.0.html) for more details.

You should have received a copy of the GNU General Public License
along with Minosse.  If not, see <http://www.gnu.org/licenses/>.
In this file, you can find almost everything you need to install and run Minosse batch system (it is a tiny program!).

This file is generated during the installation step or can be downloaded from the git repository.

## How to install:
Minosse needs Python 3 installed on your machine. No special packages are needed.

To install Minosse two steps are needed:
1. Run the configuration script ```minosse_config.sh``` to set the working environment:  
$ ``` ./minosse_config.sh```

2. Run the installer script ```minosse_inst.sh``` as root to copy Minosse files in the installation directory:  
$ ```sudo ./minosse_inst.sh```

Here is an example of the nodes.mns:

```
!start   
NODE: none              (number of node, not yet used)  
hostname: dyn12         (name of the computer)  
Ncpu: 4	                (n° of cores)  
RAM: 161386             (amount of ram memory MB)  
HDtype: eide	        (HD type)  
HDmemory: 1846          (dimension of the working partition GB)  
architecture: x86_64    (architecture type)  
status: up              (status of the node, not yet used)  
priority: 50            (priority of the node, not yet used)  
!end
```

You can change each one of these values and then start Minosse.  
 > ***ATTENTION*** *do not specify values bigger than the physical values of the machine.*

If you find problems installing or running this program please use the [Issues section on GitHub](https://github.com/JFadanni/Minosse/issues), I will be happy to find a solution to your problem.

This release of Minosse works only for single workstation/server with N° SHM processors.
There are no limits to the number of processors, RAM, or disk space that are supported by Minosse.

Minosse administrates your jobs through a simple scheme looking at the free 
resources of your system, so no real queues are created.
For example, if you have 4 CPUs but only 2 GB of RAM, two jobs requiring 1.5 GB RAM (each one) cannot run at the same time, and Minosse queue up one of these two.


## How to use:
During the installation, the script asks you in which directory you want to create the links. If this directory is not in your $PATH 
(like: /usr/local/bin or /urs/bin/) you cannot use the minosse commands by simply typing the name of the command, but you need to specify the entire path.
- Start/stop the demon (only root can do it):
 
   ```minosse start/stop```

- Uninstall (only root can do it):

  ```minosse_uninst```

The flag `-h` gives you the usage for all the next commands.

- Checking the queue status:

   ```mstat or mstat -v (verbose)```

- Submit a job:

   ```msub -f "path/scriptname" -c "n° of CPU" -m "RAM"```

- delete a job:

   ```mdel -j "job id" or -s "path/scriptname"```

***
# Gaussian submitting script
Here is an example of a Gaussian (Gaussian16) submitting script using Minosse:
```sh
#!/bin/bash

# to be sure is used correctly 
if [ -z $3 ]; then
   echo - '\nUsage: mg16 inputfile ncpu memory'
   echo -e '\n  Submit a Gaussian job to the Minosse queue system'
   exit
fi

# check if you are using .com extension or not
if [ $1 == ${1%.*}.com ]; then
job=${1%.*}
else
job=$1
fi

echo -e "\nSubmitting Gaussian batch job $job to Minosse queue system\n"

# define where we are
PTH=$PWD

# from here to 'END3' is defined the script which minosse executes
        cat <<END3> $job.nqs
        #!/bin/bash

        # check if the checkpoint exists
        if [ -f $PTH/$job.chk ]; then
                cp $PTH/$job.chk /scratch/$USER/
        fi

        # check if the checkpoint is compressed
        if [ -f $PTH/$job.chk.gz ]; then
                cp $PTH/$job.chk.gz /scratch/$USER/
                gzip -fd /scratch/$USER/$job.chk.gz
        fi

        # move to the working directory
        cd /scratch/$USER/

        # create the header of the Gaussian input file
        cat <<END2 > $job.com_nqs
        %chk=/scratch/$USER/$job
        %int=/scratch/$USER/$job
        %d2e=/scratch/$USER/$job
        %rwf=/scratch/$USER/$job
        %mem=$3MB
        %nproc=$2
        END2

        cat $PTH/$job.com >> $job.com_nqs
# just to be sure put an empty line at the end of the input
echo ' ' >> $job.com_nqs

# run gaussian
g16 < $job.com_nqs > $PTH/$job.log 2>&1

## compress the checkpoint 
if [ -f $job.chk ]; then
        gzip -f $job.chk
fi

# remove some useless files 
rm Gau-*.scr
rm $job.com_nqs  
rm $job.d2e $job.int $job.rwf  
mv $job.chk.gz $PTH/`  
END3

# make executable the script
`chmod a+x $job.nqs`

# submit on Minosse
`msub -f $PTH/$job.nqs -c $2 -m $3`
```
