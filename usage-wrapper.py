#!/usr/bin/env python3

import argparse
import math
import os
import subprocess
import sys
import threading
import time

try:
    import psutil
except ImportError:
    print(f'{sys.argv[0]}: the psutil module is required.', file=sys.stderr)
    sys.exit(1)

try:
    import matplotlib.pyplot as plt
except ImportError:
    plt = None

INTERVAL = 0.33
LW = 0.5

global_n = 0
global_cpu_data_sum = 0
global_memory_data_sum = 0
global_cpu_data_max = 0
global_memory_data_min = 0
global_memory_data_max = 0

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

special_processes = {'ld': 'gold',
                     'WPA': 'deepskyblue',
                     'WPA-stream-out': 'lightblue',
                     'ltrans': 'forestgreen',
                     'as': 'coral',
                     'dwz': 'limegreen',
                     'rpmbuild': 'plum'}
for i, k in enumerate(special_processes.keys()):
    process_name_map[k] = i
    process_labels.append(k)


descr = 'Run command and measure memory and CPU utilization'
parser = argparse.ArgumentParser(description=descr)
parser.add_argument('command', metavar='command',
                    help='Command', nargs=argparse.REMAINDER)
parser.add_argument('-c', '--command', dest='command1',
                    help='command as a single argument')
parser.add_argument('-v', '--verbose', action='store_true', help='Verbose')
parser.add_argument('--summary-only', dest='summary_only',
                    action='store_true',
                    help='No plot, just a summary at the end')
parser.add_argument('--no-base-memory', dest='base_memory_only',
                    action='store_true',
                    help='Adjust memory to not include the system load')
parser.add_argument('-s', '--separate-ltrans', action='store_true',
                    help='Separate LTRANS processes in graph')
parser.add_argument('-o', '--output', default='usage.svg',
                    help='Path to output image (default: usage.svg)')
parser.add_argument('-r', '--ranges',
                    help='Plot only the selected time ranges '
                    '(e.g. 20-30, 0-1000)')
parser.add_argument('-t', '--title', help='Graph title')
parser.add_argument('-f', '--frequency', type=float,
                    default=INTERVAL,
                    help='Frequency of measuring (in seconds)')
args = parser.parse_args()

if args.command1 and args.command:
    print(f'{sys.argv[0]}: either use -c "<shell command>", '
          'or append the command', file=sys.stderr)
    sys.exit(1)

if not args.summary_only and plt is None:
    print(f'{sys.argv[0]}: use --summary-only, '
          'or install the matplotlib module', file=sys.stderr)
    sys.exit(1)


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
    elif name == 'as' or name == 'dwz' or name == 'rpmbuild':
        return name
    elif '-fltrans' in cmdline:
        if args.separate_ltrans:
            return 'ltrans-%d' % proc.pid
        else:
            return 'ltrans'
    return None


def record():
    global global_n, global_cpu_data_sum, global_cpu_data_max
    global global_memory_data_sum, global_memory_data_min
    global global_memory_data_max

    active_pids = {}
    while not done:
        timestamp = time.monotonic() - start_ts
        used_cpu = psutil.cpu_percent(interval=args.frequency)
        used_memory = to_gigabyte(psutil.virtual_memory().used)
        if not args.summary_only:
            global_timestamps.append(timestamp)
            global_memory_data.append(used_memory)
            global_cpu_data.append(used_cpu)

        global_n += 1
        global_cpu_data_sum += used_cpu
        global_memory_data_sum += used_memory
        if used_cpu > global_cpu_data_max:
            global_cpu_data_max = used_cpu
        if used_memory < global_memory_data_min:
            global_memory_data_min = used_memory
        if used_memory > global_memory_data_max:
            global_memory_data_max = used_memory

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
                        if name not in special_processes:
                            process_labels.append(None)
                    if name not in entry:
                        entry[name] = {'memory': 0, 'cpu': 0}
                    entry[name]['cpu'] += cpu
                    # FIXME: ignore WPA streaming memory - COW makes it bogus
                    if name != 'WPA-stream-out':
                        entry[name]['memory'] += memory
            except Exception:
                # the process can be gone
                pass
        for pid in list(active_pids.keys()):
            if pid not in seen_pids:
                del active_pids[pid]
        if args.verbose:
            print(entry, flush=True)
        if not args.summary_only:
            global_process_usage.append(entry)


def stack_values(process_usage, key):
    stacks = []
    for _ in range(len(process_name_map)):
        stacks.append([])
    for values in process_usage:
        for k, v in process_name_map.items():
            if k in values:
                stacks[v].append(values[k][key])
            else:
                stacks[v].append(0)
    return stacks


def generate_graph(time_range):
    timestamps = []
    cpu_data = []
    memory_data = []
    process_usage = []

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

    peak_memory = max(memory_data)

    fig, (cpu_subplot, mem_subplot) = plt.subplots(2, sharex=True)
    title = args.title if args.title else ''
    if time_range:
        title += ' (%d-%d s)' % (time_range[0], time_range[1])
    fig.suptitle(title, fontsize=17)
    fig.set_figheight(5)
    fig.set_figwidth(10)
    local_peak_memory = max(memory_data)
    local_cpu_average = sum(cpu_data) / len(cpu_data)
    cpu_subplot.set_title('CPU usage')
    cpu_subplot.set_ylabel('%')
    cpu_subplot.plot(timestamps, cpu_data, c='blue', lw=LW, label='total')
    cpu_subplot.set_ylim([0, 105])
    cpu_subplot.axhline(color='r', alpha=0.5, y=100.0 / cpu_count, lw=LW,
                        linestyle='dotted', label='single core')
    cpu_subplot.set_xlim(left=time_range[0] if time_range else 0)
    cpu_subplot.grid(True)

    mem_subplot.plot(timestamps, memory_data, c='blue', lw=LW, label='total')
    mem_subplot.set_title('Memory usage')
    mem_subplot.set_ylabel('GB')
    mem_subplot.set_xlabel('time')

    # scale it to a reasonable limit
    limit = 1
    while peak_memory > limit:
        limit *= 2
    if limit > 2 and limit * 0.75 >= peak_memory:
        limit = int(limit * 0.75)
    mem_subplot.set_ylim([0, 1.1 * limit])
    mem_subplot.set_yticks(range(0, limit + 1, math.ceil(limit / 8)))
    mem_subplot.grid(True)

    colors = list(plt.cm.get_cmap('tab20c').colors * 100)
    for name, color in special_processes.items():
        if name in process_name_map:
            colors[process_name_map[name]] = color

    mem_stacks = stack_values(process_usage, 'memory')
    cpu_stacks = stack_values(process_usage, 'cpu')
    if mem_stacks:
        mem_subplot.stackplot(timestamps, mem_stacks, labels=process_labels,
                              colors=colors)
        mem_subplot.legend(loc='best', prop={'size': 6})
        cpu_subplot.stackplot(timestamps, cpu_stacks, labels=process_labels,
                              colors=colors)
        cpu_subplot.legend(loc='best', prop={'size': 6})

    filename = args.output
    if time_range:
        tr = '-%d-%d' % (time_range[0], time_range[1])
        filename = os.path.splitext(args.output)[0] + tr + '.svg'
    plt.subplots_adjust(bottom=0.15)
    hostname = os.uname()[1].split('.')[0]
    plt.figtext(0.1, 0.025,
                'hostname: %s; CPU count: %d, CPU avg: %.1f%%, '
                'peak memory: %.1f GB; total memory: %.1f GB'
                % (hostname, cpu_count, local_cpu_average, local_peak_memory,
                   to_gigabyte(psutil.virtual_memory().total)))
    plt.savefig(filename)
    if args.verbose:
        print('Saving plot to %s' % filename)


def summary():
    hostname = os.uname()[1].split('.')[0]
    cpu_average = global_cpu_data_sum / global_n
    peak_memory = global_memory_data_max
    print('SUMMARY:', 'hostname: %s; CPU count: %d, CPU avg: %.1f%%, '
          'min memory: %.1f GB; peak memory: %.1f GB; total memory: %.1f GB'
          % (hostname, cpu_count, cpu_average, global_memory_data_min,
             peak_memory, to_gigabyte(psutil.virtual_memory().total)))


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
    cmd = args.command1 if args.command1 else args.command
    cp = subprocess.run(cmd, shell=True)
except KeyboardInterrupt:
    rv = 2
finally:
    done = True
    thread.join()
    summary()
    if global_memory_data:
        min_memory = min(global_memory_data)
        if args.base_memory_only:
            global_memory_data = [x - min_memory for x in global_memory_data]

        if plt:
            generate_graph(None)
            for r in ranges:
                generate_graph(r)
    if cp:
        rv = cp.returncode

sys.exit(rv)
