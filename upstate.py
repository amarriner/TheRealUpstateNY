#!/usr/bin/env python

"""Script to build an 'accurate' map of Upstate NY"""

from bs4 import BeautifulSoup
from PIL import Image, ImageDraw

import csv
import gpolyencode
import json
import os
import random
import re
import sys
import urllib

# Working directory
PWD = '/home/amarriner/python/upstate/'

# Where to store cached maps
IMG_DIR = '/home/amarriner/public_html/nys/'

# Maps URL data for counties
GOOGLE_MAPS = {
   'URL'   : 'http://maps.googleapis.com/maps/api/staticmap?center=42.91,-75.67&zoom=6&size=400x400&format=png32',
   'STYLES': '&style=feature:all|lightness:-100|hue:0x0000FF|saturation:-100',
   'PATH'  : '&path=weight:0%7Cfillcolor:green%7Ccolor:green%7Cenc:',
}

# Maps URL data for New York State
NEW_YORK_STATE = {
   'URL'   : 'http://maps.googleapis.com/maps/api/staticmap?center=42.91,-75.67&zoom=6&size=400x400&format=png32',
   'STYLES': '',
   'PATH'  : '&path=weight:3%7Cfillcolor:orange%7Ccolor:orange%7Cenc:',
}


def build_image(counties, adjacencies):
   """Builds an image of NYS with random counties constituting an 'accurate' Upstate NY region"""

   nys = Image.open(IMG_DIR + 'new_york_state.png')

   county_images = None

   for i in range(0, 5):
      county = random.choice(counties)
      print 'Picked ' + county['county-name']
      img = Image.open(IMG_DIR + county_name_key(county['county-name']) + '.png')
      img = img.convert('RGBA')

      pixdata = img.load()

      for y in xrange(img.size[1]):
         for x in xrange(img.size[0]):
            if pixdata[x, y] == (0, 0, 0, 255):
               pixdata[x, y] = (0, 0, 0, 0)
            else:
               pixdata[x, y] = (pixdata[x, y][0], pixdata[x, y][1], pixdata[x, y][2], 180)

      if not county_images:
         county_images = img
      else:
         county_images = Image.alpha_composite(county_images, img)

   Image.alpha_composite(nys, county_images).save(IMG_DIR + 'combo.png')


def county_name_key(c):
   """Format county name as suitable hash key"""

   return c.lower().replace(' ', '-').replace('.', '')


def get_county_by_name_or_key(name, counties):
   """Return county data retrieved by name or key"""

   for c in counties:
      if c['county-name'] == name or county_name_key(c['county-name']) == name:
         return c

   return None


def load_adjacencies():
   """Load JSON file with county adjacencies"""

   f = open('adjacencies.json')
   j = json.loads(f.read())
   f.close()

   return j


def load_csv(file):
   """Load CSV file of NYS counties and parse into an object, and cache a static google map of the county boundaries"""

   keys = []
   rows = []
   reader = csv.reader(open(file))

   # Build a list of counties with their corresponding data. Use the first row to build the list of keys needed
   # then assign values to those keys for future rows
   count = 0
   for row in reader:

      if count == 0:
         for field in row:
            keys.append(county_name_key(field))

      else:
         data = {}

         for i in range(0, len(row) - 1):
            data[keys[i]] = row[i]

         rows.append(data)

      count += 1


   # Loop through the counties and determine encoded polylines based on their geometry then cache a map image if necessary
   for c in rows:
      geo = parse_geometry(c['geometry'])

      if not os.path.isfile(IMG_DIR + county_name_key(c['county-name']) + '.png'):
         print 'Downloading ' + c['county-name'] + ' ...'
         urllib.urlretrieve(GOOGLE_MAPS['URL'] + GOOGLE_MAPS['STYLES'] + GOOGLE_MAPS['PATH'] + geo[0]['points'], IMG_DIR + county_name_key(c['county-name']) + '.png')


   return rows


def load_state(file):
   """Loads state geography from file; couldn't do it via CSV because it errors off due to long record length, cache a google map of it as well, if necessary"""

   f = open(file)
   data = f.read()
   f.close()

   geo = parse_geometry(data)
   if not os.path.isfile(IMG_DIR + 'new_york_state.png'):
      print 'Downloading NYS ...'
      urllib.urlretrieve(NEW_YORK_STATE['URL'] + NEW_YORK_STATE['PATH'] + geo[2]['points'], IMG_DIR + 'new_york_state.png')

   return data


def parse_geometry(g):
   """Uses gpolyencode to return a polyline for the given geometry"""

   # Use Beautiful Soup to ease parsing the tags surrounding the geometry entry
   soup = BeautifulSoup(g)
   encoder = gpolyencode.GPolyEncoder()

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

   state = load_state('new_york_state.geo')
   counties = load_csv('new_york_counties.csv')   
   adjacencies = load_adjacencies()

   build_image(counties, adjacencies)


if __name__ == '__main__':
   sys.exit(main())

