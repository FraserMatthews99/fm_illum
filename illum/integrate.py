#!/usr/bin/env python

import argparse
import re

import numpy as np
import pyproj
import yaml
from illum.pytools import load_bin
from matplotlib.path import Path

parser = argparse.ArgumentParser(
    description="Integrates Illumina binary file over a polygon."
)
parser.add_argument("domain", help="Domain characteristics file [domain.ini].")
parser.add_argument("bin", help="Binary file to integrate.")
parser.add_argument(
    "kml",
    nargs="+",
    help="KML file or files that defines the area over wich to integrate.",
)

p = parser.parse_args()

bin = load_bin(p.bin)

# Load zones

regex = re.compile(r"<coordinates>\s*(.*)\s*<\/coordinates>")

zones = dict()
for kml_file in p.kml:
    with open(kml_file) as f:
        kml_data = f.read()

    coords_txt = re.findall(regex, kml_data)[0]
    coords_txt = coords_txt.strip().replace(" ", ";")
    coords = np.asarray(np.matrix(coords_txt))

    zones[kml_file.split(".", 1)[0]] = coords[:, :2]

# Project zone coordinates

with open(p.domain) as f:
    domain = yaml.load(f)

domain["xmin"], domain["ymin"], domain["xmax"], domain["ymax"] = list(
    map(float, domain["bbox"].split())
)

p1 = pyproj.Proj("epsg:4326")  # WGS84
p2 = pyproj.Proj(domain["srs"])

for zone, data in zones.items():
    lat, lon = data.T

    x, y = pyproj.transform(p1, p2, lon, lat, always_xy=True)

    data[:, 0] = (x - domain["xmin"]) / domain["pixsize"] + 1
    data[:, 1] = (y - domain["ymin"]) / domain["pixsize"] + 1

# Define masks
nr, nc = bin.shape
ygrid, xgrid = np.mgrid[:nr, :nc]
xypix = np.vstack((xgrid.ravel(), ygrid.ravel())).T

for zone, data in zones.items():
    pth = Path(data, closed=False)
    mask = pth.contains_points(xypix)
    mask = mask.reshape(bin.shape)
    print(zone, np.sum(bin[mask]))
