#!/usr/bin/env python
# -*- coding: utf8 -*-
# *****************************************************************
# **       PTS -- Python Toolkit for working with SKIRT          **
# **       © Astronomical Observatory, Ghent University          **
# *****************************************************************

## \package pts.modeling.data.images Contains the ImageFetcher class.

# -----------------------------------------------------------------

# Ensure Python 3 compatibility
from __future__ import absolute_import, division, print_function

# Import standard modules
from collections import defaultdict

# Import the relevant PTS classes and modules
from .component import DataComponent
from ...dustpedia.core.database import DustPediaDatabase, get_account
from ...core.tools.logging import log
from ...core.tools import filesystem as fs
from ...dustpedia.core.galex import GALEXMosaicMaker
from ...dustpedia.core.sdss import SDSSMosaicMaker

# -----------------------------------------------------------------

class ImageFetcher(DataComponent):
    
    """
    This class...
    """

    def __init__(self, config=None):

        """
        The constructor ...
        :param config:
        :return:
        """

        # Call the constructor of the base class
        super(ImageFetcher, self).__init__(config)

        # -- Attributes --

        # The DustPedia database
        self.database = DustPediaDatabase()

        # The names of the images found on the DustPedia archive, for each observatory
        self.dustpedia_image_names = defaultdict(list)

        # The images
        #self.images = []

    # -----------------------------------------------------------------

    def run(self):

        """
        This function ...
        :return:
        """

        # 1. Call the setup function
        self.setup()

        # 2. Fetch the images from the DustPedia archive
        self.get_dustpedia_names()

        # 3. Fetch GALEX data and calculate poisson errors
        self.fetch_galex()

        # 4. Fetch SDSS data and calculate poisson errors
        self.fetch_sdss()

        # 5. Fetch the H-alpha image
        self.fetch_halpha()

        # 6.
        self.fetch_2mass()

        # 7.
        self.fetch_spitzer()

        # 8.
        self.fetch_wise()

        # 9.
        self.fetch_herschel()

        # 10. Writing
        self.write()

    # -----------------------------------------------------------------

    def setup(self):

        """
        This function ...
        :return:
        """

        # Call the setup function of the base class
        super(ImageFetcher, self).setup()

        # Get username and password for the DustPedia database
        if self.config.database.username is not None:
            username = self.config.database.username
            password = self.config.database.password
        else: username, password = get_account()

        # Login to the DustPedia database
        self.database.login(username, password)

    # -----------------------------------------------------------------

    def get_dustpedia_names(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Fetching the names of the images on the DustPedia database ...")

        # Get the image names
        all_names = self.database.get_image_names(self.ngc_id_nospaces)

        # Order the names per origin
        for origin in self.data_origins:
            for name in all_names:
                if origin in name: self.dustpedia_image_names[origin].append(name)

    # -----------------------------------------------------------------

    def fetch_galex(self):

        """
        This function ...
        :return:
        """

        # Loop over all GALEX images
        for name in self.dustpedia_image_names["GALEX"]:

            # Determine the path to the image file
            path = fs.join(self.data_path, name)

            # Download the image
            self.database.download_image(self.ngc_id_nospaces, name, path)

    # -----------------------------------------------------------------

    def fetch_sdss(self):

        """
        This function ...
        :return:
        """

        # Loop over all GALEX images
        for name in self.dustpedia_image_names["SDSS"]:

            # Determine the path to the image file
            path = fs.join(self.data_path, name)

            # Download the image
            self.database.download_image(self.ngc_id_nospaces, name, path)

    # -----------------------------------------------------------------

    def fetch_halpha(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Fetching the H-alpha image ...")

    # -----------------------------------------------------------------

    def fetch_2mass(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Fetching the ...")

    # -----------------------------------------------------------------

    def fetch_spitzer(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Fetching the ...")

    # -----------------------------------------------------------------

    def fetch_wise(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Fetching the ...")

    # -----------------------------------------------------------------

    def fetch_herschel(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Fetching the ...")

    # -----------------------------------------------------------------

    def write(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Writing ...")

# -----------------------------------------------------------------
