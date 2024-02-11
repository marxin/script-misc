#!/usr/bin/env python3

import argparse
import datetime
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
    import matplotlib
    import matplotlib.pyplot as plt
    from matplotlib.lines import Line2D
except ImportError:
    plt = None


def to_gigabyte(value):
    return value / 1024**3


def to_megabyte(value):
    return value / 1024**2


INTERVAL = 0.33
LW = 0.5

disk_data_total = to_gigabyte(psutil.disk_usage('.').total)
disk_data_start = to_gigabyte(psutil.disk_usage('.').used)


class DataStatistic:
    def __init__(self, collect_fn):
        self.collect_fn = collect_fn
        self.values = []

    def collect(self):
        self.values.append(self.collect_fn())

    def maximum(self):
        return max(self.values)

    def minimum(self):
        return min(self.values)

    def average(self):
        return sum(self.values) / len(self.values)

    def empty(self):
        return not self.values


class DiskDataStatistic(DataStatistic):
    def __init__(self, collect_fn):
        self.latest_value = collect_fn()
        self.start_value = collect_fn()
        super().__init__(collect_fn)

    def collect(self):
        value = self.collect_fn()
        self.values.append(value - self.latest_value)
        self.latest_value = value

    def difference_in_gb(self):
        return (self.latest_value - self.start_value) / 1024


timestamps = []
process_usage = []
process_hogs = {}

process_name_map = {}
lock = threading.Lock()

done = False
start_ts = time.monotonic()

special_processes = {'linker': 'gold',
                     'WPA': 'deepskyblue',
                     'WPA-stream': 'lightblue',
                     'ltrans': 'forestgreen',
                     'as': 'coral',
                     'GCC': 'gray',
                     'clang': 'darkgray',
                     'rust': 'brown',
                     'go': 'hotpink',
                     'dwz': 'limegreen',
                     'rpm/rpm2cpio/dpkg': 'plum',
                     'xsltproc': 'bisque'}
for i, k in enumerate(special_processes.keys()):
    process_name_map[k] = i

cpu_count = psutil.cpu_count()

descr = 'Run command and measure memory and CPU utilization'
parser = argparse.ArgumentParser(description=descr)
parser.add_argument('command', metavar='command',
                    help='Command', nargs=argparse.REMAINDER)
parser.add_argument('-c', '--command', dest='command1',
                    help='command as a single argument')
parser.add_argument('-v', '--verbose', action='store_true', help='Verbose')
parser.add_argument('-S', '--summary-only', dest='summary_only',
                    action='store_true',
                    help='No plot, just a summary at the end')
parser.add_argument('-b', '--base-memory', action='store_true',
                    help='Adjust memory to include the system load')
parser.add_argument('-s', '--separate-ltrans', action='store_true',
                    help='Separate LTRANS processes in graph')
parser.add_argument('-o', '--output', default='usage.svg',
                    help='Path to output image (default: usage.svg)')
parser.add_argument('-t', '--title', help='Graph title')
parser.add_argument('-m', '--memory-hog-threshold', type=float,
                    help='Report about processes that consume the amount of '
                    'memory (in GiB)')
parser.add_argument('-f', '--frequency', type=float,
                    default=INTERVAL,
                    help='Frequency of measuring (in seconds)')
parser.add_argument('-j', '--jobs', type=int,
                    default=cpu_count, dest='used_cpus',
                    help='Scale up CPU data to used CPUs '
                    'instead of available CPUs')
parser.add_argument('--y-scale', type=int,
                    help='Minimal y-scale (in GiB)')

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
cpu_stats = DataStatistic(lambda: psutil.cpu_percent(interval=args.frequency) * cpu_scale)
mem_stats = DataStatistic(lambda: to_gigabyte(psutil.virtual_memory().used))
load_stats = DataStatistic(lambda: 100 * psutil.getloadavg()[0] / cpu_count)
disk_read_stats = DiskDataStatistic(lambda: to_megabyte((1 / INTERVAL) * (psutil.disk_io_counters().read_bytes)))
disk_write_stats = DiskDataStatistic(lambda: to_megabyte((1 / INTERVAL) * (psutil.disk_io_counters().write_bytes)))

collectors = [cpu_stats, mem_stats, load_stats, disk_read_stats, disk_write_stats]

try:
    import GPUtil
    gpu_stats = DataStatistic(lambda: 100 * GPUtil.getGPUs()[0].load)
    collectors.append(gpu_stats)
except ImportError:
    gpu_stats = None


def get_process_name(proc):
    name = proc.name()
    cmdline = proc.cmdline()
    if name in ('ld', 'ld.gold', 'ld.lld', 'ld.mold'):
        return 'linker'
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
    elif name in ('rpmbuild', 'rpm2cpio') or name.startswith('dpkg'):
        return 'rpm/rpm2cpio/dpkg'
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
            if cmd not in process_hogs:
                process_hogs[cmd] = tpl
            elif memory > process_hogs[cmd][0]:
                process_hogs[cmd] = tpl


def record():
    active_pids = {}
    while not done:
        timestamp = time.monotonic() - start_ts
        timestamps.append(timestamp)
        for stat in collectors:
            stat.collect()

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
            process_usage.append(entry)


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
    cpu_average = cpu_stats.average()
    cpu_max = cpu_stats.maximum()
    peak_memory = mem_stats.maximum()
    total_mem = to_gigabyte(psutil.virtual_memory().total)
    gpu_line = ''
    if gpu_stats:
        gpu_line = f' GPU avg/max: {gpu_stats.average():.1f}/{gpu_stats.maximum():.1f};'
    return (f'host: {hostname}; CPUs: {args.used_cpus}/{cpu_count};'
            f' CPU avg/max: {cpu_average:.1f}/{cpu_max:.1f}%;'
            f'{gpu_line}'
            f' RAM peak/total: {peak_memory:.1f}/{total_mem:.1f} GiB;')


def get_footnote2():
    disk_total = disk_data_total
    disk_start = disk_data_start
    disk_end = to_gigabyte(psutil.disk_usage('.').used)
    total_read = disk_read_stats.difference_in_gb()
    total_written = disk_write_stats.difference_in_gb()
    load_max = load_stats.maximum()
    ts = str(datetime.datetime.now())
    # strip second fraction part
    ts = ts[:ts.rindex('.')]
    return (f'taken: {int(timestamps[-1])} s; created: {ts};'
            f' load max (1m): {load_max:.0f}%;'
            f' disk start/end/total: {disk_start:.1f}/{disk_end:.1f}/{disk_total:.1f} GiB;'
            f' total read/write GiB: {total_read:.1f}/{total_written:.1f}')


def generate_graph():
    peak_memory = mem_stats.maximum()

    fig, (cpu_subplot, mem_subplot, disk_subplot) = plt.subplots(3, sharex=True)
    title = args.title if args.title else ''
    fig.suptitle(title, fontsize=17)
    fig.set_figheight(8)
    fig.set_figwidth(10)
    # scale cpu axis
    local_peak_cpu = max(cpu_stats.values + load_stats.values + (gpu_stats.values if gpu_stats else []))
    cpu_ylimit = (local_peak_cpu // 10) * 11 + 5
    if cpu_ylimit > 300:
        cpu_ylimit = 300
    cpu_subplot.set_title('CPU usage')
    cpu_subplot.set_ylabel('%')
    cpu_subplot.plot(timestamps, cpu_stats.values, c='blue', lw=LW, label='total')
    cpu_subplot.plot(timestamps, load_stats.values, c='cyan', lw=LW, label='load')
    cpu_subplot.set_ylim([0, cpu_ylimit])
    cpu_subplot.axhline(color='r', alpha=0.5, y=100.0 / args.used_cpus, lw=LW,
                        linestyle='dotted', label='single core')
    cpu_subplot.set_xlim(left=0)
    cpu_subplot.grid(True)

    mem_subplot.plot(timestamps, mem_stats.values, c='blue', lw=LW, label='total')
    mem_subplot.set_title('Memory usage')
    mem_subplot.set_ylabel('GiB')

    disk_subplot.plot(timestamps, disk_read_stats.values, c='green', lw=LW, label='read')
    disk_subplot.plot(timestamps, disk_write_stats.values, c='red', lw=LW, label='write')
    disk_subplot.set_title('Disk read/write')
    disk_subplot.set_ylabel('MiB/s')
    disk_subplot.set_xlabel('time')

    if gpu_stats:
        cpu_subplot.plot(timestamps, gpu_stats.values, c='fuchsia', lw=LW, label='GPU')

    # scale it to a reasonable limit
    limit = 1
    while peak_memory > limit:
        limit *= 2
    if limit > 2 and limit * 0.75 >= peak_memory:
        limit = int(limit * 0.75)

    if args.y_scale and limit < args.y_scale:
        limit = args.y_scale

    mem_subplot.set_ylim([0, 1.1 * limit])
    mem_subplot.set_yticks(range(0, limit + 1, math.ceil(limit / 8)))
    mem_subplot.grid(True)

    disk_subplot.grid(True)

    colors = list(matplotlib.colormaps['tab20c'].colors * 100)
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
        names = ['CPU: single core', 'CPU: total', 'CPU: load']
        if gpu_stats:
            names += ['GPU: total']
        names += ['disk: read', 'disk: write']

        custom_lines = []
        custom_lines.append(Line2D([0], [0], color='r', alpha=0.5, linestyle='dotted', lw=LW))
        custom_lines.append(Line2D([0], [0], color='b', lw=LW))
        custom_lines.append(Line2D([0], [0], color='cyan', lw=LW))
        if gpu_stats:
            custom_lines.append(Line2D([0], [0], color='fuchsia', lw=LW))
        custom_lines.append(Line2D([0], [0], color='green', lw=LW))
        custom_lines.append(Line2D([0], [0], color='red', lw=LW))

        colors = special_processes.values()
        custom_lines += [Line2D([0], [0], color=x, lw=5) for x in colors]
        names += list(special_processes.keys())
        fig.legend(custom_lines, names, loc='right', prop={'size': 6})

    filename = args.output
    plt.subplots_adjust(bottom=0.12)
    plt.figtext(0.1, 0.04, get_footnote(), fontsize='small')
    plt.figtext(0.1, 0.01, get_footnote2(), fontsize='small')
    plt.savefig(filename)
    if args.verbose:
        print('Saving plot to %s' % filename)


def summary():
    print()
    print(f'SUMMARY: {get_footnote()}')
    print(f'SUMMARY: {get_footnote2()}')
    if process_hogs:
        print(f'PROCESS MEMORY HOGS (>={args.memory_hog_threshold:.1f} GiB):')
        items = sorted(process_hogs.items(), key=lambda x: x[1][0],
                       reverse=True)
        for cmdline, (memory, ts) in items:
            print(f'  {memory:.1f} GiB: {ts:.1f} s: {cmdline}')


thread = threading.Thread(target=record, args=())
thread.start()

if args.verbose:
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
    if not mem_stats.empty():
        min_memory = mem_stats.minimum()
        if not args.base_memory:
            mem_stats.values = [x - min_memory for x in mem_stats.values]

        if not args.summary_only:
            generate_graph()
    if cp:
        rv = cp.returncode

if rv != 0:
    print(f'\nWARNING: non-zero return code returned: {rv}')
sys.exit(rv)
