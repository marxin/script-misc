#!/usr/bin/env python3

import concurrent.futures
import time

import requests


ATTEMPTS = 10

FILES = """
fc3aabdc5a83a2161eed2fe70edc3acc7aeeaefd /usr/bin/mgrtopbm
ceaee814709b36837f6f9b03c29bccc0db636dc2 /usr/bin/midi2xml
d39ca195311416d50bf5c3a78c12c0ba53d4df8f /usr/bin/migratepages
938cdb14656c58125523c868a7e4e02acde4ecc3 /usr/bin/migspeed
59f778c32ddd56069cab09a0d1270a920bfe2037 /usr/bin/mime
1672b711e600552aa194125f03978595d41a390f /usr/bin/mimelang
274c9e589c2db6a054725274d7a3e96368d5a021 /usr/bin/mimeview
cf47d58ff9ec66a604763cb191c2ce61d93eaa79 /usr/bin/mips-suse-linux-addr2line
478c59c733e5f2418a3138c49069d9e580659f7e /usr/bin/mips-suse-linux-ar
9f61d00a69fbffeaff2e04eb929d4e22012241d7 /usr/bin/mips-suse-linux-as
642c80a7213f4bfa0f6091d16d277c5a970f042c /usr/bin/mips-suse-linux-c++-11
9a94328c0457a8806b903852d50b3c7bc553fe04 /usr/bin/mips-suse-linux-c++-12
c472a7dc9e9fccd368f41b8ffc93a9d84234bde7 /usr/bin/mips-suse-linux-cpp-11
260f2d6c837082c7121b69ac4e7b80fffcc43e35 /usr/bin/mips-suse-linux-cpp-12
e8d722ec849ac6ccc213cd0b122167b59b9c0bba /usr/bin/mips-suse-linux-elfedit
642c80a7213f4bfa0f6091d16d277c5a970f042c /usr/bin/mips-suse-linux-g++-11
9a94328c0457a8806b903852d50b3c7bc553fe04 /usr/bin/mips-suse-linux-g++-12
caa43c94e3469bd4f2958c515b5293e12d858a58 /usr/bin/mips-suse-linux-gcc-11
aa38989b3aabd14f2d0baa10d470b2c747d0609b /usr/bin/mips-suse-linux-gcc-12
a1e594d20bc4f6ca54e1d3a81c45dd45809c2820 /usr/bin/mips-suse-linux-gcc-ar-11
c04c352bcac81b5d1f8d6ee11c4f090d955548ea /usr/bin/mips-suse-linux-gcc-ar-12
3a72f6ba2fdfa02b135b45a36e627adda78a8a00 /usr/bin/mips-suse-linux-gcc-nm-11
793c252846ba2ee0a1ea1121c44d5a4cb5fe70b3 /usr/bin/mips-suse-linux-gcc-nm-12
c77a9ea5c88bbedb53ebd42092de981c5b0350cc /usr/bin/mips-suse-linux-gcc-ranlib-11
ee4b12cef0e3570528194753db2c48ee4b82ff4f /usr/bin/mips-suse-linux-gcc-ranlib-12
ba5aed942159a113fb4bcac82e78b84657b95281 /usr/bin/mips-suse-linux-gcov-11
3dc12ad9216dee6a8d4fd52dcdb8dcd847cb7878 /usr/bin/mips-suse-linux-gcov-12
c7ff124c7430b55b9bf0dfa54ea4bf0364367c1d /usr/bin/mips-suse-linux-gcov-dump-11
eeedf78690c7ce27824cf2a950c31a604ca9c250 /usr/bin/mips-suse-linux-gcov-dump-12
c27bb17aa7283c04b9fd7a9a63cc0b5ca977c1e1 /usr/bin/mips-suse-linux-gcov-tool-11
0f3efec928281232c7500cdc0660976246b421b0 /usr/bin/mips-suse-linux-gcov-tool-12
68ad989cf674d992c1a6ca8ce477b013ae1f5d67 /usr/bin/mips-suse-linux-gprof
c6e185127255740eff36c427347b994875e8d787 /usr/bin/mips-suse-linux-ld
c6e185127255740eff36c427347b994875e8d787 /usr/bin/mips-suse-linux-ld.bfd
c98848d2dd0cac895e3b90fcab1cbe147691b540 /usr/bin/mips-suse-linux-nm
c0894a2a27163afbeb31bab5c33904149f1eacdc /usr/bin/mips-suse-linux-objcopy
992d0d4b8eddffc18cb283937ec424256fcaae4d /usr/bin/mips-suse-linux-objdump
ed1adbc744974f38fa7906b256671143062b0f78 /usr/bin/mips-suse-linux-ranlib
5d9a67ab23a8e1f4347f60b1b206ed3328ef5272 /usr/bin/mips-suse-linux-readelf
eb54ae613abae5f7710a28d83a7bf9081d9983f0 /usr/bin/mips-suse-linux-size
c5daf674c20f8f6c7a881ca7b40bcdbc55fc873c /usr/bin/mips-suse-linux-strings
15a5072e0ac13cdade30b390fa57ec2b9b8edd7e /usr/bin/mips-suse-linux-strip
99b1fea6db00e2b7f3a87c9a6f1cbd28e030c948 /usr/bin/mjpeg_simd_helper
d30ac47a6c54d8c0748c122e6c3a216c6aba9502 /usr/bin/mka64ins
f45e25e85fe48b4729f7935b9809357c2a85006f /usr/bin/mkarmins
ff1a1390233a9c698337186b65ed67ca6f0bdd50 /usr/bin/mkbitmap
e42bf1e760a30b0166fd3ca3d9f13985aea3fbb3 /usr/bin/mkdir
929d83693f513cefd1c38e5075f2b10b12a9f322 /usr/bin/mkfifo
d9c953fe181623f8a21da531a4c3563d630ff72f /usr/bin/mkfontscale
555c1b49f9e08bd5d8567af28756966ecdf86a54 /usr/bin/mkinsadd
8f05099425d09e99f876a1f365290a84620b70cd /usr/bin/mkisofs
aa144a9c93f87972b44dc19c21bafb1ddb12aeee /usr/bin/mkmanifest
51e90de5e6f11aba1c4bb0bd617e4c246e7155dd /usr/bin/mknod
7514f9fc35fe739df688293ca0e1a5e4feb84738 /usr/bin/mksh
7a1c85fb366e5e1a04391c5d6e4743a2b6391f08 /usr/bin/mksquashfs
2b8ac5b4259bbec9cf0d8a3def8aacc78a4362ba /usr/bin/mktemp
54ca386e3421548531a657b7dc35599a4857a295 /usr/bin/mkx86ins
307490fbd3e86f6db4dec7a9a11775a02d09054f /usr/bin/mkzftree
49a0321740cb71bb0b6314bd251837f5b9f07bcd /usr/bin/mm2gv
9794cc263d9a81759d915083a4abbc5262a4644c /usr/bin/mmafm
5597a05bc99c763236286673b9da394163bc9428 /usr/bin/mmcli
8555d0581d2c9308f01bc6458200c971a6a3ea52 /usr/bin/mmdbresolve
306a4f24d99235407613a6be442c166cd8864aff /usr/bin/mmencode
626d92530132cfdea6d2b1604898515981aafc52 /usr/bin/mmpfb
e197b70c6bb86ae3d0aad067b426b3723deae3eb /usr/bin/mode2
dfc1a9c3626e4e63fa0a41c6c32b175582cdbe57 /usr/bin/modularize-11.0.1
4a241e0e47652ca295f0935f28795c1c058ee480 /usr/bin/modularize-12.0.1
85c7f6aefc19fa394a8c0d2fb8febbecd67b714a /usr/bin/modularize-13.0.1
59b9903ed4ca56361db4c2f3c42aa0ad60167a6c /usr/bin/modularize-14.0.6
b77f4f6ac0f31f0fecf3e32b951337ee7e11188e /usr/bin/modutil
c9c8b391617dfedd7027a44061ba449ab57e7c5d /usr/bin/mokutil
888f9ebc9ac4e3e7433ea3a94369d7f9e02941c0 /usr/bin/monitor-sensor
2f28250f149d88ac85e05ff2c6705a66210c8820 /usr/bin/mono-boehm
0f08e803f96d8cd91761d7f0eab6495a19d7c528 /usr/bin/mono-hang-watchdog
7b410fdf9190350b6ca86441fd7d6f2b5c138424 /usr/bin/mono-sgen
f37a60987ea7bfa7ed042b806f7b85781d69c2b0 /usr/bin/monodis
22967a860a1a564e7350b39e0a26e083f61ae9e5 /usr/bin/more
6aed6a41b71fc01b7562c5fe2fd660c87b71403b /usr/bin/mosh-client
fd8e0eeff47d3f6f4412dfaea9e59116d1e17909 /usr/bin/mosh-server
57a24470067374205e1b3b2053348901e3822fbc /usr/bin/mount
3596a337a868f788ef680cc46723ab8bc9110528 /usr/bin/mountpoint
b59259f2b0520dd5613d1ed83a6cb7efabb363ef /usr/bin/mouse-test
5d0ac41cee50d94bef0b9bfb2ff8f9aa3c50c0ff /usr/bin/mousetweaks
c2d7f1fef9d006dabcf2ed255cb8efcd4d64740b /usr/bin/movemail
61194f354ebd13dbf5f578717c9d63c11ff70576 /usr/bin/mp2enc
975de4cf8c50d3a1cc8587d214b9e36d00c5a181 /usr/bin/mpeg2enc
c5890de66037f26e5cff3eb23e158035affcad43 /usr/bin/mpicalc
4ed27c779fe387377339cd85267eec1af5f675ce /usr/bin/mplex
2efdb2ad5a44cbe42923dc4a5e2fc6c5305bb120 /usr/bin/mpost
bb07b6bf1b6c02a1628fecce6433a64997968bb2 /usr/bin/mppcheck
9a4783c4d405ec22bb79f17d2b8615b508804fe5 /usr/bin/mpplu
6088fc71dd5cbb2bb5f9692c4be8c8a541c7a517 /usr/bin/mppprof
f630a410f03148d9955d8559a8f8188eb619320b /usr/bin/mpris-proxy
ef855705ec058cffb299de9c7e7c474b6e54c24b /usr/bin/mprof-report
950b27eb5a3287f61fd7c4fc06cec79e4812b5a2 /usr/bin/mpt-status
"""


def get_debuginfo(binary, buildid):
    url = f'https://debuginfod.opensuse.org/buildid/{buildid}/debuginfo'

    for i in range(ATTEMPTS):
        response = requests.get(url)
        if response.status_code != 200 or i != 0:
            print(f'Attemp #{i}', binary, buildid, response)
            time.sleep(1)
        if response.status_code == 200:
            return


with concurrent.futures.ProcessPoolExecutor(max_workers=8) as executor:
    futures = []
    for buildid, binary in [x.split() for x in FILES.strip().splitlines()]:
        futures.append(executor.submit(get_debuginfo, binary, buildid))
    concurrent.futures.wait(futures)
    for future in futures:
        future.result()
