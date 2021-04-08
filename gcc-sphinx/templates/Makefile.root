FOLDERS = cpp cppinternals gcc gccgo gccint gfortran libgomp libitm libquadmath install gfc-internals libiberty

default: html man latexpdf

.PHONY: html
html:
	for dir in $(FOLDERS); do $(MAKE) -C $$dir html; done

.PHONY: man
man:
	for dir in $(FOLDERS); do $(MAKE) -C $$dir man; done

.PHONY: latexpdf
latexpdf:
	for dir in $(FOLDERS); do $(MAKE) -C $$dir latexpdf; done
