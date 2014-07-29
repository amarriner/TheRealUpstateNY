#!/usr/bin/env python

"""Script to build an 'accurate' map of Upstate NY"""

from bs4 import BeautifulSoup

import csv
import gpolyencode
import json
import re
import sys


def load_csv():
   """Load CSV file of NYS counties and parse into an object"""

   counties = []
   reader = csv.reader(open("new_york_counties.csv"))

   for row in reader:

      if row[0] != 'County Name' and len(row[0]):
         county = {
                     'name':         row[0],
                     'state-county': row[1],
                     'state-abbr'  : row[2],
                     'geometry'    : row[4],
                     'value'       : row[5],
                     'geo-id'      : row[6],
                     'geo-id2'     : row[7],
                     'geo-name'    : row[8],
                     'number'      : row[10],
                  }

         counties.append(county)

   return counties


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


   counties = load_csv()
   for c in counties:
      print c['name']
      c['polyline'] = parse_geometry(c['geometry'])

      line = ''
      for p in c['polyline']:
         print p['points']

         if len(line):
            line = '|' + line

         line = line + p['points']

      #print line

   f = open('new_york_counties.json', 'w')
   f.write(json.dumps(counties))
   f.close()
   

if __name__ == '__main__':
   sys.exit(main())

