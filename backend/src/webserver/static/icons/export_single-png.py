import os
import subprocess


cols = ['#000000','#ffffff','#f79a1f']
file = 'knxcontrol_home.svg'

print file

for col in cols:
    f1 = open(file, 'r')
    f2 = open(file[0:-4]+'_tmp.svg', 'w')

    for line in f1:
        f2.write(line.replace('#000000', col))
    f2.close()
    f1.close()

    # export
    subprocess.call('inkscape '+file[0:-4]+'_tmp.svg --export-width=200 --export-png=../../www/icons/'+col[1:]+'/'+file[0:-4]+'.png')

    # remove tmp file
    os.remove(file[0:-4]+'_tmp.svg')

f1.close()
