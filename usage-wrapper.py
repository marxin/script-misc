#!/usr/bin/env python3

import argparse
import math
import subprocess
import threading
import time

import matplotlib.pyplot as plt

import psutil


INTERVAL = 0.33
LW = 0.7

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

special_processes = {'ld': 'gold', 'WPA': 'deepskyblue',
                     'ltrans': 'forestgreen'}

descr = 'Run command and measure memory and CPU utilization'
parser = argparse.ArgumentParser(description=descr)
parser.add_argument('command', metavar='command', help='Command')
parser.add_argument('-v', '--verbose', action='store_true', help='Verbose')
parser.add_argument('-s', '--separate-ltrans', action='store_true',
                    help='Separate LTRANS processes in graph')
parser.add_argument('-o', '--output', default='usage.svg',
                    help='Path to output image (default: usage.svg)')
parser.add_argument('-r', '--range',
                    help='Plot only the selected time range (e.g. 200-300)')
parser.add_argument('-t', '--title', help='Graph title')
args = parser.parse_args()
time_range = [int(x) for x in args.range.split('-')] if args.range else None


def to_gigabyte(value):
    return value / 1024**3


def get_process_name(proc):
    name = proc.name()
    cmdline = proc.cmdline()
    if name == 'ld' or name == 'ld.gold' and '-plugin' in cmdline:
        return 'ld'
    elif name == 'lto1-wpa':
        return 'WPA'
    elif '-fltrans' in cmdline:
        if args.separate_ltrans:
            return 'ltrans-%d' % proc.pid
        else:
            return 'ltrans'
    return None


def record():
    while not done:
        timestamp = time.monotonic() - start_ts
        if time_range:
            if timestamp < time_range[0] or timestamp > time_range[1]:
                time.sleep(INTERVAL)
                continue
        used_cpu = psutil.cpu_percent(interval=INTERVAL)
        used_memory = to_gigabyte(psutil.virtual_memory().used)
        timestamps.append(timestamp)
        memory_data.append(used_memory)
        cpu_data.append(used_cpu)

        entry = {}
        for proc in psutil.Process().children(recursive=True):
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
    fig, (cpu_subplot, mem_subplot) = plt.subplots(2, sharex=True)
    if args.title:
        fig.suptitle(args.title, fontsize=17)
    fig.set_figheight(5)
    fig.set_figwidth(10)
    cpu_subplot.set_title('CPU usage (red=single core)')
    cpu_subplot.set_ylabel('%')
    cpu_subplot.plot(timestamps, cpu_data, c='blue', lw=LW)
    cpu_subplot.set_ylim([0, 105])
    cpu_subplot.axhline(color='r', alpha=0.5, y=100.0 / cpu_count, lw=LW)
    cpu_subplot.set_xlim(left=time_range[0] if time_range else 0)
    cpu_subplot.grid(True)

    mem_subplot.plot(timestamps, memory_data, c='blue', lw=LW)
    mem_subplot.set_title('Memory usage')
    mem_subplot.set_ylabel('GB')
    mem_subplot.set_xlabel('time')

    # scale it to a reasonable limit
    limit = math.ceil(peak_memory * 1.2)
    mem_subplot.set_ylim([0, limit])
    mem_subplot.set_yticks(range(0, limit + 1, math.ceil((limit + 1) / 10)))
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

    if stacks:
        mem_subplot.stackplot(timestamps, stacks, labels=process_labels,
                              colors=colors)
        mem_subplot.legend(loc='upper left')
    plt.savefig(args.output)
    if args.verbose:
        print('Saving plot to %s' % args.output)


thread = threading.Thread(target=record, args=())
thread.start()

if args.verbose:
    print('Running command', flush=True)

try:
    subprocess.run(args.command, shell=True)
except KeyboardInterrupt:
    pass
finally:
    done = True
    thread.join()
    if memory_data:
        min_memory = min(memory_data)
        memory_data = [x - min_memory for x in memory_data]
        generate_graph(max(memory_data))
    elif args.verbose:
        print('No collected data')
