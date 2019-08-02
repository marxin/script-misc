#!/usr/bin/env python3

cpus = """
  {"generic", &generic_cost, 16, 10, 16, 10, 16},
  {"i386", &i386_cost, 4, 3, 4, 3, 4},
  {"i486", &i486_cost, 16, 15, 16, 15, 16},
  {"pentium", &pentium_cost, 16, 7, 16, 7, 16},
  {"lakemont", &lakemont_cost, 16, 7, 16, 7, 16},
  {"pentiumpro", &pentiumpro_cost, 16, 15, 16, 10, 16},
  {"pentium4", &pentium4_cost, 0, 0, 0, 0, 0},
  {"nocona", &nocona_cost, 0, 0, 0, 0, 0},
  {"core2", &core_cost, 16, 10, 16, 10, 16},
  {"nehalem", &core_cost, 16, 10, 16, 10, 16},
  {"sandybridge", &core_cost, 16, 10, 16, 10, 16},
  {"haswell", &core_cost, 16, 10, 16, 10, 16},
  {"bonnell", &atom_cost, 16, 15, 16, 7, 16},
  {"silvermont", &slm_cost, 16, 15, 16, 7, 16},
  {"goldmont", &slm_cost, 16, 15, 16, 7, 16},
  {"goldmont-plus", &slm_cost, 16, 15, 16, 7, 16},
  {"knl", &slm_cost, 16, 15, 16, 7, 16},
  {"knm", &slm_cost, 16, 15, 16, 7, 16},
  {"skylake", &skylake_cost, 16, 10, 16, 10, 16},
  {"skylake-avx512", &skylake_cost, 16, 10, 16, 10, 16},
  {"cannonlake", &skylake_cost, 16, 10, 16, 10, 16},
  {"icelake-client", &skylake_cost, 16, 10, 16, 10, 16},
  {"icelake-server", &skylake_cost, 16, 10, 16, 10, 16},
  {"intel", &intel_cost, 16, 15, 16, 7, 16},
  {"geode", &geode_cost, 0, 0, 0, 0, 0},
  {"k6", &k6_cost, 32, 7, 32, 7, 32},
  {"athlon", &athlon_cost, 16, 7, 16, 7, 16},
  {"k8", &k8_cost, 16, 7, 16, 7, 16},
  {"amdfam10", &amdfam10_cost, 32, 24, 32, 7, 32},
  {"bdver1", &bdver1_cost, 16, 10, 16, 7, 11},
  {"bdver2", &bdver2_cost, 16, 10, 16, 7, 11},
  {"bdver3", &bdver3_cost, 16, 10, 16, 7, 11},
  {"bdver4", &bdver4_cost, 16, 10, 16, 7, 11},
  {"btver1", &btver1_cost, 16, 10, 16, 7, 11},
  {"btver2", &btver2_cost, 16, 10, 16, 7, 11},
  {"znver1", &znver1_cost, 16, 15, 16, 15, 16}
"""

def get_new_alignment(alignment):
    if alignment == 0:
        return "NULL"
    elif

lines = cpus.strip().split('\n')

for l in lines:
    parts = [x.strip() for x in l[1:-1].split(',')]
    assert len(parts) == 7

    print(parts)
