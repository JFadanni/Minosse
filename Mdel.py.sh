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
