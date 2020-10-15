#!/usr/bin/env python3

import subprocess
import time

import matplotlib.pyplot as plt

import psutil

INTERVAL = 0.04
FILENAME = 'cpu-frequency.svg'
cpu_count = psutil.cpu_count()

times = []
cpus = []
frequencies = []

start = time.monotonic()

try:
    while True:
        cpu = psutil.cpu_percent(percpu=True)[0]
        r = subprocess.check_output('cat /proc/cpuinfo | grep MHz | head -n1',
                                    shell=True, encoding='utf8')
        freq = float(r.strip().split(' ')[-1])
        d = time.monotonic() - start
        print('%3.2f CPU: %6.2f%%, frequency: %.2f MHz' % (d, cpu, freq))
        time.sleep(INTERVAL)

        times.append(d)
        cpus.append(cpu)
        frequencies.append(freq)
except KeyboardInterrupt:
    pass
finally:
    print('xx')
    plt.plot(times, cpus, label='CPU #0 usage (in %)')
    plt.plot(times, frequencies, label='CPU #0 frequency (in MHz)')
    plt.grid(True)
    plt.legend()
    for i, ts in enumerate(times):
        if i < len(times) - 1 and abs(cpus[i] - cpus[i + 1]) > 50:
            plt.vlines(ts, 0, 4000, linestyles='dashed', lw=1, colors='gray')

    plt.title('CPU usage and frequency')
    plt.xlabel('time (s)')
    print('Saving to %s' % FILENAME)
    plt.savefig(FILENAME)
