#!/bin/sh
# Usage: $0 package-dir opt-name

if test -z "$1" -o -z "$2"; then
  echo Usage: $0 gcc-branch package-dir
  exit 1
fi

package=gcc
toplevel=$1
packagedir=$2
if ! test -e .git; then
  echo "Need to run inside git working copy"
  exit 1;
fi
git fetch || exit 1
git rev-parse $toplevel || exit 1
rev=`git rev-parse $toplevel`

v=`git show $rev:gcc/BASE-VER`

# use the count from git gcc-descr with 13+
if test "`echo $v | cut -d '.' -f 1`" -ge "13"; then
  r=`git gcc-descr $toplevel | sed -e 's/.*-\([0-9]*\)-.*/\1/'`
else
  # use gcc-BASE-VER+r<number of commits on the branch>
  r=`git rev-list --count $rev ^origin/master`
fi

  if test "`echo $v | cut -d '.' -f 1`" -lt "5"; then
   if test "`git show $rev:gcc/DEV-PHASE`" == "prerelease"; then
    v=`echo $v | cut -d '.' -f 1-2 | tr -d '\n'; echo -n .; echo $v | cut -d '.' -f 3 | tr '0123456789' '0012345678'`
   fi
   if test "`git show $rev:gcc/DEV-PHASE`" == ""; then
    pkg="$package-$v"
   else
    pkg="$package-$v+git$r"
   fi
  else
   pkg="$package-$v+git$r"
  fi
if ! test -z "$3"; then
  pkg="$3"
fi
echo $pkg

if test -e $pkg; then
  echo oops, local $pkg exists
  exit 1
fi
mkdir -p $pkg/gcc
echo "[revision $rev]" > $pkg/gcc/REVISION
git archive --format=tar --prefix=$pkg/ -o $packagedir/$pkg.tar $rev
tar rvf $packagedir/$pkg.tar $pkg/gcc/REVISION
rm -Rf $pkg
xz -T0 $packagedir/$pkg.tar
ls -l $packagedir/$pkg.tar.xz

cd $packagedir
mv gcc.spec.in gcc.spec.in.old
sed  -e "s/Version:.*$/Version: ${v}+git$r/;" \
  < gcc.spec.in.old > gcc.spec.in
chmod 755 pre_checkin.sh
./pre_checkin.sh
rm gcc.spec.in.old
