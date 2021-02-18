#!/bin/bash

GOOGLE=/home/marxin/gcc-google/bin/gcc
JAN=/home/marxin/gcc-reorder/bin/gcc
DUMP=/tmp/google-reorder-dump.txt

echo "1) Normal build"
gcc $1 -o $1-normal
echo "2) Jan build"
$JAN $1 -freorder-functions -ftoplevel-reorder -fdump-ipa-all -o $1-jan
echo "3) Google profile generate build"
$GOOGLE -freorder-functions=callgraph -fprofile-generate $1 -o $1-google-temp

chmod +x $1-google-temp
./$1-google-temp > /dev/null

echo "3) Google profile use build"
$GOOGLE -freorder-functions=callgraph -fprofile-use -Wl,--plugin-opt,file=$DUMP $1 -o $1-google-final
