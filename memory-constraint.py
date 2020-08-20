#!/usr/bin/env python3

import shutil
import os
import subprocess
import xml.etree.ElementTree as ET
import time


location = '/dev/shm/osc'

done = [
  'beignet',
  'blender',
  'carla',
  'ccls',
  'coq',
  'embree',
  'gnuradio',
  'hugin',
  'insighttoolkit',
  'kokkos',
  'libqt5-qtwebkit',
  'libreoffice',
  'MozillaThunderbird',
  'mozjs60',
  'mozjs68',
  'nlohmann_json',
  'octave',
  'opencv',
  'openscad',
  'PrusaSlicer',
  'python-torch',
  'qgis',
  'rstudio',
  'telegram-desktop',
  'tensorflow2',
  'tensorflow',
  'trilinos',
  'votca-csg',
  'votca-xtp',
  'vulkan-validationlayers'
]

packages = [
  'libqt5-qtwebengine',
]

TEMPLATE = '''
<constraints>
  <hardware>
    <memoryperjob>
      <size unit="M">%s</size>
    </memoryperjob>
  </hardware>
</constraints>
'''.strip()

for package in packages:
    print('=== %s ===' % package)
    shutil.rmtree(location, ignore_errors=True)
    os.mkdir(location)
    os.chdir(location)
    subprocess.run('osc rdelete home:marxin:memory-constraint/%s -m byebye' % package, shell=True, stderr=subprocess.DEVNULL)
    subprocess.check_output('osc branch openSUSE:Factory/%s home:marxin:memory-constraint' % package, shell=True)
    subprocess.check_output('osc co home:marxin:memory-constraint/%s' % package, shell=True)
    os.chdir('home:marxin:memory-constraint/' + package)
    spec = package + '.spec'
    lines = open(spec).read().split('\n')
    limit = [l for l in lines if l.startswith('%limit_build')]
    assert len(limit) == 1
    limit = limit[0]
    limit = limit.split('-m')[-1].strip()
    if limit == '%limit_build':
        limit = '1000'

    lines = [l for l in lines if not l.startswith('BuildRequires:  memory-constraints') and not l.startswith('%limit_build')]
    with open(spec, 'w') as f:
        f.write('\n'.join(lines))
    if os.path.exists('_constraints'):
        tree = ET.parse('_constraints')
        root = tree.getroot()
        hw = root.find('hardware')
        n = ET.Element('memoryperjob')
        s = ET.Element('size')
        s.set('unit', 'M')
        s.text = limit
        n.append(s)
        hw.append(n)
        tree.write('_constraints')
        subprocess.check_output('tidy -m -xml -i _constraints', shell=True, stderr=subprocess.DEVNULL)
    else:
        with open('_constraints', 'w') as f:
            f.write(TEMPLATE % limit)
        subprocess.check_output('osc add _constraints', shell=True)

    lines = open('_constraints').read().split('\n')
    start = '<?xml version="1.0" encoding="UTF-8"?>'
    if lines[0] != start:
        lines.insert(0, start)
    with open('_constraints', 'w') as f:
        f.write('\n'.join(lines))

    msg = 'Use memoryperjob constraint instead of %limit_build macro.'
    subprocess.check_output('osc vc -m "%s"' % msg, shell=True)
    print(subprocess.check_output('osc diff | colordiff', shell=True, encoding='utf8'))
    subprocess.check_output('osc commit -m "%s"' % msg, shell=True)
    time.sleep(20)
    subprocess.check_output('osc sr -m "%s"' % msg, shell=True)
