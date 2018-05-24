#!/usr/bin/env python3

import re

class Option:
    def __init__(self, name, option_string, description):
        self.name = name
        self.option_string = option_string
        self.description = description
        self.options = {}

        self.parse_options()

    def parse_options(self):
        s = self.option_string

        while s != '':
            m = re.search('^(\w+)\(([^)]*)\)', s)
            if m != None:
                s = s[m.span(0)[1]:].strip()
                self.options[m.group(1)] = m.group(2)
            else:
                m2 = re.search('^[^\ ]*', s)
                s = s[m2.span(0)[1]:].strip()
                self.options[m2.group(0)] = None

    def flag_set_p(self, flag):
        return flag in self.options

    def get(self, key):
        return self.options[key]

    def get_c_type(self):
        if self.flag_set_p('UInteger'):
            return 'int'
        elif self.flag_set_p('Enum'):
            return 'enum'
        elif not self.flag_set_p('Joined') and not self.flag_set_p('Separate'):
            if self.flag_set_p('Mask'):
                if self.flag_set_p('HOST_WIDE_INT'):
                    return 'HOST_WIDE_INT'
                else:
                    return 'int'
            else:
                return 'signed char'
        else:
            return 'const char *'

    def get_c_type_size(self):
        type = self.get_c_type()
        if type == 'const char *' or type == 'HOST_WIDE_INT':
            return 8
        elif type == 'enum' or type == 'int':
            return 4
        elif type == 'signed char':
            return 1
        else:
            assert False

    def get_variable_name(self):
        name = self.get('Var')
        return name.split(',')[0]

    def get_full_c_type(self):
        t = self.get_c_type()
        if t == 'enum':
            return 'enum %s' % self.get('Enum')

    def generate_assignment(self, printer, lhs, rhs):
        name = self.get_variable_name()
        printer.print('%s->x_%s = %s->x_%s;' % (lhs, name, rhs, name), 2)

    def get_printf_format(self):
        t = self.get_c_type()
        return '%#x' if t != 'const char *' else '%s'

    def generate_print(self, printer):
        name = self.get_variable_name()
        format = self.get_printf_format() 
        printer.print('if (ptr->x_%s)' % name, 2)
        printer.print('fprintf (file, "%*s%s (' + format + ')\\n", indent_to, "", "' + name + '", ptr->x_' + name + ');', 4)

    def generate_print_diff(self, printer):
        name = self.get_variable_name()
        format = self.get_printf_format() 
        printer.print('if (ptr1->x_%s != ptr2->x_%s)' % (name, name), 2)
        printer.print('fprintf (file, "%*s%s (' + format + '/' + format + ')\\n", indent_to, "", "' + name + '", ptr1->x_' + name + ', ptr2->x_' + name +  ');', 4)

    def generate_hash(self, printer):
        t = self.get_c_type()
        name = self.get_variable_name()
        v = 'ptr->x_' + name
        if t == 'const char *':
            printer.print('if (%s)' % v, 2)
            printer.print('hstate.add (%s, strlen (%s));' % (v, v), 4)
            printer.print('else', 2)
            printer.print('hstate.add_int (0);', 4)
        else:
            printer.print('hstate.add_hwi (%s);' % v, 2)

    def generate_stream_out(self, printer):
        t = self.get_c_type()
        name = self.get_variable_name()
        v = 'ptr->x_' + name
        if t == 'const char *':
            printer.print('bp_pack_string (ob, bp, %s, true);' % v, 2)
        else:
            printer.print('bp_pack_value (bp, %s, 64);' % v, 2)

    def generate_stream_in(self, printer):
        t = self.get_c_type()
        name = self.get_variable_name()
        v = 'ptr->x_' + name
        if t == 'const char *':
            printer.print('%s = bp_unpack_string (data_in, bp);' % v, 2)
            printer.print('if (%s)' % v, 2)
            printer.print('%s = xstrdup (%s);' % (v, v), 4)
        else:
            cast = '' if t != 'enum' else '(%s)' % self.get_full_c_type()
            printer.print('%s = %sbp_unpack_value (bp, 64);' % (v, cast), 2)

    def print(self):
        print('%s:%s:%s' % (self.name, self.options, self.description))

class Printer:
    def print_function_header(self, comment, return_type, name, args):
        print('/* %s */' % comment)
        print(return_type)
        print('%s (%s)' % (name, ', '.join(args)))
        print('{')

    def print_function_footer(self):
        print('}\n')

    def print(self, s, indent):
        print(' ' * indent + s)

delimiter = u'\x1c'

printer = Printer()

# parse content of optionlist
lines = [line.strip() for line in open('/home/marxin/Programming/gcc/objdir/gcc/optionlist').readlines()]
flags = []
for l in lines:
    parts = l.split(delimiter)

    description = None
    if len(parts) > 2:
        description = ' '.join(parts[2:])

    name = parts[0]
    ignored = set(['Language', 'TargetSave', 'Variable', 'TargetVariable', 'HeaderInclude', 'SourceInclude', 'Enum', 'EnumValue'])

    if not name in ignored:
        flags.append(Option(name, parts[1], description))

optimization_flags = [f for f in flags if (f.flag_set_p('Optimization') or f.flag_set_p('PerFunction')) and f.flag_set_p('Var')]
optimization_flags = sorted(optimization_flags, key = lambda x: (x.get_c_type_size(), x.get_c_type()), reverse = True)

# start printing
printer.print_function_header('Save optimization variables into a structure.',
        'void', 'cl_optimization_save', ['cl_optimization *ptr, gcc_options *opts'])
for f in optimization_flags:
    f.generate_assignment(printer, 'ptr', 'opts')
printer.print_function_footer()

printer.print_function_header('Restore optimization options from a structure.',
        'void', 'cl_optimization_restore', ['gcc_options *opts', 'cl_optimization *ptr'])
for f in optimization_flags:
    f.generate_assignment(printer, 'opts', 'ptr')
printer.print('targetm.override_options_after_change ();', 2)
printer.print_function_footer()

printer.print_function_header('Print optimization options from a structure.',
        'void', 'cl_optimization_print', ['FILE *file', 'int indent_to', 'cl_optimization *ptr'])
printer.print('fputs ("\\n", file);', 2)
for f in optimization_flags:
    f.generate_print(printer)
printer.print_function_footer()

printer.print_function_header('Print different optimization variables from structures provided as arguments.',
        'void', 'cl_optimization_print_diff', ['FILE *file', 'int indent_to', 'cl_optimization *ptr1', 'cl_optimization *ptr2'])
for f in optimization_flags:
    f.generate_print_diff(printer)
printer.print_function_footer()

optimization_flags = list(filter(lambda x: x.flag_set_p('Optimization'), optimization_flags))

printer.print_function_header('Hash optimization options.',
        'hashval_t', 'cl_optimization_hash', ['cl_optimization const *ptr'])
printer.print('inchash::hash hstate;', 2)
for f in optimization_flags:
    f.generate_hash(printer)
printer.print('return hstate.end();', 2)
printer.print_function_footer()

printer.print_function_header('Stream out optimization options.',
        'void', 'cl_optimization_stream_out', ['output_block *ob', 'bitpack_d *bp', 'cl_optimization *ptr'])
for f in optimization_flags:
    f.generate_stream_out(printer)
printer.print_function_footer()

printer.print_function_header('Stream in optimization options.',
        'void', 'cl_optimization_stream_in', ['data_in *data_in', 'bitpack_d *bp', 'cl_optimization *ptr'])
for f in optimization_flags:
    f.generate_stream_in(printer)
printer.print_function_footer()
