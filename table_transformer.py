#!/usr/bin/env python

from __future__ import print_function
from optparse import OptionParser
from lxml import etree

import os
import sys

delimiter = ':'

parser = OptionParser()
parser.add_option("-d", "--delimiter", dest="delimiter", help="column delimiter")

(options, args) = parser.parse_args()

if options.delimiter:
  delimiter = options.delimiter

if len(args) < 1:
  print('Usage: table_transform [options] {file}')

lines = [x.strip().split(delimiter) for x in open(args[0]).readlines()]
width = len(lines[0])

table = etree.Element('table', { 'class': 'table table-stripped'})

# header creation
thead = etree.SubElement(table, 'thead')
theadtr = etree.SubElement(thead, 'tr')

for column in range(width):
  th = etree.SubElement(theadtr, 'th')
  th.text = 'header' + str(column)

# body creation
tbody = etree.SubElement(table, 'tbody')

for line in lines:
  tr = etree.SubElement(tbody, 'tr')
  for column in line:
    td = etree.SubElement(tr, 'td')
    td.text = column

etree.dump(table)
