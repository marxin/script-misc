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
    from matplotlib.lines import Line2D
except ImportError:
    plt = None


def to_gigabyte(value):
    return value / 1024**3


INTERVAL = 0.33
LW = 0.5

global_n = 0
global_cpu_data_sum = 0
global_memory_data_sum = 0
global_cpu_data_max = 0
global_memory_data_min = to_gigabyte(psutil.virtual_memory().total)
global_memory_data_max = 0
global_swap_data_min = to_gigabyte(psutil.swap_memory().total)
global_swap_data_max = 0
global_disk_data_total = to_gigabyte(psutil.disk_usage('.').total)
global_disk_data_start = to_gigabyte(psutil.disk_usage('.').used)

global_timestamps = []
global_cpu_data = []
global_memory_data = []
global_process_usage = []
global_process_hogs = {}

process_name_map = {}
lock = threading.Lock()

done = False
start_ts = time.monotonic()
cpu_count = psutil.cpu_count()

special_processes = {'ld': 'gold',
                     'WPA': 'deepskyblue',
                     'WPA-stream': 'lightblue',
                     'ltrans': 'forestgreen',
                     'as': 'coral',
                     'GCC': 'gray',
                     'clang': 'darkgray',
                     'rust': 'brown',
                     'go': 'hotpink',
                     'dwz': 'limegreen',
                     'rpm/dpkg': 'plum'}
for i, k in enumerate(special_processes.keys()):
    process_name_map[k] = i


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
parser.add_argument('--base-memory', action='store_true',
                    help='Adjust memory to include the system load')
parser.add_argument('-s', '--separate-ltrans', action='store_true',
                    help='Separate LTRANS processes in graph')
parser.add_argument('-o', '--output', default='usage.svg',
                    help='Path to output image (default: usage.svg)')
parser.add_argument('-r', '--ranges',
                    help='Plot only the selected time ranges '
                    '(e.g. 20-30, 0-1000)')
parser.add_argument('-t', '--title', help='Graph title')
parser.add_argument('-m', '--memory-hog-threshold', type=float,
                    help='Report about processes that consume the amount of '
                    'memory (in GB)')
parser.add_argument('-f', '--frequency', type=float,
                    default=INTERVAL,
                    help='Frequency of measuring (in seconds)')
parser.add_argument('-j', '--jobs', type=int,
                    default=cpu_count, dest='used_cpus',
                    help='Scale up CPU data to used CPUs '
                    'instead of available CPUs')
args = parser.parse_args()

if args.command1 and args.command:
    print(f'{sys.argv[0]}: either use -c "<shell command>", '
          'or append the command', file=sys.stderr)
    sys.exit(1)

if not args.summary_only and plt is None:
    print(f'{sys.argv[0]}: use --summary-only, '
          'or install the matplotlib module', file=sys.stderr)
    sys.exit(1)

cpu_scale = cpu_count / args.used_cpus


def get_process_name(proc):
    name = proc.name()
    cmdline = proc.cmdline()
    if name == 'ld' or name == 'ld.gold':
        return 'ld'
    elif name == 'lto1-wpa':
        return 'WPA'
    elif name == 'lto1-wpa-stream':
        return 'WPA-stream-out'
    elif name in ('cc1', 'cc1plus', 'cc1objc', 'f951', 'd21', 'go1', 'gnat1'):
        return 'GCC'
    elif name.startswith('clang'):
        return 'clang'
    elif name.startswith('rust'):
        return 'rust'
    elif name in ('as', 'dwz', 'go'):
        return name
    elif name == 'rpmbuild' or name.startswith('dpkg'):
        return 'rpm/dpkg'
    elif '-fltrans' in cmdline:
        if args.separate_ltrans:
            return 'ltrans-%d' % proc.pid
        else:
            return 'ltrans'
    return None


def record_process_memory_hog(proc, memory, timestamp):
    if args.memory_hog_threshold:
        if memory >= args.memory_hog_threshold:
            cmd = ' '.join(proc.cmdline())
            tpl = (memory, timestamp)
            if cmd not in global_process_hogs:
                global_process_hogs[cmd] = tpl
            elif memory > global_process_hogs[cmd][0]:
                global_process_hogs[cmd] = tpl


def record():
    global global_n, global_cpu_data_sum, global_cpu_data_max
    global global_memory_data_sum, global_memory_data_min
    global global_memory_data_max
    global global_swap_data_min, global_swap_data_max

    active_pids = {}
    while not done:
        timestamp = time.monotonic() - start_ts
        used_cpu = psutil.cpu_percent(interval=args.frequency) * cpu_scale
        used_memory = to_gigabyte(psutil.virtual_memory().used)
        used_swap = to_gigabyte(psutil.swap_memory().used)
        if not args.summary_only:
            global_timestamps.append(timestamp)
            global_memory_data.append(used_memory)
            global_cpu_data.append(used_cpu)

        global_n += 1
        global_cpu_data_sum += used_cpu
        global_memory_data_sum += used_memory
        global_cpu_data_max = max(global_cpu_data_max, used_cpu)
        global_memory_data_min = min(global_memory_data_min, used_memory)
        global_memory_data_max = max(global_memory_data_max, used_memory)
        global_swap_data_min = min(global_swap_data_min, used_swap)
        global_swap_data_max = max(global_swap_data_max, used_swap)

        entry = {}
        seen_pids = set()
        for proc in psutil.Process().children(recursive=True):
            try:
                memory = to_gigabyte(proc.memory_info().rss)
                record_process_memory_hog(proc, memory, timestamp)
                name = get_process_name(proc)
                if name:
                    seen_pids.add(proc.pid)
                    if proc.pid not in active_pids:
                        active_pids[proc.pid] = proc
                    else:
                        proc = active_pids[proc.pid]
                    cpu = proc.cpu_percent() / args.used_cpus
                    if name not in process_name_map:
                        length = len(process_name_map)
                        process_name_map[name] = length
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


def get_footnote():
    hostname = os.uname()[1].split('.')[0]
    cpu_average = global_cpu_data_sum / global_n
    cpu_max = global_cpu_data_max
    base_memory = global_memory_data_min
    peak_memory = global_memory_data_max
    total_mem = to_gigabyte(psutil.virtual_memory().total)
    return (f'host: {hostname}; CPUs: {args.used_cpus}/{cpu_count};'
            f' CPU avg: {cpu_average:.0f}%;'
            f' CPU max: {cpu_max:.0f}%;'
            f' base memory: {base_memory:.1f} GB;'
            f' peak memory: {peak_memory:.1f} GB;'
            f' total memory: {total_mem:.1f} GB')


def get_footnote2():
    peak_swap = global_swap_data_max
    total_swap = to_gigabyte(psutil.swap_memory().total)
    disk_total = global_disk_data_total
    disk_start = global_disk_data_start
    disk_end = to_gigabyte(psutil.disk_usage('.').used)
    disk_delta = disk_end - disk_start
    return (f'swap peak/total: {peak_swap:.1f}/{total_swap:.1f} GB;'
            f' disk start/end/total: {disk_start:.1f}/{disk_end:.1f}/{disk_total:.1f} GB;'
            f' disk delta: {disk_delta:.1f} GB')


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
    # scale cpu axis
    local_peak_cpu = max(cpu_data)
    cpu_ylimit = (local_peak_cpu // 10) * 11 + 5
    if cpu_ylimit > 200:
        cpu_ylimit = 200
    cpu_subplot.set_title('CPU usage')
    cpu_subplot.set_ylabel('%')
    cpu_subplot.plot(timestamps, cpu_data, c='blue', lw=LW, label='total')
    cpu_subplot.set_ylim([0, cpu_ylimit])
    cpu_subplot.axhline(color='r', alpha=0.5, y=100.0 / args.used_cpus, lw=LW,
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
        mem_subplot.stackplot(timestamps, mem_stacks,
                              colors=colors)
        cpu_subplot.stackplot(timestamps, cpu_stacks,
                              colors=colors)

        # generate custom legend
        colors = special_processes.values()
        custom_lines = [Line2D([0], [0], color=x, lw=5) for x in colors]
        custom_lines.insert(0, Line2D([0], [0], color='b', lw=LW))
        custom_lines.insert(0, Line2D([0], [0], color='r', alpha=0.5,
                                      linestyle='dotted', lw=LW))
        names = ['single core', 'total'] + list(special_processes.keys())
        fig.legend(custom_lines, names, loc='right', prop={'size': 6})

    filename = args.output
    if time_range:
        tr = '-%d-%d' % (time_range[0], time_range[1])
        filename = os.path.splitext(args.output)[0] + tr + '.svg'
    plt.subplots_adjust(bottom=0.15)
    plt.figtext(0.1, 0.04, get_footnote(), fontsize='small')
    plt.figtext(0.1, 0.01, get_footnote2(), fontsize='small')
    plt.savefig(filename)
    if args.verbose:
        print('Saving plot to %s' % filename)


def summary():
    print(f'SUMMARY: {get_footnote()}')
    print(f'SUMMARY: {get_footnote2()}')
    if global_process_hogs:
        print(f'PROCESS MEMORY HOGS (>={args.memory_hog_threshold:.1f} GB):')
        items = sorted(global_process_hogs.items(), key=lambda x: x[1][0],
                       reverse=True)
        for cmdline, (memory, ts) in items:
            print(f'  {memory:.1f} GB: {ts:.1f} s: {cmdline}')


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

cp = None
try:
    if args.command1:
        cp = subprocess.run(args.command1, shell=True)
    else:
        cp = subprocess.run(args.command)
except KeyboardInterrupt:
    rv = 2
finally:
    done = True
    thread.join()
    summary()
    if global_memory_data:
        min_memory = min(global_memory_data)
        if not args.base_memory:
            global_memory_data = [x - min_memory for x in global_memory_data]

        if plt:
            generate_graph(None)
            for r in ranges:
                generate_graph(r)
    if cp:
        rv = cp.returncode

sys.exit(rv)
