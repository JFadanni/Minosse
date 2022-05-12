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
architecture= os.uname()[-1]
id=str(random.randint(1, 1000000))

subjob=[varnames,
        [socket.gethostname(),options.cpus,options.memory,'eide',options.HD,architecture,'que',
         options.priority,'','',options.file ,getpass.getuser(),id,options.chain,time.strftime("%m/%d/%y %H.%M.%S", time.localtime()),'']]

writeallfile(Mdir+file5+id,subjob)
