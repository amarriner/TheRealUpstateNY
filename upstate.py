#!/usr/bin/env python

"""Script to build an 'accurate' map of Upstate NY"""

from bs4 import BeautifulSoup

import csv
import gpolyencode
import json
import re
import sys


def load_csv(file):
   """Load CSV file of NYS counties and parse into an object"""

   rows = []
   reader = csv.reader(open(file))

   keys = []

   count = 0
   for row in reader:

      if count == 0:
         for field in row:
            keys.append(field.lower().replace(' ', '-'))

      else:
         data = {}

         for i in range(0, len(row) - 1):
            data[keys[i]] = row[i]

         rows.append(data)

      count += 1

   return rows


def load_state(file):
   """Loads state geography from file; couldn't do it via CSV because it errors off due to long record length"""

   f = open(file)
   data = BeautifulSoup(f.read())
   f.close()

   return data


def parse_geometry(g):
   """Uses gpolyencode to return a polyline for the given geometry"""

   encoder = gpolyencode.GPolyEncoder()
   soup = BeautifulSoup(g)

   print soup.prettify()

   polylines = []
   for coords in soup.find_all('coordinates'):

      points = []
      for p in coords.text.split(' '):
         pt = p.split(',')

         pt[0] = float(pt[0])
         pt[1] = float(pt[1])

         points.append(pt)

      polylines.append(encoder.encode(points))
   
   return polylines


def main():
   """Main entry point"""


   counties = load_csv('new_york_counties.csv')   
   print len(counties)

   state = load_state('new_york_state.geo')
   print state.prettify()


if __name__ == '__main__':
   sys.exit(main())

