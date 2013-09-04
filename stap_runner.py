#!/usr/bin/env python

import os
import sys
import tempfile
import commands
import operator

stap_config = 'stap_readpage_ptr.stp'
graph_command = 'readpage_graph.py'
devs = ['/dev/sda2', '/dev/sdb1']
original_devs = []

def die(message):
  print('Error:' + message)
  exit(-1)

def restore_blockdev():
 for i, dev in enumerate(devs):
  r = commands.getstatusoutput('blockdev --setra ' + str(original_devs[i]) + ' ' + dev)
  if r[0] != 0:
    die('blockdev command failed')

if len(sys.argv) <= 1:
  print('step_runner [binary] <pdf>')
  exit(-1)

binary_file = sys.argv[1]
temp_prefix = os.path.basename(binary_file) + '-'

### setup phase ###

for dev in devs:
  r = commands.getstatusoutput('blockdev --getra ' + dev)
  if r[0] != 0:
    die('blockdev command failed')

  original_devs.append(int(r[1]))

  print('Setting zero readahead for device: ' + dev)
  r = commands.getstatusoutput('blockdev --setra 0 ' + dev)
  if r[0] != 0:
    die('blockdev command failed')

print(original_devs)

print('Invalidating kernel FS caches')
r = commands.getstatusoutput('echo 3 > /proc/sys/vm/drop_caches')

if r[0] != 0:
  die('could not invalidate kernel FS caches')

print('Starting stap command')
r = commands.getstatusoutput('stap ' + stap_config + ' -c ' + binary_file)

restore_blockdev()

if r[0] != 0:
  print(r[1])
  die('stap execution for ' + binary_file + ' failed')  

print('Stap command finished')

### stap data parsing ###

lines = r[1].split('\n')
first_line_tokens = lines[0].strip().split(' ')

start_time = int(first_line_tokens[0])
main_binary = first_line_tokens[1]
offset = int(first_line_tokens[2])

### histogram of touched pages for binaries that are wrapped ###
histogram = {}

for l in lines:
  f = l.split(' ')[1]

  if f in histogram:
    histogram[f] += 1
  else:
    histogram[f] = 1

sorted_histogram = sorted(histogram.iteritems(), key=operator.itemgetter(1), reverse = True)

# main_binary = sorted_histogram[0][0]

print(main_binary)

if offset != 0:
  die('offset of main library is non-zero: ' + str(offset))

stats = [x for x in lines if x.strip().split(' ')[1] == main_binary]

print('Disk pages read: %u' % len(stats))

### writing results to file ###
temp = tempfile.mkstemp(prefix = temp_prefix)

for s in stats:
  os.write(temp[0], str(s) + '\n')

os.close(temp[0])
os.chmod(temp[1], 0777)

print('Temp file with stap created: ' + temp[1])
print('Calling graph creation command')

### graph creation ###
pdf_file = None
pdf_file_set = False

if len(sys.argv) >= 3:
  if sys.argv[2].endswith('.pdf'):
    pdf_file = sys.argv[2]
    pdf_file_set = True
  else:
    binary_file = sys.argv[2]

if pdf_file_set == False:
  t = tempfile.mkstemp(suffix = '.pdf', prefix = temp_prefix)
  os.close(t[0])
  os.chmod(t[1], 0777)
  pdf_file = t[1]

command = 'python ' + graph_command + ' ' + temp[1] + ' ' + binary_file + ' ' + pdf_file
print('graph command execution: ' + command)

r = commands.getstatusoutput(command)

if r[0] != 0:
  die('graph creation command failed')

print('PDF graph has been created to file: ' + pdf_file)
print('Openning evince')

os.system('evince ' + pdf_file + ' &')
