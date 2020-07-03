#!/usr/bin/env python3

import argparse
import math
import subprocess
import threading
import time

import matplotlib.pyplot as plt

import psutil


INTERVAL = 0.33

timestamps = []
cpu_data = []
memory_data = []
memory_subdata = []
process_mapping = {}
process_labels = []
lock = threading.Lock()

done = False
start_ts = time.monotonic()
cpu_count = psutil.cpu_count()

special_processes = {'ld': 'gold', 'WPA': 'deepskyblue'}


def to_gigabyte(value):
    return value / 1024**3


def get_process_name(proc):
    name = proc.name()
    cmdline = proc.cmdline()
    if (name == 'ld' or name == 'ld.gold'
            and len(cmdline) >= 2 and cmdline[1] == '-plugin'):
        return 'ld'
    elif name == 'lto1-wpa':
        return 'WPA'
    elif '-fltrans' in cmdline:
        return 'ltrans-%d' % proc.pid
    return None


def record():
    while not done:
        timestamp = time.monotonic() - start_ts
        used_cpu = psutil.cpu_percent(interval=INTERVAL)
        used_memory = to_gigabyte(psutil.virtual_memory().used)
        timestamps.append(timestamp)
        memory_data.append(used_memory)
        cpu_data.append(used_cpu)

        entry = {}
        attrs = ['name', 'cmdline', 'memory_info']
        for proc in psutil.process_iter(attrs=attrs):
            try:
                name = get_process_name(proc)
                if name:
                    memory = to_gigabyte(proc.memory_info().rss)
                    if name not in process_mapping:
                        length = len(process_mapping)
                        process_mapping[name] = length
                        if name in special_processes:
                            process_labels.append(name)
                        else:
                            process_labels.append(None)
                    if name not in entry:
                        entry[name] = 0
                    entry[name] += memory
            except Exception:
                # the process can be gone
                pass
        memory_subdata.append(entry)


def generate_graph(peak_memory):
    f, (cpu_subplot, mem_subplot) = plt.subplots(2, sharex=True)
    cpu_subplot.set_title('CPU usage (red=single core)')
    cpu_subplot.set_ylabel('%')
    cpu_subplot.plot(timestamps, cpu_data)
    cpu_subplot.set_ylim([0, 105])
    cpu_subplot.axhline(color='r', alpha=0.5, y=100.0 / cpu_count)
    cpu_subplot.grid(True)

    mem_subplot.plot(timestamps, memory_data, c='blue')
    mem_subplot.set_title('Memory usage')
    mem_subplot.set_ylabel('GB')

    # scale it to a reasonable limit
    limit = math.ceil(peak_memory * 1.2)
    mem_subplot.set_ylim([0, limit])
    mem_subplot.set_yticks(range(limit + 1))
    mem_subplot.grid(True)

    stacks = []
    for _ in range(len(process_mapping)):
        stacks.append([])
    for values in memory_subdata:
        for k, v in process_mapping.items():
            if k in values:
                stacks[v].append(values[k])
            else:
                stacks[v].append(0)

    colors = list(plt.cm.get_cmap('tab20c').colors * 100)
    for name, color in special_processes.items():
        if name in process_mapping:
            colors[process_mapping[name]] = color

    mem_subplot.stackplot(timestamps, stacks, labels=process_labels,
                          colors=colors)
    mem_subplot.legend(loc='upper left')

    plt.savefig('output.svg')


descr = 'Run command and measure memory and CPU utilization'
parser = argparse.ArgumentParser(description=descr)
parser.add_argument('command', metavar='command', help='Command')
parser.add_argument('-v', '--verbose', action='store_true', help='Verbose')
args = parser.parse_args()

thread = threading.Thread(target=record, args=())
thread.start()

if args.verbose:
    print('Running command', flush=True)
subprocess.run(args.command, shell=True)

done = True
thread.join()
min_memory = min(memory_data)
memory_data = [x - min_memory for x in memory_data]
generate_graph(max(memory_data))
