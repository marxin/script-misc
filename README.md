The repository contains simple linux scripts mainly written in Python.

List of scripts:

+ function_generator - generates random source code having foo functions that are called from main and each other
+ gcc-reorder-runner.sh - wrapper running batch of gcc binaries (function reorder specific)
+ readelf_sections - wrapper that will print all sections presented in ELF binary, display modes: none|latex|padded
+ readelf_relocs - prints for each relocation type number of relocations
+ ldd_informer - shows all dependencies of executable including size of all shared libraries
+ readpage_graph - creates a graph from stap dump and binary file; all important ELF sections are highlighted
+ stap_readpage.stp - STAP script file printing all ext4 disc reads done by kernel
+ readelf_sorted_symbols - prints symbols from ELF in binary layout order
+ symbol_section_finder - reads a set of object files and find corresponding sections for given list of functions
+ gcc-function-reorder - script compares all symbols met by compiler, if all occure in correct order according to dump
+ spec_statistics - script being to parse spec results and arrange them to latex table style
+ vmstat_parser - loads CPU utilization and memory usage from vmstat output; matplotlib is used for graph visualization
+ function_call_stats - temporary script for function call statistics aggregation
+ filter_lists - given a file to filter and a file with lines that should be filtered, print all these lines
+ icf_parser - ICF to IPA sem equality function equality comparer
+ aimx_parser - AIMX benchmark result parser
+ spec_parser - SPEC result parser
+ spec_batch_runner - runs a set of SPEC tests and collects statistics
+ spec_speed_size_graph - matplotlib graph generator for a single SPEC benchmark
+ stap_run - uses systemtap script to monitor disk access to binary and creates graph with readpage_graph script
+ system_top - utilizes vmstat and free commands to get used memory and CPU (including lto1 in WPA and LTRANS phases)
+ gentoo_parse_packages - parses a list of packages (with topic) and generates emerge command
+ binaries_walker - goes through all shared libraries and ELF executables and presents stats about size of files
