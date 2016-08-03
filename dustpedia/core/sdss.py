#!/usr/bin/env python
# -*- coding: utf8 -*-
# *****************************************************************
# **       PTS -- Python Toolkit for working with SKIRT          **
# **       © Astronomical Observatory, Ghent University          **
# *****************************************************************

## \package pts.dustpedia.core.sdss Contains the SDSSMosaicMaker class.

# -----------------------------------------------------------------

# Ensure Python 3 compatibility
from __future__ import absolute_import, division, print_function

# Import the relevant PTS classes and modules
from ...core.basics.configurable import Configurable
from ...core.tools.logging import log
from .dataprocessing import DustPediaDataProcessing
from ...core.tools import filesystem as fs

# -----------------------------------------------------------------

sdss_bands = ["u", "g", "r", "i", "z"]

# -----------------------------------------------------------------

class SDSSMosaicMaker(Configurable):

    """
    This class ...
    """

    def __init__(self, config=None):

        """
        This function ...
        """

        # Call the constructor of the base class
        super(SDSSMosaicMaker, self).__init__(config)

        # The DustPedia data processing instance
        self.dpdp = None

    # -----------------------------------------------------------------

    def run(self):

        """
        This function ...
        :return:
        """

        # 1. Call the setup function
        self.setup()

        # 2. Do the mosaicing
        self.mosaic()

    # -----------------------------------------------------------------

    def setup(self):

        """
        This function ...
        :return:
        """

        # Call the setup function of the base class
        super(SDSSMosaicMaker, self).setup()

        # Create the DustPedia data processing instance
        self.dpdp = DustPediaDataProcessing()

    # -----------------------------------------------------------------

    def mosaic(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Making the SDSS " + self.config.band + " mosaic ...")

        # If the band is not specified, do all bands
        if self.config.band is None:

            # Loop over all bands and make the mosaics and Poisson frames
            for band in sdss_bands:

                # Create an output directory for the results of this band
                output_path = fs.join(self.output_path, band)
                fs.create_directory(output_path)

                # Make the mosaic and Poisson error frame
                self.dpdp.make_sdss_mosaic_and_poisson_frame(self.config.galaxy_name, band, output_path)

        # Make
        else:

            # Make the mosaic for the specified band
            output_path = self.output_path
            self.dpdp.make_sdss_mosaic_and_poisson_frame(self.config.galaxy_name, self.config.band, output_path)

# -----------------------------------------------------------------
