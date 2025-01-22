#!/usr/bin/env python

"""Script to build an 'accurate' map of Upstate NY"""

import csv
import json
import os
import polyline
import random
import requests
import sys
import time

from atproto import Client as BlueskyClient
from bs4 import BeautifulSoup
from PIL import Image, ImageDraw, ImageFont


# Get configuration
with open(f"{os.path.dirname(os.path.realpath(__file__))}/.config.json") as f:
    config = json.loads(f.read())

# Working directory
PWD = config['working_directory']

# Where to store cached maps
IMG_DIR = f"{PWD}/images"

# Number of times to iterate county adjacencies
DEPTH = random.choice([3, 4, 5])

# Base URL for static maps API
BASE_URL = "http://maps.googleapis.com/maps/api/staticmap"

# Center of the map
CENTER = "center=42.91,-75.67&zoom=6&size=400x400&scale=2&format=png32"

# Maps URL data for counties
GOOGLE_MAPS = {
    'URL': f"{BASE_URL}?{CENTER}&key={config['google']['maps']['key']}",
    'STYLES': '&style=feature:all|lightness:-100|hue:0x0000FF|saturation:-100',
    'PATH': '&path=fillcolor:green%7Ccolor:green%7Cweight:0%7C',
}

# Maps URL data for New York State
NEW_YORK_STATE = {
    'URL': f"{BASE_URL}?{CENTER}&key={config['google']['maps']['key']}",
    'STYLES': '',
    'PATH': '&path=weight:3%7Ccolor:orange%7Cfillcolor:orange%7C',
}


def build_image(counties, adjacencies):
    """Builds an image of NYS with random counties constituting an 'accurate' Upstate NY region"""

    # Use the adjacencies to build a list of counties to include in the image
    county_list = {}
    start = random.choice(counties)
    county_list[county_name_key(start['county-name'])] = start
    county_list = get_adjacencies(county_list, start, counties, adjacencies, 1)

    # Cached image of NYS
    nys = Image.open(f"{IMG_DIR}/new_york_state.png")

    county_images = None
    for key in county_list.keys():
        county = county_list[key]

        print(f"Picked {county['county-name']}")
        img = Image.open(f"{IMG_DIR}/{county_name_key(county['county-name'])}.png")
        img = img.convert('RGBA')

        # Used the code at the URL below to set black pixels to transparent
        # http://stackoverflow.com/questions/765736/using-pil-to-make-all-white-pixels-transparent
        pixdata = img.load()
        for y in range(img.size[1]):
            for x in range(img.size[0]):
                if y > 725:
                    pixdata[x, y] = (0, 0, 0, 0)
                elif pixdata[x, y] == (0, 0, 0, 255):
                    pixdata[x, y] = (0, 0, 0, 0)
                elif pixdata[x, y] == (255, 255, 255, 255):
                    pixdata[x, y] = (0, 0, 0, 0)
                else:
                    pixdata[x, y] = (pixdata[x, y][0], pixdata[x, y][1], pixdata[x, y][2], 180)

        # Continually build an overlay of all counties to place on top of the NYS image
        if not county_images:
            county_images = img
        else:
            county_images = Image.alpha_composite(county_images, img)

    # Place the combined county overlay onto the state image
    img = Image.alpha_composite(nys, county_images)
    text = "THIS is upstate NY!"
    draw = ImageDraw.Draw(img)
    font = ImageFont.truetype(f"{PWD}/HackNerdFont-Bold.ttf", 60)
    draw.text((60, 25), text, font=font, fill=(76, 187, 23), stroke_width=3, stroke_fill=(53, 94, 59))

    filename = f"{IMG_DIR}/combo.png"
    img.save(filename)
    with open(filename, 'rb') as f:
        b = f.read()

    return b


def county_name_key(c):
    """Format county name as suitable hash key"""

    return c.lower().replace(' ', '-').replace('.', '')


def get_adjacencies(county_list, start, counties, adjacencies, depth):
    """Add adjacencies to a list"""

    # Keeps getting adjacent counties until the specified depth is reached
    for a in get_adjacencies_by_key(county_name_key(start['county-name']), adjacencies):
        next = get_county_by_name_or_key(a, counties)

        if county_name_key(next['county-name']) not in county_list.keys():
            county_list[county_name_key(next['county-name'])] = next

        if depth < DEPTH:
            get_adjacencies(county_list, next, counties, adjacencies, depth + 1)

    return county_list


def get_adjacencies_by_key(key, adjacencies):
    """Return all county adjacencies by key"""

    for a in adjacencies.keys():
        if a == key:
            return adjacencies[a]

    return None


def get_county_by_name_or_key(name, counties):
    """Return county data retrieved by name or key"""

    for c in counties:
        if c['county-name'] == name or county_name_key(c['county-name']) == name:
            return c

    return None


def load_adjacencies():
    """Load JSON file with county adjacencies"""

    with open(f"{PWD}/adjacencies.json") as f:
        j = json.loads(f.read())

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

        if not os.path.isfile(f"{IMG_DIR}/{county_name_key(c['county-name'])}.png"):
            print(f"Downloading {c['county-name']} ...")
            url = f"{GOOGLE_MAPS['URL']}{GOOGLE_MAPS['STYLES']}{GOOGLE_MAPS['PATH']}enc:{geo[0]}"
            filename = f"{IMG_DIR}/{county_name_key(c['county-name'])}.png"
            with open(filename, 'wb') as f:
                f.write(requests.get(url).content)
            time.sleep(1)  # Lazy way to avoid throttling while caching...should check response instead and retry

    return rows


def load_state(file):
    """Loads state geography from file; Cache a google map of it if necessary"""

    with open(file) as f:
        data = f.read()

    # Get an encoded polyline for the state geography and cache the map if necessary
    geo = parse_geometry(data)
    if not os.path.isfile(f"{IMG_DIR}/new_york_state.png"):
        print("Downloading NYS ...")
        url = f"{NEW_YORK_STATE['URL']}{NEW_YORK_STATE['PATH']}enc:{geo[2]}"
        print(url)
        filename = f"{IMG_DIR}/new_york_state.png"
        with open(filename, 'wb') as f:
            f.write(requests.get(url).content)

    return data


def parse_geometry(g):
    """Uses polyline to return a polyline for the given geometry"""

    # Use Beautiful Soup to ease parsing the tags surrounding the geometry entry
    soup = BeautifulSoup(g, features="html.parser")

    polylines = []
    for coords in soup.find_all('coordinates'):

        points = [[float(p.split(',')[1]), float(p.split(',')[0])] for p in coords.text.split(' ')]
        polylines.append(polyline.encode(points))

    return polylines


def main():
    """Main entry point"""

    load_state(f"{PWD}/new_york_state.geo")
    counties = load_csv(f"{PWD}/new_york_counties.csv")
    adjacencies = load_adjacencies()
    byte_arr = build_image(counties, adjacencies)

    client = BlueskyClient()
    client.login(config['bluesky']['username'], config['bluesky']['password'])
    client.send_image('This is the real #UpstateNY!', byte_arr, image_alt='This is the real #UpstateNY')


if __name__ == '__main__':
    sys.exit(main())
