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
