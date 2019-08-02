#!/usr/bin/env python3

import os
import json

def get_svn_revision(path):
    x = 'Updated to revision '
    x2 = 'At revision '
    for l in open(path).readlines():
        l = l.strip()
        if l.startswith(x):
            return l[len(x):-1]
        elif l.startswith(x2):
            return l[len(x2):-1]

    return None

def find_file_by_extension(path, extension):
    assert extension.startswith('.')
    files = os.listdir(path)
    candidates = list(filter(lambda x: x.endswith(extension), files))
    if len(candidates) == 1:
        return os.path.join(path, candidates[0])
    else:
        return None

def get_revision_for_dir(path):
    if len(os.listdir(path)) == 0:
        return None
    else:
        log = find_file_by_extension(path, '.log')
        revision = get_svn_revision(log)
        return revision

def values_for_rsf_line(lines, key1, key2):
    return [x[x.find(':')+1:].strip() for x in lines if key1 in x and key2 in x]

def value_for_rsf_line(lines, key1, key2):
    before = lines
    lines = values_for_rsf_line(lines, key1, key2)
    if len(lines) == 0:
        return None
    return lines[0]

def parse_spec(rsf_file, statistics_file):
    d = {}
    lines = [x.strip() for x in open(rsf_file).readlines()]
    statistics = [x.strip() for x in open(statistics_file).readlines()]
    reported = [x for x in lines if 'reported_time' in x]
    for report in reported:
        time = report.split(':')[-1].strip()
        tokens = report.split('.')
        name = tokens[3]

        if not name in d:
            d[name] = {}

    for tune in ['base', 'peak']:
        for benchmark in d.keys():
            key = benchmark + '.' + tune
            time = value_for_rsf_line(lines, key, 'reported_time')
            if time == None:
                continue

            if time == '--':
                time = None
            else:
                time = float(time)

            ratio = value_for_rsf_line(lines, key, '.ratio:')
            if ratio == '--':
                ratio = None
            else:
                ration = float(ratio)
            reference = int(value_for_rsf_line(lines, key, '.reference:'))

            d[benchmark][tune] = {}
            v = d[benchmark][tune]

            d[benchmark][tune]['name'] = benchmark
            d[benchmark][tune]['tune'] = tune
            d[benchmark][tune]['time'] = time
            d[benchmark][tune]['ratio'] = ratio
            d[benchmark][tune]['reference'] = reference

            errors = values_for_rsf_line(lines, key, 'errors')
            if len(errors) > 0:
                d[benchmark][tune]['errors'] = errors
            else:
                d[benchmark][tune]['errors'] = None

            compile_time = value_for_rsf_line(statistics, key, 'compiletime')
            d[benchmark][tune]['compiletime'] = int(compile_time)
            binary_size = values_for_rsf_line(statistics, key, 'size')
            if len(binary_size) == 1:
                d[benchmark][tune]['binary_size'] = binary_size[0]
            elif len(binary_size) == 0:
                d[benchmark][tune]['binary_size'] = None
            else:
                assert False

    return d

root_dir = '/home/marxin/BIG/Programming/opensuse-data'
evans_config = ('evans', [('2006', 'normal', 'sb-evans-head-64-2006')])
megrez_config = ('megrez', [('2000', 'normal', 'sb-megrez-head-64')])

d = []

machines = [evans_config, megrez_config]
for machine_config in machines:
    configuration_results = []
    for configuration in machine_config[1]:
        # 1) parse SVN revisions
        base_dir = os.path.join(root_dir, configuration[2])
        svn_logs_dir = os.path.join(base_dir, 'log')
        dirs = sorted(os.listdir(svn_logs_dir), reverse = True)

        svn_dictionary = {}

        for (i, timestamp) in enumerate(dirs):
            dir = os.path.join(svn_logs_dir, timestamp)
            revision = get_revision_for_dir(dir)
            if revision == None and i != len(dirs) - 1:
                revision = get_revision_for_dir(os.path.join(svn_logs_dir, dirs[i + 1]))

            svn_dictionary[timestamp] = revision

        # 2) parse SPEC results
        spec_results_dir = os.path.join(base_dir, 'x86_64/spec-result')
        results = []

        for root, dirs, files in os.walk(spec_results_dir):
            if root == spec_results_dir:
                for result in dirs:
                    if not '.' in result:
                        continue
                    tokens = result.split('.')
                    timestamp = tokens[0]
                    # Can be null
                    # assert timestamp in svn_dictionary
                    suffix = tokens[1]
                    f = os.path.join(root, result)
                    rsf = find_file_by_extension(f, '.rsf')
                    if rsf == None:
                        rsf = find_file_by_extension(f, '.raw')
                    if rsf == None:
                        continue
                    svn = None
                    if timestamp in svn_dictionary:
                        svn = svn_dictionary[timestamp]
                    results.append({'results': parse_spec(rsf, find_file_by_extension(f, '.' + suffix)), 'group': suffix, 'svn':  svn, 'timestamp': timestamp})
        d3 = {'type': configuration[0], 'name': configuration[1], 'results': results}
        configuration_results.append(d3)

    d2 = {'name': machine_config[0], 'specs': configuration_results}
    d.append(d2)

print(json.dumps(d, indent = 2))
