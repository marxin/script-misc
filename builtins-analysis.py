#!/usr/bin/env python3

import os
import sys
import re
import itertools
import subprocess

all_libmath_functions = '''double sin (double x)
float sinf (float x)
long double sinl (long double x)
double cos (double x)
float cosf (float x)
long double cosl (long double x)
double tan (double x)
float tanf (float x)
long double tanl (long double x)
void sincos (double x, double *sinx, double *cosx)
void sincosf (float x, float *sinx, float *cosx)
void sincosl (long double x, long double *sinx, long double *cosx)
complex double csin (complex double z)
complex float csinf (complex float z)
complex long double csinl (complex long double z)
complex double ccos (complex double z)
complex float ccosf (complex float z)
complex long double ccosl (complex long double z)
complex double ctan (complex double z)
complex float ctanf (complex float z)
complex long double ctanl (complex long double z)
double asin (double x)
float asinf (float x)
long double asinl (long double x)
double acos (double x)
float acosf (float x)
long double acosl (long double x)
double atan (double x)
float atanf (float x)
long double atanl (long double x)
double atan2 (double y, double x)
float atan2f (float y, float x)
long double atan2l (long double y, long double x)
complex double casin (complex double z)
complex float casinf (complex float z)
complex long double casinl (complex long double z)
complex double cacos (complex double z)
complex float cacosf (complex float z)
complex long double cacosl (complex long double z)
complex double catan (complex double z)
complex float catanf (complex float z)
complex long double catanl (complex long double z)
double exp (double x)
float expf (float x)
long double expl (long double x)
double exp2 (double x)
float exp2f (float x)
long double exp2l (long double x)
double exp10 (double x)
float exp10f (float x)
long double exp10l (long double x)
double pow10 (double x)
float pow10f (float x)
long double pow10l (long double x)
double log (double x)
float logf (float x)
long double logl (long double x)
double log10 (double x)
float log10f (float x)
long double log10l (long double x)
double log2 (double x)
float log2f (float x)
long double log2l (long double x)
double logb (double x)
float logbf (float x)
long double logbl (long double x)
int ilogb (double x)
int ilogbf (float x)
int ilogbl (long double x)
double pow (double base, double power)
float powf (float base, float power)
long double powl (long double base, long double power)
double sqrt (double x)
float sqrtf (float x)
long double sqrtl (long double x)
double cbrt (double x)
float cbrtf (float x)
long double cbrtl (long double x)
double hypot (double x, double y)
float hypotf (float x, float y)
long double hypotl (long double x, long double y)
double expm1 (double x)
float expm1f (float x)
long double expm1l (long double x)
double log1p (double x)
float log1pf (float x)
long double log1pl (long double x)
complex double cexp (complex double z)
complex float cexpf (complex float z)
complex long double cexpl (complex long double z)
complex double clog (complex double z)
complex float clogf (complex float z)
complex long double clogl (complex long double z)
complex double clog10 (complex double z)
complex float clog10f (complex float z)
complex long double clog10l (complex long double z)
complex double csqrt (complex double z)
complex float csqrtf (complex float z)
complex long double csqrtl (complex long double z)
complex double cpow (complex double base, complex double power)
complex float cpowf (complex float base, complex float power)
complex long double cpowl (complex long double base, complex long double power)
double sinh (double x)
float sinhf (float x)
long double sinhl (long double x)
double cosh (double x)
float coshf (float x)
long double coshl (long double x)
double tanh (double x)
float tanhf (float x)
long double tanhl (long double x)
complex double csinh (complex double z)
complex float csinhf (complex float z)
complex long double csinhl (complex long double z)
complex double ccosh (complex double z)
complex float ccoshf (complex float z)
complex long double ccoshl (complex long double z)
complex double ctanh (complex double z)
complex float ctanhf (complex float z)
complex long double ctanhl (complex long double z)
double asinh (double x)
float asinhf (float x)
long double asinhl (long double x)
double acosh (double x)
float acoshf (float x)
long double acoshl (long double x)
double atanh (double x)
float atanhf (float x)
long double atanhl (long double x)
complex double casinh (complex double z)
complex float casinhf (complex float z)
complex long double casinhl (complex long double z)
complex double cacosh (complex double z)
complex float cacoshf (complex float z)
complex long double cacoshl (complex long double z)
complex double catanh (complex double z)
complex float catanhf (complex float z)
complex long double catanhl (complex long double z)
double erf (double x)
float erff (float x)
long double erfl (long double x)
double erfc (double x)
float erfcf (float x)
long double erfcl (long double x)
double lgamma (double x)
float lgammaf (float x)
long double lgammal (long double x)
double lgamma_r (double x, int *signp)
float lgammaf_r (float x, int *signp)
long double lgammal_r (long double x, int *signp)
double gamma (double x)
float gammaf (float x)
long double gammal (long double x)
double tgamma (double x)
float tgammaf (float x)
long double tgammal (long double x)
double j0 (double x)
float j0f (float x)
long double j0l (long double x)
double j1 (double x)
float j1f (float x)
long double j1l (long double x)
double jn (int n, double x)
float jnf (int n, float x)
long double jnl (int n, long double x)
double y0 (double x)
float y0f (float x)
long double y0l (long double x)
double y1 (double x)
float y1f (float x)
long double y1l (long double x)
double yn (int n, double x)
float ynf (int n, float x)
long double ynl (int n, long double x)'''.split('\n')

gcc_builtins = '''int __builtin_types_compatible_p (type1, type2)
type __builtin_call_with_static_chain (call_exp, pointer_exp)
type __builtin_choose_expr (const_exp, exp1, exp2)
type __builtin_complex (real, imag)
int __builtin_constant_p (exp)
long __builtin_expect (long exp, long c)
void __builtin_trap (void)
void __builtin_unreachable (void)
void * __builtin_assume_aligned (const void *exp, size_t align, ...)
int __builtin_LINE ()
const char * __builtin_FUNCTION ()
const char * __builtin_FILE ()
void __builtin___clear_cache (char *begin, char *end)
void __builtin_prefetch (const void *addr, ...)
double __builtin_huge_val (void)
float __builtin_huge_valf (void)
long double __builtin_huge_vall (void)
int __builtin_fpclassify (int, int, int, int, int, ...)
double __builtin_inf (void)
_Decimal32 __builtin_infd32 (void)
_Decimal64 __builtin_infd64 (void)
_Decimal128 __builtin_infd128 (void)
float __builtin_inff (void)
long double __builtin_infl (void)
int __builtin_isinf_sign (...)
double __builtin_nan (const char *str)
_Decimal32 __builtin_nand32 (const char *str)
_Decimal64 __builtin_nand64 (const char *str)
_Decimal128 __builtin_nand128 (const char *str)
float __builtin_nanf (const char *str)
long double __builtin_nanl (const char *str)
double __builtin_nans (const char *str)
float __builtin_nansf (const char *str)
long double __builtin_nansl (const char *str)
int __builtin_ffs (int x)
int __builtin_clz (unsigned int x)
int __builtin_ctz (unsigned int x)
int __builtin_clrsb (int x)
int __builtin_popcount (unsigned int x)
int __builtin_parity (unsigned int x)
int __builtin_ffsl (long)
int __builtin_clzl (unsigned long)
int __builtin_ctzl (unsigned long)
int __builtin_clrsbl (long)
int __builtin_popcountl (unsigned long)
int __builtin_parityl (unsigned long)
int __builtin_ffsll (long long)
int __builtin_clzll (unsigned long long)
int __builtin_ctzll (unsigned long long)
int __builtin_clrsbll (long long)
int __builtin_popcountll (unsigned long long)
int __builtin_parityll (unsigned long long)
double __builtin_powi (double, int)
float __builtin_powif (float, int)
long double __builtin_powil (long double, int)
uint16_t __builtin_bswap16 (uint16_t x)
uint32_t __builtin_bswap32 (uint32_t x)
uint64_t __builtin_bswap64 (uint64_t x)'''.split('\n')

def get_function_name(signature):
    return re.match('.* ([^ ]*) \(', signature).group(1)

gcc_builtins_cache = {}
for i in gcc_builtins:
    gcc_builtins_cache[get_function_name(i)] = i

libmath_names = set(map(get_function_name, all_libmath_functions))

solution_string = '''
_exit,_Exit,abort,exit,__builtin_trap,__builtin_unreachable:candidate for TRAP instruction
bcmp:legacy function (replaced by memcmp)
dcgettext,dgettext,fprintf_unlocked,fputs_unlocked,gettext,index,isascii,printf_unlocked,rindex,stpcpy,stpncpy,strcasecmp,strdup,strfmon,strncasecmp,strndup,toascii,isblank,iswblank,snprintf,vfscanf,vscanf,vsnprintf,vsscanf,iswalnum,iswalpha,iswcntrl,iswdigit,iswgraph,iswlower,iswprint,iswpunct,iswspace,iswupper,iswxdigit,towlower,towupper,fprintf,fputs,fscanf,isalnum,isalpha,iscntrl,isdigit,isgraph,islower,isprint,ispunct,isspace,isupper,isxdigit,tolower,toupper,printf,putchar,puts,scanf,snprintf,sprintf,sscanf,strcat,strchr,strcmp,strcpy,strcspn,strlen,strncat,strncmp,strncpy,strpbrk,strrchr,strspn,strstr,vfprintf,vprintf,vsprintf:string function
drem,dremf,signbit,signbitf,signbitd32,signbitd64,signbitd128,significandf,significand,imaxabs,llabs,llrintf,llrint,lroundf,lround,lrintf,lrint,lroundf,lround,llround,llroundf,nearbyintf,nearbyinti,nearbyint,scalblnf,scalbln,scalbnf,scalbn,memchr,memcmp,copysignf,__builtin_bswap16,__builtin_bswap32,__builtin_bswap64:candidate for HSAIL implementation
gamma,gammaf,gamma_r,gammaf_r,pow10,pow10f,__builtin_powi,__builtin_powif,lgamma,lgammaf,lgammal_r,gammal_r,nexttowardf,nexttoward,cproj,cprojf:HSAIL math library
j0,j0f,j1,j1f,f1,f1f,jn,jnf,y0,y0f,y1,y1f,yn,ynf:HSAIL math library (Bessel function)
lgammaf_r:probably alias of lgamma_rf
scalb,scalbf:Obsolete function.
calloc,malloc:dynamic memory allocation
clog10,clog10f,clog,clogf:HSAIL math library (complex function)
cabs,cabsf,carg,cargf,conj,conjf:complex function, candidate
__builtin_types_compatible_p,__builtin_call_with_static_chain,__builtin_choose_expr,__builtin_constant_p,__builtin_expect,__builtin_assume_aligned,__builtin_LINE,__builtin_FUNCTION,__builtin_FILE,__builtin___clear_cache:math not-related builtin
__builtin_fpclassify,__builtin_isinf_sign:floating-point clasification macro
__builtin_prefetch:Can HSA support that?
'''

solution = {}
for line in solution_string.strip().split('\n'):
    parts = line.split(':')
    for f in parts[0].split(','):
        solution[f] = parts[1]

categories = ['Outside ISO C', 'ISO C99', 'ISO C99 cont.', 'ISO C94', 'ISO C90', 'ISO C99 reserved', 'GCC builtins']
functions = []

functions.append(["_exit", "alloca", "bcmp", "bzero", "dcgettext", "dgettext", "dremf", "dreml", "drem", "exp10f", "exp10l", "exp10", "ffsll", "ffsl", "ffs", "fprintf_unlocked", "fputs_unlocked", "gammaf", "gammal", "gamma", "gammaf_r", "gammal_r", "gamma_r", "gettext", "index", "isascii", "j0f", "j0l", "j0", "j1f", "j1l", "j1", "jnf", "jnl", "jn", "lgammaf_r", "lgammal_r", "lgamma_r", "mempcpy", "pow10f", "pow10l", "pow10", "printf_unlocked", "rindex", "scalbf", "scalbl", "scalb", "signbit", "signbitf", "signbitl", "signbitd32", "signbitd64", "signbitd128", "significandf", "significandl", "significand", "sincosf", "sincosl", "sincos", "stpcpy", "stpncpy", "strcasecmp", "strdup", "strfmon", "strncasecmp", "strndup", "toascii", "y0f", "y0l", "y0", "y1f", "y1l", "y1", "ynf", "ynl", "yn"])
functions.append(["_Exit", "acoshf", "acoshl", "acosh", "asinhf", "asinhl", "asinh", "atanhf", "atanhl", "atanh", "cabsf", "cabsl", "cabs", "cacosf", "cacoshf", "cacoshl", "cacosh", "cacosl", "cacos", "cargf", "cargl", "carg", "casinf", "casinhf", "casinhl", "casinh", "casinl", "casin", "catanf", "catanhf", "catanhl", "catanh", "catanl", "catan", "cbrtf", "cbrtl", "cbrt", "ccosf", "ccoshf", "ccoshl", "ccosh", "ccosl", "ccos", "cexpf", "cexpl", "cexp", "cimagf", "cimagl", "cimag", "clogf", "clogl", "clog", "conjf", "conjl", "conj", "copysignf", "copysignl", "copysign", "cpowf", "cpowl", "cpow", "cprojf", "cprojl", "cproj", "crealf", "creall", "creal", "csinf", "csinhf", "csinhl", "csinh", "csinl", "csin", "csqrtf", "csqrtl", "csqrt", "ctanf", "ctanhf", "ctanhl", "ctanh", "ctanl", "ctan", "erfcf", "erfcl", "erfc", "erff", "erfl", "erf", "exp2f", "exp2l", "exp2", "expm1f", "expm1l", "expm1", "fdimf", "fdiml", "fdim", "fmaf", "fmal", "fmaxf", "fmaxl", "fmax", "fma", "fminf", "fminl", "fmin", "hypotf", "hypotl", "hypot", "ilogbf", "ilogbl", "ilogb", "imaxabs", "isblank", "iswblank", "lgammaf", "lgammal", "lgamma", "llabs", "llrintf", "llrintl", "llrint", "llroundf", "llroundl", "llround", "log1pf", "log1pl", "log1p", "log2f", "log2l", "log2", "logbf", "logbl", "logb", "lrintf", "lrintl", "lrint", "lroundf", "lroundl", "lround", "nearbyintf", "nearbyintl", "nearbyint", "nextafterf", "nextafterl", "nextafter", "nexttowardf", "nexttowardl", "nexttoward", "remainderf", "remainderl", "remainder", "remquof", "remquol", "remquo", "rintf", "rintl", "rint", "roundf", "roundl", "round", "scalblnf", "scalblnl", "scalbln", "scalbnf", "scalbnl", "scalbn", "snprintf", "tgammaf", "tgammal", "tgamma", "truncf", "truncl", "trunc", "vfscanf", "vscanf", "vsnprintf", "vsscanf"])
functions.append(["acosf", "acosl", "asinf", "asinl", "atan2f", "atan2l", "atanf", "atanl", "ceilf", "ceill", "cosf", "coshf", "coshl", "cosl", "expf", "expl", "fabsf", "fabsl", "floorf", "floorl", "fmodf", "fmodl", "frexpf", "frexpl", "ldexpf", "ldexpl", "log10f", "log10l", "logf", "logl", "modfl", "modf", "powf", "powl", "sinf", "sinhf", "sinhl", "sinl", "sqrtf", "sqrtl", "tanf", "tanhf", "tanhl", "tanl"])
functions.append(["iswalnum", "iswalpha", "iswcntrl", "iswdigit", "iswgraph", "iswlower", "iswprint", "iswpunct", "iswspace", "iswupper", "iswxdigit", "towlower", "towupper"])
functions.append(["abort", "abs", "acos", "asin", "atan2", "atan", "calloc", "ceil", "cosh", "cos", "exit", "exp", "fabs", "floor", "fmod", "fprintf", "fputs", "frexp", "fscanf", "isalnum", "isalpha", "iscntrl", "isdigit", "isgraph", "islower", "isprint", "ispunct", "isspace", "isupper", "isxdigit", "tolower", "toupper", "labs", "ldexp", "log10", "log", "malloc", "memchr", "memcmp", "memcpy", "memset", "modf", "pow", "printf", "putchar", "puts", "scanf", "sinh", "sin", "snprintf", "sprintf", "sqrt", "sscanf", "strcat", "strchr", "strcmp", "strcpy", "strcspn", "strlen", "strncat", "strncmp", "strncpy", "strpbrk", "strrchr", "strspn", "strstr", "tanh", "tan", "vfprintf", "vprintf", "vsprintf"])
functions.append(["clog10", "clog10f", "clog10l"])
functions.append(list(map(get_function_name, gcc_builtins)))

all_gcc_functions = set(itertools.chain(*functions))

# make sure we have all libmath functions covered
assert (len(libmath_names - all_gcc_functions) == 0)

native_implementations = set(['alloca', 'ceil', 'floor', 'rint', 'sqrt', 'trunc', 'clrsb', 'clz', 'ctz', 'ffs', 'ffsl', 'ffsll', 'parity', 'popcout', 'creal', 'crealf', 'cimag', 'cimagf', 'abs', 'labs', 'memset', 'bzero', 'memcpy', 'mempcpy', '__builtin_complex'])

native_implementations |= set('''__builtin_clrsb
__builtin_clrsbl
__builtin_clrsbll
__builtin_clz
__builtin_clzl
__builtin_clzll
__builtin_ctz
__builtin_ctzl
__builtin_ctzll
__builtin_ffs
__builtin_ffsl
__builtin_ffsll
__builtin_parity
__builtin_parityl
__builtin_parityll
__builtin_popcount
__builtin_popcountl
__builtin_popcountll
__builtin_memcpy
__builtin_memset
__builtin_alloca
__builtin_alloca_with_align'''.split('\n'))


semi_native_implementations = set(['cos', 'exp2', 'log2', 'sin'])

FNULL = open(os.devnull, 'w')

def parse_signature(signature):
    signature = signature.strip().strip(';')
    parts = signature.split('(')
    assert len(parts) == 2
    left = parts[0].strip()
    right = parts[1].strip().rstrip(')')
    x = left.rfind(' ')
    name = left[x:].strip()
    rettype = left[:x]

    arguments = []
    for a in right.split(','):
        a = a.strip()
        l = max(a.rfind('*'), a.rfind(' '))
        if l == -1:
            return None
        arguments.append(a[:(l+1)].strip())

    if name[0] == '*':
        name = name[1:]
        rettype += ' *'

    return(name, rettype, arguments)

def process_man(func):
    description = '' 
    signature = ''

    try:
        result = subprocess.check_output(['man', '3', func], stderr = FNULL)
        lines = result.decode('utf-8').split('\n')
        in_name = False
        for l in lines:
            l = l.strip()
            if l == 'NAME':
                in_name = True
            elif in_name and '-' in l:
                description = l.split('-')[-1].strip()
                break

        in_synopsis = False
        last_line = ''
        for l in lines:
            l = l.strip()
            sl = last_line + l
            if l == 'SYNOPSIS':
                in_synopsis = True
            elif func + '(' in l and l.endswith(';'):
                signature = l
                break
            elif func + ' (' in l and l.endswith(';'):
                signature = l
                break
            elif func + '(' in sl and sl.endswith(';'):
                signature = sl
                break
            elif func + ' (' in sl and sl.endswith(';'):
                signature = sl
                break
            elif l == 'DESCRIPTION':
                break
            last_line = l
    except subprocess.CalledProcessError as e:
       pass 

    return [description, signature.strip(';')]

class HSAFunc:
    def __init__(self, name, iso_category, signature, hsa_implementation, description, suggestion):
        self.name = name
        self.iso_category = iso_category
        self.signature = signature
        self.hsa_implementation = hsa_implementation
        self.description = description
        self.suggestion = suggestion

        if signature != '':
            self.parsed_signature = parse_signature(self.signature)

    def csv(self):
        return ';'.join([self.name, self.iso_category, self.signature, self.hsa_implementation, self.description, self.suggestion])

    def __repr__(self):
        return self.signature

    def create_test(self, test_values, supported_rettypes):
        sign = self.parsed_signature
        if sign == None:
            return None
        e = False
        for arg in sign[2]:
            if not arg in test_values:
                print('Missing: "%s"' % arg, file = sys.stderr)
                e = True

        if sign[1] == 'void' or sign[1] == 'const void':
            pass
        else:
            if not sign[1] in supported_rettypes:
                print('Missing return type: "%s"' % sign[1], file = sys.stderr)
                return None

        if e:
            return None

        s = sign[0] + '('
        for (i, arg) in enumerate(sign[2]):
            s += 'arg_%s' % arg.replace(' ', '_')
            if i != len(sign[2]) - 1:
                s += ', '
        s += ');'

        return s

if len(sys.argv) <= 1:
    print('usage: builtins-analysis [libhsamath.hsail]')
    exit(-1)

existing = set()
for line in filter(lambda x: x.strip().startswith('decl prog function'), open(sys.argv[1]).readlines()):
    m = re.match('decl prog function.*&([^\(]*).*', line)
    existing.add(m.group(1))

# Create all HSA functions
hsa_functions = []

for (i, category) in enumerate(functions):
    for func in category:
        hsa_impl = ''
        suggestion = ''
        if func in native_implementations:
            hsa_impl = 'native insn implementation'
        elif func in semi_native_implementations:
            hsa_impl = 'semi-native insn implementation'
        elif func in existing:
            hsa_impl = 'HSAIL math library implementation'
        elif func.endswith('l') and func[:-1] in all_gcc_functions:
            hsa_impl = 'long double (not supported)'

        m = process_man(func)
        signature = m[1]
        description = m[0]

        if func in solution:
            suggestion = solution[func]
        elif func.startswith('c') and description.startswith('complex '):
            suggestion = 'HSAIL math library (complex function)'
        elif func.startswith('__builtin_nan') or func.startswith('__builtin_huge_val'):
            suggestion = 'compile time constant'
        elif func.startswith('__builtin_inf'):
            suggestion = 'inf compile time constant.'

        if signature == '' and func in gcc_builtins_cache:
            signature = gcc_builtins_cache[func]

        hsa_functions.append(HSAFunc(func, categories[i], signature, hsa_impl, description, suggestion))

integer_value = '2345'
test_arguments = {}
test_arguments['int'] = integer_value
test_arguments['unsigned int'] = integer_value
test_arguments['unsigned'] = integer_value
test_arguments['unsigned long'] = integer_value
test_arguments['long'] = integer_value
test_arguments['long int'] = integer_value
test_arguments['long long int'] = integer_value
test_arguments['size_t'] = integer_value
test_arguments['float'] = '2.45f'
test_arguments['double'] = '16.44'
test_arguments['float complex'] = '1.2f + 3.2f * I'
test_arguments['double complex'] = '1.2 + 3.2 * I'

supported_rettypes = {}
supported_rettypes['float'] = 'f'
supported_rettypes['double'] = 'f'
supported_rettypes['int'] = 'd'
supported_rettypes['long int'] = 'ld'
supported_rettypes['void *'] = 'p'

display = hsa_functions

if len(sys.argv) <= 2:
    display = sorted(filter(lambda x: x.hsa_implementation == '', hsa_functions), key = lambda x: x.suggestion)

c = 1
retvar_dict = {}
retvars = []
declarations = []
body = []
func_dict = {}
arguments = {}

for (i, func) in enumerate(filter(lambda x: x.hsa_implementation != '' and not 'not supported' in x.hsa_implementation, hsa_functions)):
    r = func.create_test(test_arguments, supported_rettypes)
    if r != None:
        body.append('// test %d: %s' % (c, func.name))
        retvar = None
        retvar_type = func.parsed_signature[1]
        if retvar_type != 'void':
            retvar = 'return_value_%d' % c
            retvar_dict[retvar] = supported_rettypes[retvar_type]
            retvars.append(retvar)
            func_dict[retvar] = func
            declarations.append('%s %s;' % (retvar_type, retvar))
            body.append('%s = %s' % (retvar, r))
            arguments[retvar] = r
        else:
            body.append(r)

        c += 1

print('#define _GNU_SOURCE')
print('#include <math.h>')
print('#include <complex.h>')
print('#include <stdio.h>')
print('#include <string.h>')
print('#include <stdlib.h>')
print('#include <alloca.h>')

print('int main() {')

inputs = {}
for t in test_arguments:
    n = 'arg_%s' % t.replace(' ', '_')
    inputs[t] = n
    print('%s %s = %s;' % (t, n, test_arguments[t]))

print('\n'.join(declarations))

print('#pragma omp target map(tofrom:%s,%s)\n{' % (','.join(inputs.values()), ','.join(retvars)))
print('\n'.join(body))
print('}')

for retvar in retvars:
    print('printf ("%s (%s) = %%%s\\n", %s);' % (retvar, func_dict[retvar].name, retvar_dict[retvar], retvar))

print('return 0;}')
exit(1)


print('Function name;Category;Signature;HSA implementation;MAN page description;Suggestion')
for func in display:
    print(func.csv())

print('')
print('HSAIL math library fns')

for f in sorted(existing-all_gcc_functions):
    print(f)
