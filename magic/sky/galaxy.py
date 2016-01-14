#!/usr/bin/env python
# -*- coding: utf8 -*-
# *****************************************************************
# **       AstroMagic -- the image editor for astronomers        **
# **       © Astronomical Observatory, Ghent University          **
# *****************************************************************

## \package pts.magic.sky.galaxy Contains the Galaxy class.

# -----------------------------------------------------------------

# Ensure Python 3 functionality
from __future__ import absolute_import, division, print_function

# Import astronomical modules
from astropy import units as u
from astropy.coordinates import Angle

# Import the relevant AstroMagic classes and modules
from ..core import Source
from .skyobject import SkyObject
from ..basics import Extent, Ellipse
from ..tools import catalogs

# -----------------------------------------------------------------

class Galaxy(SkyObject):

    """
    This class ...
    """

    def __init__(self, index, name, position, redshift, galaxy_type, names, distance, inclination, d25, major, minor, position_angle):

        """
        The constructor ...
        :param position:
        :param name:
        :return:
        """

        self.index = index

        # Set attributes
        self.name = name
        self.redshift = redshift
        self.type = galaxy_type
        self.names = names
        self.distance = distance
        self.inclination = inclination
        self.d25 = d25
        self.major = major
        self.minor = minor
        self.pa = position_angle

        # Set the principal and companion flags to False initially
        self.principal = False
        self.companion = False

        # Initialize a list for the names of companion galaxies
        self.companions = []
        self.parent = None

        # Call the constructor of the base class
        super(Galaxy, self).__init__(position)

    # -----------------------------------------------------------------

    @classmethod
    def from_name(cls, name, position=None):

        """
        This function ...
        :return:
        """

        # Get the galaxy information
        name, position, redshift, type, names, distance, inclination, d25, major, minor, pa = catalogs.get_galaxy_info(name, position)

        # Create and return a new Galaxy instance
        return cls(0, name, position, redshift, type, names, distance, inclination, d25, major, minor, pa)

    # -----------------------------------------------------------------

    def contains(self, position):

        """
        This function ...
        :param star:
        :return:
        """

        # If the position does not lie within the cutout box of the galaxy's source, return False
        if not self.source.cutout.contains(position): return False

        # If it does, check whether the pixel position is masked by the mask of the galaxy's source
        return self.source.mask.masks(self.source.cutout.rel_position(position))

    # -----------------------------------------------------------------

    @property
    def has_extent(self):

        """
        This function ...
        :return:
        """

        # Check whether the length of the major axis is defined
        return self.major is not None

    # -----------------------------------------------------------------

    def ellipse_parameters(self, wcs, pixelscale, default_radius):

        """
        This function ...
        :param default_radius:
        :return:
        """

        #print("pixelscale=", pixelscale)

        #print("self.pa=", self.pa)
        #print("self.major=", self.major)
        #print("self.minor=", self.minor)

        if self.pa is None: angle = Angle(0.0, u.deg)
        else: angle = self.pa

        if self.major is None:

            x_radius = default_radius
            y_radius = default_radius

        elif self.minor is None or angle == 0.0:

            x_radius = 0.5 * self.major.to("arcsec") / pixelscale
            y_radius = x_radius

        else:

            x_radius = 0.5 * self.major.to("arcsec") / pixelscale
            y_radius = 0.5 * self.minor.to("arcsec") / pixelscale

        #print("x_radius=", x_radius)
        #print("y_radius=", y_radius)

        pixel_position = self.pixel_position(wcs)

        #print("PIXEL_POSITION=", pixel_position)

        # Return the parameters
        return pixel_position, Extent(x=x_radius, y=y_radius), angle

    # -----------------------------------------------------------------

    def source_from_parameters(self, frame, outer_factor, expansion_factor=1.0):

        """
        This function ...
        :return:
        """

        # Get the parameters describing the elliptical contour
        center, radius, angle = self.ellipse_parameters(frame.wcs, frame.pixelscale, None)

        if center.x < 0 or center.y < 0:
            self.source = None
            return

        # Create a source object
        ellipse = Ellipse(center, radius*expansion_factor, angle)
        self.source = Source.from_ellipse(frame, ellipse, outer_factor)

        if self.source.cutout.shape[0] == 0 or self.source.cutout.shape[1] == 0:

            print(self.name)
            print("radius=", radius)

    # -----------------------------------------------------------------

    def fit_model(self, config):

        """
        This function ...
        :param frame:
        :param config:
        :return:
        """

        pass

    # -----------------------------------------------------------------

    def remove(self, frame, mask, config):

        """
        This function ...
        :param frame:
        :param mask:
        :param config:
        :return:
        """

        # If a segment was found that can be identified with a source
        if self.has_source or config.remove_if_undetected:

            # Estimate the background
            self.source.estimate_background(config.interpolation_method, config.sigma_clip)

            # Replace the frame with the estimated background
            self.source.background.replace(frame, where=self.source.mask)

            # Update the mask
            mask[self.source.cutout.y_slice, self.source.cutout.x_slice] += self.source.mask

# -----------------------------------------------------------------