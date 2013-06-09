The repository contains simple linux scripts mainly written in Python.

List of scripts:

+ function_generator - generates random source code having foo functions that are called from main and each other
+ gcc-reorder-runner.sh - wrapper running batch of gcc binaries (function reorder specific)
+ readelf_sections - wrapper that will print all sections presented in ELF binary, display modes: none|latex|padded
+ readelf_relocs - prints for each relocation type number of relocations
+ ldd_informer - shows all dependencies of executable including size of all shared libraries
+ readpage_graph - creates a graph from stap dump and binary file; all important ELF sections are highlighted
