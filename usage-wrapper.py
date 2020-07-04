#!/usr/bin/env python3

import argparse
import math
import os
import subprocess
import threading
import time

import matplotlib.pyplot as plt

import psutil


INTERVAL = 0.33
LW = 0.7

global_timestamps = []
global_cpu_data = []
global_memory_data = []
global_process_usage = []

process_name_map = {}
process_labels = []
lock = threading.Lock()

done = False
start_ts = time.monotonic()
cpu_count = psutil.cpu_count()

special_processes = {'ld': 'gold', 'WPA': 'deepskyblue',
                     'WPA-stream-out': 'lightblue',
                     'ltrans': 'forestgreen', 'as': 'coral'}
for i, k in enumerate(special_processes.keys()):
    process_name_map[k] = i
    process_labels.append(k)


descr = 'Run command and measure memory and CPU utilization'
parser = argparse.ArgumentParser(description=descr)
parser.add_argument('command', metavar='command', help='Command')
parser.add_argument('-v', '--verbose', action='store_true', help='Verbose')
parser.add_argument('-s', '--separate-ltrans', action='store_true',
                    help='Separate LTRANS processes in graph')
parser.add_argument('-o', '--output', default='usage.svg',
                    help='Path to output image (default: usage.svg)')
parser.add_argument('-r', '--ranges',
                    help='Plot only the selected time ranges '
                    '(e.g. 20-30, 0-1000)')
parser.add_argument('-t', '--title', help='Graph title')
args = parser.parse_args()


def to_gigabyte(value):
    return value / 1024**3


def get_process_name(proc):
    name = proc.name()
    cmdline = proc.cmdline()
    if name == 'ld' or name == 'ld.gold':
        return 'ld'
    elif name == 'lto1-wpa':
        return 'WPA'
    elif name == 'lto1-wpa-stream':
        return 'WPA-stream-out'
    elif name == 'as':
        return 'as'
    elif '-fltrans' in cmdline:
        if args.separate_ltrans:
            return 'ltrans-%d' % proc.pid
        else:
            return 'ltrans'
    return None


def record():
    active_pids = {}
    while not done:
        timestamp = time.monotonic() - start_ts
        used_cpu = psutil.cpu_percent(interval=INTERVAL)
        used_memory = to_gigabyte(psutil.virtual_memory().used)
        global_timestamps.append(timestamp)
        global_memory_data.append(used_memory)
        global_cpu_data.append(used_cpu)

        entry = {}
        seen_pids = set()
        for proc in psutil.Process().children(recursive=True):
            try:
                name = get_process_name(proc)
                if name:
                    seen_pids.add(proc.pid)
                    if proc.pid not in active_pids:
                        active_pids[proc.pid] = proc
                    else:
                        proc = active_pids[proc.pid]
                    memory = to_gigabyte(proc.memory_info().rss)
                    cpu = proc.cpu_percent() / cpu_count
                    if name not in process_name_map:
                        length = len(process_name_map)
                        process_name_map[name] = length
                        if name in special_processes:
                            process_labels.append(name)
                        else:
                            process_labels.append(None)
                    if name not in entry:
                        entry[name] = {'memory': 0, 'cpu': 0}
                    entry[name]['cpu'] += cpu
                    entry[name]['memory'] += memory
            except Exception:
                # the process can be gone
                pass
        for pid in list(active_pids.keys()):
            if pid not in seen_pids:
                del active_pids[pid]
        if args.verbose:
            print(entry, flush=True)
        global_process_usage.append(entry)


def generate_graph(time_range):
    timestamps = []
    cpu_data = []
    memory_data = []
    process_usage = []
    peak_memory = max(global_memory_data)

    # filter date by timestamp
    for i, ts in enumerate(global_timestamps):
        if not time_range or time_range[0] <= ts and ts <= time_range[1]:
            timestamps.append(ts)
            cpu_data.append(global_cpu_data[i])
            memory_data.append(global_memory_data[i])
            process_usage.append(global_process_usage[i])

    if not timestamps:
        if args.verbose:
            print('No data for range: %s' % str(time_range))
        return

    fig, (cpu_subplot, mem_subplot) = plt.subplots(2, sharex=True)
    title = args.title if args.title else ''
    if time_range:
        title += ' (%d-%d s)' % (time_range[0], time_range[1])
    fig.suptitle(title, fontsize=17)
    fig.set_figheight(5)
    fig.set_figwidth(10)
    local_peak_memory = max(memory_data)
    local_cpu_average = sum(cpu_data) / len(cpu_data)
    cpu_subplot.set_title('CPU usage (red=single core, avg=%.1f%%)'
                          % local_cpu_average)
    cpu_subplot.set_ylabel('%')
    cpu_subplot.plot(timestamps, cpu_data, c='blue', lw=LW)
    cpu_subplot.set_ylim([0, 105])
    cpu_subplot.axhline(color='r', alpha=0.5, y=100.0 / cpu_count, lw=LW)
    cpu_subplot.set_xlim(left=time_range[0] if time_range else 0)
    cpu_subplot.grid(True)

    mem_subplot.plot(timestamps, memory_data, c='blue', lw=LW)
    mem_subplot.set_title('Memory usage (peak: %.1f GB)' % local_peak_memory)
    mem_subplot.set_ylabel('GB')
    mem_subplot.set_xlabel('time')

    # scale it to a reasonable limit
    limit = 1
    while 1.2 * peak_memory > limit:
        limit *= 2
    mem_subplot.set_ylim([0, limit + 1])
    mem_subplot.set_yticks(range(0, limit + 1, math.ceil(limit / 8)))
    mem_subplot.grid(True)

    # TODO: move to a function
    cpu_stacks = []
    mem_stacks = []
    for _ in range(len(process_name_map)):
        cpu_stacks.append([])
        mem_stacks.append([])
    for values in process_usage:
        for k, v in process_name_map.items():
            if k in values:
                cpu_stacks[v].append(values[k]['cpu'])
                mem_stacks[v].append(values[k]['memory'])
            else:
                cpu_stacks[v].append(0)
                mem_stacks[v].append(0)

    colors = list(plt.cm.get_cmap('tab20c').colors * 100)
    for name, color in special_processes.items():
        if name in process_name_map:
            colors[process_name_map[name]] = color

    if mem_stacks:
        mem_subplot.stackplot(timestamps, mem_stacks, labels=process_labels,
                              colors=colors)
        mem_subplot.legend(loc='best')
        cpu_subplot.stackplot(timestamps, cpu_stacks, labels=process_labels,
                              colors=colors)
        cpu_subplot.legend(loc='best')

    filename = args.output
    if time_range:
        tr = '-%d-%d' % (time_range[0], time_range[1])
        filename = os.path.splitext(args.output)[0] + tr + '.svg'
    plt.savefig(filename)
    if args.verbose:
        print('Saving plot to %s' % filename)


thread = threading.Thread(target=record, args=())
thread.start()

ranges = []
if args.ranges:
    for r in args.ranges.split(','):
        parts = r.split('-')
        assert len(parts) == 2
        ranges.append([int(x) for x in parts])

if args.verbose:
    print('Ranges are %s' % str(ranges))
    print('Running command', flush=True)

try:
    subprocess.run(args.command, shell=True)
except KeyboardInterrupt:
    pass
finally:
    done = True
    thread.join()
    if global_memory_data:
        min_memory = min(global_memory_data)
        global_memory_data = [x - min_memory for x in global_memory_data]

        generate_graph(None)
        for r in ranges:
            generate_graph(r)
