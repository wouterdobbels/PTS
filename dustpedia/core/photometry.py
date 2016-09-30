#!/usr/bin/env python
# -*- coding: utf8 -*-
# *****************************************************************
# **       PTS -- Python Toolkit for working with SKIRT          **
# **       © Astronomical Observatory, Ghent University          **
# *****************************************************************

## \package pts.dustpedia.core.photometry Contains the DustPediaPhotometry class.

# -----------------------------------------------------------------

# Ensure Python 3 compatibility
from __future__ import absolute_import, division, print_function

# Import standard modules
import requests
from lxml import html

# Import astronomical modules
from astropy.table import Table

# Import the relevant PTS classes and modules
from ...core.tools.logging import log
from ...core.tools import introspection
from ...core.tools import filesystem as fs
from ...core.tools import tables
from ...core.basics.filter import Filter
from ...modeling.core.sed import ObservedSED

# -----------------------------------------------------------------

dustpedia_dat_path = fs.join(introspection.pts_dat_dir("dustpedia"))

# -----------------------------------------------------------------

dustpedia_photometry_path = fs.join(dustpedia_dat_path, "photometry")

# -----------------------------------------------------------------

ap_phot_table_path = fs.join(dustpedia_photometry_path, "DustPedia_Aperture_Photometry.csv")
iras_scanpi_phot_table_path = fs.join(dustpedia_photometry_path, "DustPedia_IRAS_SCANPI.csv")
planck_phot_table_path = fs.join(dustpedia_photometry_path, "DustPedia_Planck_CCS2.csv")

# -----------------------------------------------------------------

# CHRIS:
#
# I'm very pleased to say that the DustPedia photometry is now ready for everyone to enjoy! The files are attached.
#
# There is a short(ish) PDF describing the photometry, along with 3 tables. One main table of aperture-matched
# photometry, one table of supplementary Planck catalogue photometry, and one table of supplementary IRAS photometry.
#
# Also, I have transferred to Manolis the PNG image grids (described in the PDF) showing for each source the
# apertures in all bands for which aperture photometry is performed; these should hopefully be accessible to everyone
# on the database soon.
#
# Please feel free to send me any questions you have. I wouldn't be surprised if there are a few small issues
# still hidden in the photometry, that my checks haven't found. So please report back anything odd you might find!

# -----------------------------------------------------------------

leda_search_object_url = "http://leda.univ-lyon1.fr/ledacat.cgi?"

# -----------------------------------------------------------------

non_flux_columns = ["name", "ra", "dec", "semimaj_arcsec", "axial_ratio", "pos_angle", "global_flag"]

# -----------------------------------------------------------------

class DustPediaPhotometry(object):

    """
    This class ...
    """

    def __init__(self):

        """
        The constructor ...
        """

        self.aperture = Table.read(ap_phot_table_path)
        self.iras_scanpi = Table.read(iras_scanpi_phot_table_path)
        self.planck = Table.read(planck_phot_table_path)

        self.aperture_filters = dict()
        self.iras_filters = dict()
        self.planck_filters = dict()

        self.set_filters()

    # -----------------------------------------------------------------

    def set_filters(self):

        """
        This function ...
        :return:
        """

        # APERTURE

        for colname in self.aperture.colnames:

            if colname in non_flux_columns: continue

            if colname.endswith("_err") or colname.endswith("_flag"): continue

            fltr = Filter.from_string(colname)

            self.aperture_filters[colname] = fltr

        # IRAS

        for colname in self.iras_scanpi.colnames:

            if colname in non_flux_columns: continue
            if colname.endswith("_err") or colname.endswith("_flag"): continue

            fltr = Filter.from_string(colname)

            self.iras_filters[colname] = fltr

        # PLANCK

        for colname in self.planck.colnames:

            if colname in non_flux_columns: continue
            if colname.endswith("_err") or colname.endswith("_flag"): continue

            fltr = Filter.from_string(colname)

            self.planck_filters[colname] = fltr

    # -----------------------------------------------------------------

    def get_hyperleda_name(self, galaxy_name):

        """
        This function ...
        :param galaxy_name:
        :return:
        """

        url = leda_search_object_url + galaxy_name

        page_as_string = requests.get(url).content

        tree = html.fromstring(page_as_string)

        tables = [e for e in tree.iter() if e.tag == 'table']

        table = tables[1]

        table_rows = [e for e in table.iter() if e.tag == 'tr']
        column_headings = [e.text_content() for e in table_rows[0].iter() if e.tag == 'th']

        #return table_rows, column_headings

        objname = str(table_rows[1].text_content().split("\n")[1]).strip()

        return objname

    # -----------------------------------------------------------------

    def get_sed(self, galaxy_name, add_iras=True, add_planck=True):
            
        """
        This function ...
        :param galaxy_name:
        :param add_iras:
        :param add_planck:
        """

        objname = self.get_hyperleda_name(galaxy_name)

        index = tables.find_index(self.aperture, objname, "name")

        filters = []
        fluxes = []
        errors = []

        for colname in self.aperture_filters:

            # Masked entry
            if hasattr(self.aperture[colname], "mask") and self.aperture[colname].mask[index]: continue

            flux = self.aperture[colname][index]

            filters.append(self.aperture_filters[colname])
            fluxes.append(flux)

            if colname + "_err" in self.aperture.colnames:
                errors.append(self.aperture[colname + "_err"][index])
            else: errors.append(None)

        index = tables.find_index(self.iras_scanpi, objname, "name")

        # Add IRAS
        if add_iras:

            for colname in self.iras_filters:

                # Masked entry
                if hasattr(self.iras_scanpi[colname], "mask") and self.iras_scanpi[colname].mask[index]: continue

                flux = self.iras_scanpi[colname][index]

                # Filter and flux
                filters.append(self.iras_filters[colname])
                fluxes.append(flux)

                # Add error
                if colname + "_err" in self.iras_scanpi.colnames:
                    errors.append(self.iras_scanpi[colname + "_err"][index])
                else: errors.append(None)

        index = tables.find_index(self.planck, objname, "name")

        # Add Planck fluxes
        if add_planck:

            for colname in self.planck_filters:

                # Masked entry
                if hasattr(self.planck[colname], "mask") and self.planck[colname].mask[index]: continue

                flux = self.planck[colname][index]

                filters.append(self.planck_filters[colname])
                fluxes.append(flux)

                if colname + "_err" in self.planck.colnames:
                    errors.append(self.planck[colname + "_err"][index])
                else: errors.append(None)

        sed = ObservedSED()

        for i in range(len(filters)):
            sed.add_entry(filters[i], fluxes[i], errors[i])

        return sed

# -----------------------------------------------------------------