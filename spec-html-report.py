#!/usr/bin/env python3

import os
import re
import shutil
import subprocess
from html import escape

spec_script = 'runcpu --config=spec2017 --size=ref --iterations=1  --no-reportable --tune=peak'
perf_record_prefix = 'perf record --call-graph dwarf'
perf_record_regex = re.compile(r'\s+([^\s]*)%\s+(?P<percent>[^\s]*)%\s*(?P<samples>[\d]+)\s*([^\s]*)\s*(?P<shobj>[^\s]*)\s*\[.\]\s(?P<function>.*)')
threshold_percent = 1
output_folder = 'html'

int_benchmarks = ['500.perlbench_r', '502.gcc_r', '505.mcf_r', '520.omnetpp_r', '523.xalancbmk_r',
                  '525.x264_r', '531.deepsjeng_r', '541.leela_r', '548.exchange2_r', '557.xz_r']
fp_benchmarks = ['503.bwaves_r', '507.cactuBSSN_r', '508.namd_r', '510.parest_r', '511.povray_r', '519.lbm_r',
                 '521.wrf_r', '526.blender_r', '527.cam4_r', '538.imagick_r', '544.nab_r', '549.fotonik3d_r',
                 '554.roms_r']

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


os.chdir('/home/marxin/Programming/cpu2017')
shutil.rmtree(output_folder, ignore_errors=True)

for benchmark in int_benchmarks + fp_benchmarks:
    print(f'== {benchmark} ==')
    subprocess.check_output('source ./shrc && runcpu --action trash --config=spec2017 all', shell=True)
    subprocess.check_output(f'source ./shrc && {spec_script}  --action build -D {benchmark}', shell=True)
    cmd = f'source ./shrc && perf record -F150 -o perf.data --call-graph dwarf {spec_script} --action run {benchmark}'
    subprocess.check_output(cmd, shell=True)
    r = subprocess.check_output('perf report --no-demangle --stdio -g none --show-nr-samples',
                                shell=True, encoding='utf8')
    report = parse_spec_report(r.splitlines())
    folder = os.path.join(output_folder, benchmark)
    os.makedirs(folder)
    flamegraph = os.path.join(folder, f'{benchmark}.svg')
    perf_script_output = filter_perf_script()
    cmd = f'~/Programming/FlameGraph/stackcollapse-perf.pl --context > tmp.txt ' \
          f'&& ~/Programming/FlameGraph/flamegraph.pl --title {benchmark} --minwidth 3 tmp.txt > {flamegraph}'
    subprocess.check_output(cmd, input=perf_script_output, shell=True)

    with open(os.path.join(folder, 'index.html'), 'w+') as f:
        f.write(f'<object class="p" data="{benchmark}.svg" type="image/svg+xml">'
                f'<img src="{benchmark}.svg" \\></object>')
        for mangled_function, (percentage, samples) in sorted(report.items(), key=lambda x: x[1], reverse=True):
            function = demangle(mangled_function)
            f.write(f'<h4><a href="index.html#{mangled_function}">{percentage}% ({samples} samples) - '
                    f'{escape(function)}</a></h4>')
        for mangled_function, (percentage, samples) in sorted(report.items(), key=lambda x: x[1], reverse=True):
            shutil.rmtree('/home/marxin/.debug/.build-id', ignore_errors=True)
            function = demangle(mangled_function)
            f.write(f'<h3 id="{mangled_function}">{percentage}% ({samples} samples) - {escape(function)}</h3>')
            cmd = f'perf annotate --no-demangle --symbol={mangled_function} --stdio --stdio-color=always -l |' \
                  ' aha --no-header'
            data = subprocess.check_output(cmd, shell=True)
            data = decode_perf_annotate(data)
            f.write('<pre style="font-size: 8pt;">')
            f.write(data)
            f.write('</pre>')
