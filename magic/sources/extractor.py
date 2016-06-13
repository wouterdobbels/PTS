#!/usr/bin/env python
# -*- coding: utf8 -*-
# *****************************************************************
# **       PTS -- Python Toolkit for working with SKIRT          **
# **       © Astronomical Observatory, Ghent University          **
# *****************************************************************

## \package pts.magic.sources.extractor Contains the SourceExtractor class.

# -----------------------------------------------------------------

# Ensure Python 3 compatibility
from __future__ import absolute_import, division, print_function

# Import standard modules
import numpy as np

# Import astronomical modules
from astropy.utils import lazyproperty

# Import the relevant PTS classes and modules
from ..basics.mask import Mask
from ..basics.geometry import Ellipse
from ..core.source import Source
from ...core.tools.logging import log
from ...core.basics.configurable import Configurable
from ..tools import plotting
from ..tools import masks

# -----------------------------------------------------------------

class SourceExtractor(Configurable):

    """
    This class ...
    """

    def __init__(self, config=None):

        """
        The constructor ...
        :return:
        """

        # Call the constructor of the base class
        super(SourceExtractor, self).__init__(config, "magic")

        # -- Attributes --

        # The image frame
        self.frame = None

        # The output path
        self.output_path = None

        # The original minimum and maximum value
        self.minimum_value = None
        self.maximum_value = None

        # The mask of nans
        self.nan_mask = None

        # Regions
        self.galaxy_region = None
        self.star_region = None
        self.saturation_region = None
        self.other_region = None

        # The animation
        self.animation = None

        # Segmentation maps
        self.galaxy_segments = None
        self.star_segments = None
        self.other_segments = None

        # The total mask of removed sources
        self.mask = None

        # The list of sources
        self.sources = []

    # -----------------------------------------------------------------

    @classmethod
    def from_arguments(cls, arguments):

        """
        This function ...
        :param arguments:
        :return:
        """

        # Create a new SourceExtractor instance
        extractor = cls()

        # Return the extractor
        return extractor

    # -----------------------------------------------------------------

    def run(self, frame, galaxy_region, star_region, saturation_region, other_region, galaxy_segments, star_segments, other_segments, animation=None):

        """
        This function ...
        :param frame:
        :param galaxy_region:
        :param star_region:
        :param saturation_region:
        :param other_region:
        :param galaxy_segments:
        :param star_segments:
        :param other_segments:
        :param animation:
        :return:
        """

        # 1. Call the setup function
        self.setup(frame, galaxy_region, star_region, saturation_region, other_region, galaxy_segments, star_segments, other_segments, animation)

        # 2. Load the sources
        self.load_sources()

        # 3. Remove the sources
        self.remove_sources()

        # 4. Fix extreme values that showed up during the interpolation steps
        self.fix_extreme_values()

        # 4. Set nans back into the frame
        self.set_nans()

    # -----------------------------------------------------------------

    def setup(self, frame, galaxy_region, star_region, saturation_region, other_region, galaxy_segments, star_segments,
              other_segments, animation=None):

        """
        This function ...
        :param frame:
        :param galaxy_region:
        :param star_region:
        :param saturation_region:
        :param other_region:
        :param galaxy_segments:
        :param star_segments:
        :param other_segments:
        :param animation:
        :return:
        """

        # Set the image frame
        self.frame = frame

        # Regions
        self.galaxy_region = galaxy_region
        self.star_region = star_region
        self.saturation_region = saturation_region
        self.other_region = other_region

        # Segmentation maps
        self.galaxy_segments = galaxy_segments
        self.star_segments = star_segments
        self.other_segments = other_segments

        # Initialize the mask
        self.mask = Mask.empty_like(self.frame)

        # Remember the minimum and maximum value
        self.minimum_value = np.nanmin(frame)
        self.maximum_value = np.nanmax(frame)

        # Create a mask of the pixels that are NaNs
        self.nan_mask = Mask.is_nan(self.frame)
        self.frame[self.nan_mask] = 0.0

        # Make a reference to the animation
        self.animation = animation

    # -----------------------------------------------------------------

    def load_sources(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Loading the sources ...")

        # Load the galaxy sources
        self.load_galaxy_sources()

        # Load the star sources
        if self.star_region is not None: self.load_star_sources()

        # Load the other sources
        if self.other_region is not None: self.load_other_sources()

    # -----------------------------------------------------------------

    def load_galaxy_sources(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Loading the galaxy sources ...")

        # Loop over the shapes in the galaxy region
        for shape in self.galaxy_region:

            # Shapes without text are in this case just coordinates
            if "text" not in shape.meta: continue

            # Get the coordinate of the center for this galaxy
            center = shape.center

            # Check the label of the corresponding segment
            label = self.galaxy_segments[int(center.y), int(center.x)]

            if label == 3 or (label == 2 and self.config.remove_companions):

                # Create a source and add it to the list
                source = Source.from_shape(self.frame, shape, self.config.source_outer_factor)
                self.sources.append(source)

    # -----------------------------------------------------------------

    def load_star_sources(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Loading the star sources ...")

        # Loop over all stars in the region
        for shape in self.star_region:

            # Ignore shapes without text, these should be just the positions of the peaks
            if "text" not in shape.meta: continue

            # Ignore shapes with color red (stars without source)
            if shape.meta["color"] == "red": continue

            # Get the star index
            index = int(shape.meta["text"])

            # Look whether a saturation source is present
            saturation_source = None

            # Check whether the star is a foreground star
            #if self.principal_mask.masks(shape.center): foreground = True

            if self.saturation_region is not None:

                # Add the saturation sources
                # Loop over the shapes in the saturation region
                for j in range(len(self.saturation_region)):

                    saturation_shape = self.saturation_region[j]

                    if "text" not in saturation_shape.meta: continue

                    saturation_index = int(saturation_shape.meta["text"])

                    if index != saturation_index: continue
                    else:
                        # Remove the saturation shape from the region
                        saturation_shape = self.saturation_region.pop(j)

                        # Create saturation source
                        saturation_source = Source.from_shape(self.frame, saturation_shape, self.config.source_outer_factor)

                        # Replace the saturation mask
                        segments_cutout = self.star_segments[saturation_source.y_slice, saturation_source.x_slice]
                        saturation_mask = Mask(segments_cutout == index)
                        saturation_source.mask = saturation_mask.fill_holes()

                        # Break the loop
                        break

            if saturation_source is not None:

                # Add the saturation source
                self.sources.append(saturation_source)

            else:

                # Create a new source from the shape and add it
                source = Source.from_shape(self.frame, shape, self.config.source_outer_factor)
                self.sources.append(source)

    # -----------------------------------------------------------------

    def load_other_sources(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Loading the other sources ...")

        # Loop over the shapes in the other sources region
        for shape in self.other_region:

            # This is a source found by SourceFinder
            if "text" in shape.meta:

                label = int(shape.meta["text"])

                # Create a source
                source = Source.from_shape(self.frame, shape, self.config.source_outer_factor)

                # Replace the source mask
                segments_cutout = self.other_segments[source.y_slice, source.x_slice]
                source.mask = Mask(segments_cutout == label).fill_holes()

            # This is a shape drawn by the user and added to the other sources region
            else:

                # Create a source
                source = Source.from_shape(self.frame, shape, self.config.source_outer_factor)

            # Add the source to the list
            self.sources.append(source)

    # -----------------------------------------------------------------

    def remove_sources(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Interpolating the frame over the masked pixels ...")

        nsources = len(self.sources)
        count = 0

        # Set principal ellipse and mask for the animation
        if self.animation is not None:
            self.animation.principal_ellipse = self.principal_ellipse
            self.animation.mask = self.mask

        # Loop over all sources and remove them from the frame
        for source in self.sources:

            # Debugging
            log.debug("Estimating background and replacing the frame pixels of source " + str(count+1) + " of " + str(nsources) + " ...")

            # Check whether the source is in front of the principal galaxy
            #foreground = self.principal_mask.masks(source.center)
            if self.principal_mask is not None: foreground = masks.overlap(self.principal_mask[source.y_slice, source.x_slice], source.mask)
            else: foreground = False

            # Disable sigma-clipping for estimating background when the source is foreground to the principal galaxy (to avoid clipping the galaxy's gradient)
            sigma_clip = self.config.sigma_clip if not foreground else False

            # Estimate the background
            try:
                source.estimate_background(self.config.interpolation_method, sigma_clip=sigma_clip)
            except ValueError: # ValueError: zero-size array to reduction operation minimum which has no identity
                # in: limits = (np.min(known_points), np.max(known_points)) [inpaint_biharmonic]
                count += 1
                continue

            # If these pixels are already replaced by an overlapping source (e.g. saturation), skip this source,
            # otherwise the area will be messed up
            current_mask_cutout = self.mask[source.y_slice, source.x_slice]
            if current_mask_cutout.covers(source.mask):
                count += 1
                continue

            # Adapt the mask
            self.mask[source.y_slice, source.x_slice] += source.mask

            # Add frame to the animation
            if self.animation is not None and (self.principal_mask is None or self.principal_mask.masks(source.center)) and self.animation.nframes <= 20:
                self.animation.add_source(source)

            # Replace the pixels by the background
            source.background.replace(self.frame, where=source.mask)

            #if not sigma_clip:
            #    # source.plot()

            #    plotting.plot_removal(source.cutout, source.mask, source.background,
            #                          self.frame[source.y_slice, source.x_slice])

            count += 1

    # -----------------------------------------------------------------

    def fix_extreme_values(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Fixing extreme values that were introduced during the interpolation steps ...")

        self.frame[self.frame < self.minimum_value] = self.minimum_value
        self.frame[self.frame > self.maximum_value] = self.maximum_value

    # -----------------------------------------------------------------

    def set_nans(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Setting original NaN-pixels back to NaN ...")

        # Set the NaN pixels to zero in the frame
        self.frame[self.nan_mask] = float("nan")

    # -----------------------------------------------------------------

    @lazyproperty
    def principal_ellipse(self):

        """
        This function ...
        :return:
        """

        if self.galaxy_region is None: return None

        largest_shape = None

        # Loop over all the shapes in the galaxy region
        for shape in self.galaxy_region:

            # Skip shapes that are not ellipses
            if not isinstance(shape, Ellipse): continue

            major_axis_length = shape.major

            if largest_shape is None or major_axis_length > largest_shape.major: largest_shape = shape

        # Return the largest shape in the galaxy region
        return largest_shape

    # -----------------------------------------------------------------

    @lazyproperty
    def principal_mask(self):

        """
        This function ...
        :return:
        """

        if self.principal_ellipse is None: return None
        return self.principal_ellipse.to_mask(self.frame.xsize, self.frame.ysize)

# -----------------------------------------------------------------
