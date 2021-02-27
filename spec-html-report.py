#!/usr/bin/env python3

import argparse
import datetime
import os
import re
import shutil
import subprocess
from html import escape

spec_script = 'runcpu --config=spec2017 --size=ref --iterations=1  --no-reportable --tune=peak'
perf_record_prefix = 'perf record --call-graph dwarf'
perf_record_regex = re.compile(r'\s+([^\s]*)%\s+(?P<percent>[^\s]*)%\s*(?P<samples>[\d]+)'
                               r'\s*([^\s]*)\s*(?P<shobj>[^\s]*)\s*\[.\]\s(?P<function>.*)')
perf_annotate_regex = re.compile(r'\s+(?P<percent>[0-9]+\.[0-9]+)\s+:.*')
context_size = 15
threshold_percent = 1
perf_annotate_threshold = 0.3
output_folder = 'html'

int_benchmarks = ['500.perlbench_r', '502.gcc_r', '505.mcf_r', '520.omnetpp_r', '523.xalancbmk_r',
                  '525.x264_r', '531.deepsjeng_r', '541.leela_r', '548.exchange2_r', '557.xz_r']
fp_benchmarks = ['503.bwaves_r', '507.cactuBSSN_r', '508.namd_r', '510.parest_r', '511.povray_r', '519.lbm_r',
                 '521.wrf_r', '526.blender_r', '527.cam4_r', '538.imagick_r', '544.nab_r', '549.fotonik3d_r',
                 '554.roms_r']

HTML_HEADER = """
    <html><head>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.0.0-beta2/dist/css/bootstrap.min.css"
            rel="stylesheet" integrity="sha384-BmbxuPwQa2lc/FVzBcNJ7UAyJxM6wuqIj61tLrc4wSX0szH/Ev+nYRRuWlolflfl"
            crossorigin="anonymous">
        <title>%s</title>
    </head>
    <body>
    <main>
    <div class="container">
    <h2>%s</h2>
"""

HTML_FOOTER = """
    </main></div><footer><div class="container">%s</div></footer></body></html>
"""

parser = argparse.ArgumentParser(description='SPEC perf analysis HTML report generator')
parser.add_argument('machine', help='Machine name')
parser.add_argument('compiler', help='Compiler name')
parser.add_argument('options', help='Compiler options')
args = parser.parse_args()


def skip_binary(binary):
    return binary.startswith('spec') or binary in ('runcpu', 'sh')


def parse_spec_report(lines):
    functions = {}
    for line in lines:
        m = perf_record_regex.match(line)
        if m:
            percent = float(m.group('percent'))
            samples = int(m.group('samples'))
            shobj = m.group('shobj')
            if not skip_binary(shobj) and percent >= threshold_percent:
                functions[m.group('function')] = (percent, samples)
    return functions


def decode_perf_annotate(data):
    try:
        return data.decode('utf8')
    except Exception:
        # Some Fortran SPEC benchmarks have latin1 encoding
        return data.decode('latin1')


def demangle(function):
    return subprocess.check_output(f'c++filt {function}', shell=True, encoding='utf8').strip()


def filter_perf_script():
    output = []
    data = subprocess.check_output('perf script', shell=True, encoding='utf8')
    records = data.strip().split('\n\n')
    for record in records:
        binary = record.split('\n')[0].split(' ')[0]
        if not skip_binary(binary):
            output.append(record)
    return '\n\n'.join(output).encode()


def write_hot_perf_annotate_hunks(data, data_nocolor):
    color_lines = data.split('\n')
    nocolor_lines = data_nocolor.split('\n')
    assert len(color_lines) == len(nocolor_lines)
    # add header to interesting spots
    lines_to_output = set(range(30))

    # investigate interesting spots
    for i, line in enumerate(nocolor_lines):
        m = perf_annotate_regex.match(line)
        if m and float(m.group('percent')) >= perf_annotate_threshold:
            for x in range(-context_size, context_size):
                lines_to_output.add(i + x)

    # output interesting hunks
    output = []
    last_line = -1
    for i, line in enumerate(color_lines):
        if i in lines_to_output:
            if last_line + 1 != i:
                output.append(f'... ({i - last_line - 1} lines skipped) ...')
            output.append(line)
            last_line = i

    # transform colored output to HTML
    return subprocess.check_output('aha --no-header', input='\n'.join(output), shell=True, encoding='utf8')


os.chdir(os.path.expanduser('~/Programming/cpu2017'))
if not os.path.exists(output_folder):
    os.mkdir(output_folder)

for benchmark in int_benchmarks + fp_benchmarks:
    title = f'{benchmark} - {args.machine} - {args.compiler} {args.options}'
    print(f'== {title} ==')
    subprocess.check_output('source ./shrc && runcpu --action trash --config=spec2017 all', shell=True)
    subprocess.check_output(f'source ./shrc && {spec_script}  --action build -D {benchmark}', shell=True)
    cmd = f'source ./shrc && perf stat -- {spec_script} --action run {benchmark}'
    r = subprocess.run(cmd, shell=True, encoding='utf8', stderr=subprocess.PIPE, stdout=subprocess.DEVNULL)
    assert r.returncode == 0
    stats = r.stderr.strip()
    print('  ... perf stat done')
    cmd = f'source ./shrc && perf record -F150 -o perf.data --call-graph dwarf {spec_script} --action run {benchmark}'
    subprocess.check_output(cmd, shell=True, stderr=subprocess.DEVNULL)
    r = subprocess.check_output('perf report --no-demangle --stdio -g none --show-nr-samples',
                                shell=True, encoding='utf8')
    print('  ... perf report done')
    report = parse_spec_report(r.splitlines())
    filename = f'{benchmark}-{args.machine}-{args.compiler}-{args.options}'
    filename = filename.replace(' ', '_').replace('-', '_')
    flamegraph = os.path.join(output_folder, f'{filename}.svg')
    perf_script_output = filter_perf_script()
    cmd = f'~/Programming/FlameGraph/stackcollapse-perf.pl --context > tmp.txt ' \
          f'&& ~/Programming/FlameGraph/flamegraph.pl --title {benchmark} --minwidth 3 tmp.txt > {flamegraph}'
    subprocess.check_output(cmd, input=perf_script_output, shell=True)

    with open(os.path.join(output_folder, filename + '.html'), 'w+') as f:
        f.write(HTML_HEADER % (title, title))
        f.write('<h3>Flame graph</h3>')
        f.write(f'<object class="p" data="{filename}.svg" type="image/svg+xml">'
                f'<img src="{filename}.svg" \\></object>')
        f.write('<h3>Perf stat</h3>')
        f.write(f'<pre style="font-size: 8pt;">{stats}</pre>')
        f.write('<h3>Perf annotate</h3>')
        f.write('<table class="table"><thead><th>Function</th><th class="text-end">Samples</th>'
                '<th class="text-end">Percentage</th></thead><tbody>')
        for mangled_function, (percentage, samples) in sorted(report.items(), key=lambda x: x[1], reverse=True):
            function = demangle(mangled_function)
            f.write(f'<tr><td><a href="#{mangled_function}">{escape(function)}</a></td>'
                    f'<td class="text-end">{samples}</td><td class="text-end">{percentage:.2f} %</td></tr>')
        f.write('<tbody></table>')
        for mangled_function, (percentage, samples) in sorted(report.items(), key=lambda x: x[1], reverse=True):
            shutil.rmtree(os.path.expanduser('~/.debug/.build-id'), ignore_errors=True)
            function = demangle(mangled_function)
            f.write(f'<h5 id="{mangled_function}">{percentage:.2f}% ({samples} samples) - {escape(function)}</h5>')
            cmd = f'perf annotate --no-demangle --symbol={mangled_function} --stdio --stdio-color=always -l'
            data = decode_perf_annotate(subprocess.check_output(cmd, shell=True))
            data_nocolor = decode_perf_annotate(subprocess.check_output(cmd + ' --stdio-color=never', shell=True))
            f.write('<pre style="font-size: 8pt;">')
            f.write(write_hot_perf_annotate_hunks(data, data_nocolor))
            f.write('</pre>')
        f.write(HTML_FOOTER % f'Generated {datetime.datetime.now()}')
