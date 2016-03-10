#!/usr/bin/env python
# -*- coding: utf8 -*-
# *****************************************************************
# **       AstroMagic -- the image editor for astronomers        **
# **       © Astronomical Observatory, Ghent University          **
# *****************************************************************

## \package pts.magic.extraction.simpleextraction Contains the SimpleExtractor class.

# -----------------------------------------------------------------

# Ensure Python 3 compatibility
from __future__ import absolute_import, division, print_function

# Import standard modules
from skimage.restoration import inpaint

# Import the relevant AstroMagic classes and modules
from ..core import Frame, Source, Image
from ..basics import Mask, Region
from ..tools import masks

# Import the relevant PTS classes and modules
from ...core.tools import filesystem
from ...core.tools.logging import log

# -----------------------------------------------------------------

class SimpleExtractor(object):

    """
    This class ...
    """

    def __init__(self):

        """
        The constructor ...
        :return:
        """

        # -- Attributes --

        # The image
        self.image = None

        # The output path
        self.output_path = None

        # The mask of nans
        self.nan_mask = None

        # The masks
        self.principal_mask = None
        self.companion_mask = None
        self.other_galaxies_mask = None
        self.foreground_stars_sources = dict()
        self.other_stars_mask = None

        # The total mask of removed sources
        self.total_mask = None

    # -----------------------------------------------------------------

    def run(self, image_path, output_path):

        """
        This function ...
        :param image_path:
        :param output_path:
        :return:
        """

        # 1. Call the setup function
        self.setup(image_path, output_path)

        # 2. Create the masks
        self.create_masks()

        # 3. Remove the galaxies
        self.remove_galaxies()

        # 4. Remove the stars
        self.remove_stars_including_saturation()

    # -----------------------------------------------------------------

    def setup(self, image_path, output_path):

        """
        This function ...
        :param image_path:
        :param output_path:
        :return:
        """

        # Set the image
        self.image = Image.from_file(image_path)

        # Set the output path
        self.output_path = output_path

        # Create a mask of the pixels that are NaNs
        self.nan_mask = Mask.is_nan(self.image.frames.primary)

        # Set the NaN pixels to zero in the frame
        self.image.frames.primary[self.nan_mask] = 0.0

        # The total mask of removed sources
        self.total_mask = Mask.empty_like(self.image.frames.primary)

    # -----------------------------------------------------------------

    def create_masks(self):

        """
        This function ...
        :return:
        """

        # Create galaxy masks
        self.create_galaxy_masks()

        # Create star masks
        self.create_star_masks()

    # -----------------------------------------------------------------

    def create_galaxy_masks(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        #log.info("Loading the galaxy region ...")
        #galaxy_region_path = filesystem.join(self.output_path, "galaxies.reg")
        #self.galaxy_region = Region.from_file(galaxy_region_path)

        # Inform the user
        log.info("Loading the galaxy segmentation map ...")

        segments_path = filesystem.join(self.output_path, "galaxy_segments.fits")
        segments = Frame.from_file(segments_path)

        # Create the galaxy masks
        self.principal_mask = segments == 1
        self.companion_mask = segments == 2
        self.other_galaxies_mask = segments == 3

    # -----------------------------------------------------------------

    def create_star_masks(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Loading the star region ...")

        # Star region
        star_region_path = filesystem.join(self.output_path, "stars.reg")
        star_region = Region.from_file(star_region_path)

        # Inform the user
        log.info("Loading the segmentation map of stars ...")

        # Star segmentation map
        star_segments_path = filesystem.join(self.output_path, "star_segments.fits")
        star_segments = Frame.from_file(star_segments_path)

        # Inform the user
        log.info("Loading the saturation region ...")

        # Saturation region
        saturation_region_path = filesystem.join(self.output_path, "saturation.reg")
        saturation_region = Region.from_file(saturation_region_path)

        # Inform the user
        log.info("Loading the saturation segmentation map ...")

        # Saturation segmentation map
        saturation_segments_path = filesystem.join(self.output_path, "saturation_segments.fits")
        saturation_segments = Frame.from_file(saturation_region_path)

        # Initialize a list for the star indices that are present in the star region
        star_indices = set()

        # Initialize the foreground and other stars masks
        self.foreground_stars_mask = Mask.empty_like(self.image.frames.primary)
        self.other_stars_mask = Mask.empty_like(self.image.frames.primary)

        # Loop over all stars in the region
        for shape in star_region:

            # Ignore shapes without text, these should be just the positions of the peaks
            if "text" not in shape.meta: continue

            # Ignore shapes with color red (stars without source)
            if shape.meta["color"] == "red": continue

            # Get the star index
            index = int(shape.meta["text"])
            star_indices.add(index)

            # Get the star position
            position = shape.center

            # Check whether the star is a foreground star
            if self.principal_mask.masks(position):

                # FOREGROUND STARS: create sources, because the background is estimated by fitting a polynomial to
                # pixels in annulus around shape

                #source_mask = star_segments == index # not necessary, the source is created from the ellipse so
                # the star mask is created again

                # Create a source from the shape
                source = Source.from_ellipse(self.image.frames.primary, shape, 1.3)
                source.estimate_background("polynomial", sigma_clip=True)

                # Add the source to the dictionary, with a key that is the star index (so that the source for this star
                # can be replaced by the saturation source, if any
                self.foreground_stars_sources[index] = source

            # Not a foreground star
            else: self.other_stars_mask += star_segments == index

        # Add the saturation sources
        # Loop over the shapes in the saturation region
        for shape in saturation_region:

            # Ignore shapes without text (there should be none, but..)
            if "text" not in shape.meta: continue

            # Get the star index
            index = int(shape.meta["text"])

            # If this star index is not in the star_indices list (the star is removed from the star region by the user), ignore it (don't add the saturation mask for it)
            if index not in star_indices: continue

            # Get the star position
            position = shape.center

            # Check whether the star is a foreground star
            if self.principal_mask.masks(position):

                # Create a source from the shape
                source = Source.from_ellipse(self.image.frames.primary, shape, 1.3)

                # Set the source mask
                source.mask = saturation_segments == index

                # Estimate the background
                source.estimate_background("polynomial", True)

                # Replace the star source by the saturation source
                self.foreground_stars_sources[index] = source

            # Not a foreground star
            else: self.other_stars_mask += saturation_segments == index

    # -----------------------------------------------------------------

    def remove_galaxies(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Removing the galaxies from the frame ...")

        # Remove the companion galaxies
        #data = interpolation.in_paint(self.image.frames.primary, self.companion_mask)
        data = inpaint.inpaint_biharmonic(self.image.frames.primary, self.companion_mask, multichannel=True)
        self.image.frames.primary = Frame(data)

        # Add the mask to the total mask of removed sources
        self.total_mask += self.other_galaxies_mask

        # Remove the other galaxies
        #data = interpolation.in_paint(self.image.frames.primary, self.other_galaxies_mask)
        data = inpaint.inpaint_biharmonic(self.image.frames.primary, self.companion_mask, multichannel=True)
        self.image.frames.primary = Frame(data)

        # Add the mask to the total mask of removed sources
        self.total_mask += self.other_galaxies_mask

    # -----------------------------------------------------------------

    def remove_stars_including_saturation(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Removing the stars from the frame ...")

        # Remove the foreground stars including saturation
        for source in self.foreground_stars_sources:

            # Replace the frame by the estimated polynomial background
            source.background.replace(self.image.frames.primary, where=source.mask)

            # Add the source mask to the total mask
            self.total_mask[source.y_slice, source.x_slice] += source.mask

        # Remove the other stars including saturation
        data = inpaint.inpaint_biharmonic(self.image.frames.primary, self.other_stars_mask, multichannel=False)
        self.image.frames.primary = Frame(data)

        # Add the mask to the total mask of removed sources
        self.total_mask += self.other_stars_mask

    # -----------------------------------------------------------------

    def write(self):

        """
        This function ...
        :return:
        """

        # Write the result
        self.write_result()

        # Write the total mask of removed sources
        self.write_mask()

    # -----------------------------------------------------------------

    def write_result(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Writing the result ...")

        # Determine the path to the resulting FITS file
        path = filesystem.join(self.output_path, "final_result.fits")
        self.image.save(path)

    # -----------------------------------------------------------------

    def write_mask(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Writing the total mask of removed sources ...")

        # Determine the path to the mask FITS file
        path = filesystem.join(self.output_path, "final_mask.fits")
        Frame(self.total_mask).save(path)

# -----------------------------------------------------------------
