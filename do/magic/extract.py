#!/usr/bin/env python
# -*- coding: utf8 -*-
# *****************************************************************
# **       PTS -- Python Toolkit for working with SKIRT          **
# **       © Astronomical Observatory, Ghent University          **
# *****************************************************************

## \package pts.do.magic.extract Extract stars and other objects from an astronomical image.

# -----------------------------------------------------------------

# Ensure Python 3 compatibility
from __future__ import absolute_import, division, print_function

# Import standard modules
import os
import argparse

# Import the relevant AstroMagic classes and modules
from pts.magic.misc.imageimporter import ImageImporter
from pts.magic.sources.extractor import SourceExtractor
from pts.core.tools import configuration, logging, time, filesystem

# -----------------------------------------------------------------

# Create the command-line parser
parser = argparse.ArgumentParser()
parser.add_argument("image", type=str, help="the name of the input image")
parser.add_argument("--debug", action="store_true", help="enable debug logging mode")
parser.add_argument('--report', action='store_true', help='write a report file')
parser.add_argument('--config', type=str, help='the name of a configuration file', default=None)
parser.add_argument("--settings", type=configuration.from_string, help="settings")


#parser.add_argument("--synchronize", action="store_true", help="synchronize with DustPedia catalog")

#parser.add_argument("--filecatalog", action="store_true", help="use file catalogs")

#parser.add_argument("-i", "--input", type=str, help="the name of the input directory")
#parser.add_argument("-o", "--output", type=str, help="the name of the output directory")

parser.add_argument("--special", type=str, help="the name of the file specifying regions with objects needing special attention")

parser.add_argument("--bad", type=str, help="the name of the file specifying regions that have to be added to the mask of bad pixels")

# Parse the command line arguments
arguments = parser.parse_args()

# -----------------------------------------------------------------

# If an input directory is given
if arguments.input is not None:

    # Determine the full path to the input directory
    arguments.input_path = os.path.abspath(arguments.input)

    # Give an error if the input directory does not exist
    if not os.path.isdir(arguments.input_path): raise argparse.ArgumentError(arguments.input_path, "The input directory does not exist")

# If no input directory is given, assume the input is placed in the current working directory
else: arguments.input_path = os.getcwd()

# -----------------------------------------------------------------

# If an output directory is given
if arguments.output is not None:
    
    # Determine the full path to the output directory
    arguments.output_path = os.path.abspath(arguments.output)
    
    # Create the directory if it does not yet exist
    if not os.path.isdir(arguments.output_path): os.makedirs(arguments.output_path)

# If no output directory is given, place the output in the current working directory
else: arguments.output_path = os.getcwd()

# -----------------------------------------------------------------

# Determine the log file path
logfile_path = filesystem.join(arguments.output_path, time.unique_name("sourceextractor") + ".txt") if arguments.report else None

# Determine the log level
level = "DEBUG" if arguments.debug else "INFO"

# Initialize the logger
log = logging.setup_log(level=level, path=logfile_path)
logging.log.info("Starting extract script ...")

# -----------------------------------------------------------------

# Determine the full path to the image
image_path = filesystem.absolute(arguments.image)

# Determine the full path to the bad region file
bad_region_path = os.path.join(arguments.input_path, arguments.bad) if arguments.bad is not None else None

# Import the image
importer = ImageImporter()
importer.run(image_path, bad_region_path=bad_region_path)

# -----------------------------------------------------------------

# Create a mask of the pixels that are NaNs
#self.nan_mask = Mask.is_nan(self.image.frames.primary)

# Set the NaN pixels to zero in the frame
#self.image.frames.primary[self.nan_mask] = 0.0

# Create an Extractor instance and configure it according to the command-line arguments
extractor = SourceExtractor.from_arguments(arguments)

# Run the extractor
extractor.run(importer.image)

# Save the result
#extractor.write_result(importer.image.original_header)

# -----------------------------------------------------------------



# -----------------------------------------------------------------
