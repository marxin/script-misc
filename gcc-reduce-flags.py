#!/usr/bin/env python3

import subprocess
import sys

assert len(sys.argv) >= 2

patterns = ['nternal compiler error', 'Segmentation fault', 'runtime error:',
            'ERROR: AddressSanitizer', 'fcompare-debug']


if len(sys.argv) == 3:
    pattern = sys.argv[2]


def does_ice(command):
    r = subprocess.run(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stderr = r.stderr.decode('utf-8')
    if r.returncode == 124:
        return True
    for p in patterns:
        if p in stderr:
            return True
    return False


def do_cmd(base, flags):
    return 'timeout 10 %s %s' % (' '.join(base), ' '.join(flags))


def strip_timeout(command):
    tokens = command.split(' ')
    while len(tokens) > 0 and tokens[0] == 'timeout':
        tokens = tokens[2:]

    return ' '.join(tokens)


command_line = [x.replace('#', '--param ') for x in sys.argv[1].replace('--param ', '#').split(' ') if x != '']

base = [x for x in command_line if not x.startswith('-')]
flags = {x for x in command_line if x not in base}


def reduce(base, flags):
    while True:
        change = False
        for f in list(flags):
            flags.remove(f)
            if does_ice(do_cmd(base, flags)):
                change = True
                break
            else:
                flags.add(f)

        if not change:
            cmd = do_cmd(base, flags)
            stripped = strip_timeout(cmd)
            return stripped if does_ice(stripped) else cmd


print(reduce(base, flags))
