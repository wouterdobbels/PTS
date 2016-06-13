#!/usr/bin/env python
# -*- coding: utf8 -*-
# *****************************************************************
# **       PTS -- Python Toolkit for working with SKIRT          **
# **       © Astronomical Observatory, Ghent University          **
# *****************************************************************

## \package pts.do.magic.prepare_image Prepare an image with PTS.

# -----------------------------------------------------------------

# Ensure Python 3 compatibility
from __future__ import absolute_import, division, print_function

# Import standard modules
import argparse

# Import the relevant PTS classes and modules
from pts.magic.prepare.imagepreparation import ImagePreparer
from pts.core.tools import logging, time, tables
from pts.core.tools import filesystem as fs
from pts.magic.core.image import Image
from pts.magic.basics.region import Region
from pts.magic.misc.calibration import CalibrationError
from pts.magic.misc.extinction import GalacticExtinction

# -----------------------------------------------------------------

# Create the command-line parser
parser = argparse.ArgumentParser()

# Basic
parser.add_argument("image", type=str, nargs='?', help="the name/path of the image for which to run the preparation")
parser.add_argument("kernel", type=str, help="the name/path of the kernel file for the convolution")
parser.add_argument("reference", type=str, help="the name/path of the reference image (to which the image is rebinned)")

# Advanced options
parser.add_argument("--sky_annulus_outer", type=float, help="the factor to which the ellipse describing the principal galaxy should be multiplied to represent the outer edge of the sky annulus")
parser.add_argument("--sky_annulus_inner", type=float, help="the factor to which the ellipse describing the principal galaxy should be multiplied to represent the inner edge of the sky annulus")
parser.add_argument("--convolution_remote", type=str, help="the name of the remote host to be used for the convolution step")
parser.add_argument("--sky_region", type=str, help="the name/path of a file with manually selected regions for the sky estimation (not apertures but extended regions of any shape and number)")

# Input and output
parser.add_argument("--input", type=str, help="the input path (output of find_sources step)")
parser.add_argument("--output", type=str, help="the output path")

# Logging
parser.add_argument("--debug", action="store_true", help="enable debug logging mode")
parser.add_argument("--report", action='store_true', help="write a report file")

parser.add_argument("--steps", action="store_true", help="write the results of intermediate steps")
parser.add_argument("--config", type=str, help="the name of a configuration file")

# Visualisation
parser.add_argument("--visualise", action="store_true", help="make visualisations")

# Parse the command line arguments
arguments = parser.parse_args()

# -----------------------------------------------------------------

# Determine the full input and output paths
if arguments.output is None: arguments.output = fs.cwd()
if arguments.input is None: arguments.input = fs.cwd()
arguments.input = fs.absolute(arguments.input)
arguments.output = fs.absolute(arguments.output)

# -----------------------------------------------------------------

# Determine the log file path
logfile_path = fs.join(arguments.output, time.unique_name("log") + ".txt") if arguments.report else None

# Determine the log level
level = "DEBUG" if arguments.debug else "INFO"

# Initialize the logger
log = logging.setup_log(level=level, path=logfile_path)
log.start("Starting prepare_image ...")

# -----------------------------------------------------------------

# Determine the path to the input image
image_path = fs.absolute(arguments.image)

# Load the image
image = Image.from_file(image_path)

# Determine the absolute path to the reference image
arguments.reference = fs.absolute(arguments.reference)

# Determine the absolute path to the convolution kernel
arguments.kernel = fs.absolute(arguments.kernel)

# Determine the path to the galaxy region
galaxy_region_path = fs.join(arguments.input, "galaxies.reg")

# Load the galaxy region
galaxy_region = Region.from_file(galaxy_region_path)

# Determine the path to the star region
star_region_path = fs.join(arguments.input, "stars.reg")

# Load the star region
star_region = Region.from_file(star_region_path)

# Determine the path to the saturation region
saturation_region_path = fs.join(arguments.input, "saturation.reg")

# Load the saturation region
saturation_region = Region.from_file(saturation_region_path) if fs.is_file(saturation_region_path) else None

# Determine the path to the region of other sources
other_region_path = fs.join(arguments.input, "other_sources.reg")

# Load the region of other sources
other_region = Region.from_file(other_region_path) if fs.is_file(other_region_path) else None

# Load the image with segmentation maps
segments_path = fs.join(arguments.input, "segments.fits")
segments = Image.from_file(segments_path, no_filter=True)

# Get the segmentation maps
galaxy_segments = segments.frames.galaxies
star_segments = segments.frames.stars
other_segments = segments.frames.other_sources

# -----------------------------------------------------------------

# Get the center coordinate of the frame
center_coordinate = image.coordinate_range[0]

# Get the filter name
if image.filter is None: raise RuntimeError("Filter not recognized!")
filter_name = str(image.filter)

# -----------------------------------------------------------------

# Debugging
log.debug("Getting galactic extinction ...")

# Get the galactic extinction for this image
arguments.attenuation = GalacticExtinction(center_coordinate).extinction_for_filter(image.filter)

# -----------------------------------------------------------------

# Get the calibration error
arguments.calibration = CalibrationError.from_filter(image.filter)

# -----------------------------------------------------------------

# If visualisation is enabled, set the visualisation path (=output path)
if arguments.visualise: visualisation_path = arguments.output
else: visualisation_path = None

# -----------------------------------------------------------------

# Create an ImagePreparer instance
preparer = ImagePreparer.from_arguments(arguments)

# Run the image preparation
preparer.run(image, galaxy_region, star_region, saturation_region, other_region, galaxy_segments, star_segments, other_segments, visualisation_path)

# -----------------------------------------------------------------
