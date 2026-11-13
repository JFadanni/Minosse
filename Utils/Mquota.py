#! /usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import pwd
import sys
from   argparse   import ArgumentParser

from    Mutil      import *
from    Mutil      import __version__

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

##------------------------------------------------------------------------------
## Files names
##------------------------------------------------------------------------------

Mdir="$instdir/"
file1=Mdir+'nodes'
file9=Mdir+'quotas'

##------------------------------------------------------------------------------
## Flags
##------------------------------------------------------------------------------

parser = ArgumentParser(prog="minosse quota",
                        description="Set the cpu and RAM quotas of the users "
                                    "(root only). Without options, list the "
                                    "users of the machine and ask for the "
                                    "quota of each.")

parser.add_argument("--version", action="version",
                    version=f"%(prog)s {__version__}")
source = parser.add_mutually_exclusive_group()
source.add_argument("-f", "--file",
                    action="store", dest="file", default=None,
                    help="read the quotas from a JSON file, written as "
                         "quotas.mns")
source.add_argument("-s", "--split",
                    action="store_true", dest="split", default=False,
                    help="split the cpus equally among the users of the "
                         "machine, and the RAM with them")
source.add_argument("--clear",
                    action="store_true", dest="clear", default=False,
                    help="remove all the quotas: nobody is limited")
source.add_argument("--show",
                    action="store_true", dest="show", default=False,
                    help="show the quotas and exit")
parser.add_argument("-y", "--yes",
                    action="store_true", dest="yes", default=False,
                    help="write the quotas without asking for confirmation")

options = parser.parse_args()

##------------------------------------------------------------------------------
## Functions
##------------------------------------------------------------------------------

def abort(why):
    sys.exit(f"minosse quota: {why}: no quotas written")

def knownuser(user):
    try:
        pwd.getpwnam(user)
    except KeyError:
        return False
    return True

def yes(question):
    """Ask a question, yes by default"""
    try:
        answer = input(f"{question} [Yes/no] ").strip()
    except EOFError:
        abort("no answer")
    return answer in ('','Yes','Y','y','yes')

def ask(question,default,least):
    """Ask for an integer of at least least, default on an empty answer"""
    while True:
        try:
            answer = input(f"{question} [{default}]: ").strip()
        except EOFError:
            abort("no answer")
        if not answer:
            return default
        try:
            value = int(answer)
        except ValueError:
            print('   a whole number, please')
            continue
        if value < least:
            print(f"   at least {least}, please")
        else:
            return value

def showquotas(quotas):
    if not quotas:
        print('  No quotas: the jobs of every user can use all the node')
        return
    print('%15s' % 'user','%6s' % 'Ncpu','%10s' % 'RAM(MB)')
    print('-'*60)
    for user, quota in quotas.items():
        print('%15s' % user,'%6s' % quota['Ncpu'],'%10s' % quota['RAM'])
    other = smallestquota(quotas)
    print('%15s' % 'other users','%6s' % other['Ncpu'],'%10s' % other['RAM'])

##------------------------------------------------------------------------------
## Main program
##------------------------------------------------------------------------------

node = readallfile(file1)
least = minimumquota(node)
try:
    current = readquotas(file9,node)
except (OSError, ValueError) as error:
    print(f"The quotas in use are malformed, and ignored here: {error}")
    current = {}

if options.show:
    showquotas(current)
    sys.exit(0)

# only root, who runs the demon, can write in the installation directory
if not os.access(Mdir,os.W_OK):
    sys.exit("minosse quota: only root can set the quotas")

# the users of the machine, and those given a quota earlier: users from a
# network directory may be found only by name
users = sorted(set(machineusers()) | {user for user in current if knownuser(user)})

if options.clear:
    quotas = {}
elif options.file:
    try:
        with open(options.file,encoding='utf-8') as filein:
            quotas = parsequotas(filein.read(),node)
    except (OSError, ValueError) as error:
        abort(f"{options.file}: {error}")
    for user in quotas:
        if not knownuser(user):
            print(f"Warning: {user} is not a user of this machine")
elif options.split:
    if not users:
        abort("no users found")
    quotas = splitquotas(users,node)
else:
    print(f"The node has {node['Ncpu']} cpus and {node['RAM']} MB of RAM; "
          f"a quota is at least {least['Ncpu']} cpu and {least['RAM']} MB.")
    print("The users left out have the smallest quota given here.\n")
    if not users:
        abort("no users found: give the quotas with --file")
    print('Users of the machine:', ' '.join(users))
    split = splitquotas(users,node)
    if yes(f"Split the node equally among them "
           f"({formatquota(split[users[0]])} each)?"):
        quotas = split
    else:
        print("Give the quota of each user; Enter keeps the value in brackets.")
        quotas = {}
        for user in users:
            proposal = current.get(user,split[user])
            cpus = ask(f"{user:>15}  cpus",proposal['Ncpu'],least['Ncpu'])
            # the RAM follows the cpus, unless they are left as they were
            ram = proposal['RAM'] if cpus == proposal['Ncpu'] else shareram(cpus,len(users),node)
            quotas[user] = {'Ncpu': cpus, 'RAM': ask(f"{user:>15}  RAM (MB)",ram,least['RAM'])}

print()
showquotas(quotas)
if not options.yes and not yes("Write these quotas?"):
    abort("cancelled")
writeallfile(file9,quotas)
print("Quotas written: Minosse applies them at once, also to the queued jobs")
