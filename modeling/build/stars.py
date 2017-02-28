#!/usr/bin/env python
# -*- coding: utf8 -*-
# *****************************************************************
# **       PTS -- Python Toolkit for working with SKIRT          **
# **       © Astronomical Observatory, Ghent University          **
# *****************************************************************

## \package pts.modeling.build.stars Contains the StarsBuilder class.

# -----------------------------------------------------------------

# Ensure Python 3 compatibility
from __future__ import absolute_import, division, print_function

# Import standard modules
import math

# Import the relevant PTS classes and modules
from .component import BuildComponent
from ...core.tools.logging import log
from ...core.basics.configuration import ConfigurationDefinition
from ...core.basics.configuration import InteractiveConfigurationSetter
from ...core.basics.unit import parse_unit as u

# -----------------------------------------------------------------

class StarsBuilder(BuildComponent):
    
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
        super(StarsBuilder, self).__init__(config)

    # -----------------------------------------------------------------

    def run(self):

        """
        This function ...
        :return:
        """

        # 1. Call the setup function
        self.setup()

        # 2. Build bulge
        if self.config.bulge: self.build_bulge()

        # 3. Set the evolved stellar disk component
        if self.config.old: self.build_old()

        # 4. Set the young stellar component
        if self.config.young: self.build_young()

        # 5. Set the ionizing stellar component
        if self.config.ionizing: self.build_ionizing()

        # 6. Build additional stellar components
        if self.config.additional: self.build_additional()

        # 7. Write
        self.write()

    # -----------------------------------------------------------------

    def setup(self):

        """
        This function ...
        :return:
        """

        # Call the setup function of the base class
        super(StarsBuilder, self).setup()

    # -----------------------------------------------------------------

    def build_bulge(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Configuring the bulge component ...")

        # Like M31
        bulge_template = "BruzualCharlot"
        bulge_age = 12
        bulge_metallicity = 0.03

        # Get the flux density of the bulge
        fluxdensity = self.bulge2d_model.fluxdensity

        # Create definition
        definition = ConfigurationDefinition()
        definition.add_optional("template", "string", "template SED family", default=bulge_template, choices=[bulge_template])
        definition.add_optional("age", "positive_real", "age in Gyr", default=bulge_age)
        definition.add_optional("metallicity", "positive_real", "metallicity", default=bulge_metallicity)
        definition.add_optional("fluxdensity", "photometric_quantity", default=fluxdensity)

        # Prompt for the values
        setter = InteractiveConfigurationSetter("bulge")
        config = setter.run(definition)

        # Convert the flux density into a spectral luminosity
        luminosity = fluxdensity_to_luminosity(fluxdensity, self.i1_filter.pivot, self.galaxy_properties.distance)

    # -----------------------------------------------------------------

    def build_old(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Configuring the old stellar component ...")

        # Like M31
        disk_template = "BruzualCharlot"
        disk_age = 8
        # disk_metallicity = 0.02
        disk_metallicity = 0.03

        # Get the scale height
        # scale_height = 521. * Unit("pc") # first models
        scale_height = self.disk2d_model.scalelength / 8.26  # De Geyter et al. 2014
        bulge_fluxdensity = self.bulge2d_model.fluxdensity

        # Get the 3.6 micron flux density with the bulge subtracted
        fluxdensity = self.observed_flux(self.i1_filter, unit="Jy") - bulge_fluxdensity

        # Create definition
        definition = ConfigurationDefinition()
        definition.add_optional("template", "string", "template SED family", default=disk_template, choices=[disk_template])
        definition.add_optional("age", "positive_real", "age in Gyr", default=disk_age)
        definition.add_optional("metallicity", "positive_real", "metallicity", default=disk_metallicity)
        definition.add_optional("scale_height", "quantity", "scale height", default=scale_height)
        definition.add_optional("fluxdensity", "photometric_quantity", "flux density", default=fluxdensity)

        # Prompt for the values
        setter = InteractiveConfigurationSetter("old stellar disk")
        config = setter.run(definition)

        # Convert the flux density into a spectral luminosity
        luminosity = fluxdensity_to_luminosity(fluxdensity, self.i1_filter.pivot, self.galaxy_properties.distance)

        ## NEW: SET FIXED PARAMETERS
        #self.fixed["metallicity"] = disk_metallicity
        #self.fixed["old_scaleheight"] = scale_height
        #self.fixed["i1_old"] = luminosity
        ##

        # Get the spectral luminosity in solar units
        # luminosity = luminosity.to(self.sun_i1).value

        # Set the parameters of the evolved stellar component
        deprojection = self.deprojection.copy()
        deprojection.filename = self.old_stellar_map_filename
        deprojection.scale_height = scale_height
        self.deprojections["old stars"] = deprojection

        # Adjust the ski file
        #self.ski_template.set_stellar_component_geometry("Evolved stellar disk", deprojection)
        #self.ski_template.set_stellar_component_sed("Evolved stellar disk", disk_template, disk_age, disk_metallicity)  # SED
        # self.ski.set_stellar_component_luminosity("Evolved stellar disk", luminosity, self.i1) # normalization by band
        #self.ski_template.set_stellar_component_luminosity("Evolved stellar disk", luminosity, self.i1_filter.centerwavelength() * u("micron"))

    # -----------------------------------------------------------------

    def build_young(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Configuring the young stellar component ...")

        # Like M31
        young_template = "BruzualCharlot"
        young_age = 0.1
        # young_metallicity = 0.02
        young_metallicity = 0.03

        # Get the scale height
        # scale_height = 150 * Unit("pc") # first models
        scale_height = 100. * u("pc")  # M51

        # Get the FUV flux density
        fluxdensity = 2. * self.observed_flux(self.fuv_filter, unit="Jy")

        # Convert the flux density into a spectral luminosity
        luminosity = fluxdensity_to_luminosity(fluxdensity, self.fuv_filter.pivot, self.galaxy_properties.distance)

        # Get the spectral luminosity in solar units
        # luminosity = luminosity.to(self.sun_fuv).value # for normalization by band

        ## NEW: SET FIXED PARAMETERS
        #self.fixed["young_scaleheight"] = scale_height
        ##

        # Set the parameters of the young stellar component
        deprojection = self.deprojection.copy()
        deprojection.filename = self.young_stellar_map_filename
        deprojection.scale_height = scale_height
        self.deprojections["young stars"] = deprojection

        # Adjust the ski file
        #self.ski_template.set_stellar_component_geometry("Young stars", deprojection)
        #self.ski_template.set_stellar_component_sed("Young stars", young_template, young_age, young_metallicity)  # SED
        # self.ski.set_stellar_component_luminosity("Young stars", luminosity, self.fuv) # normalization by band
        # self.ski_template.set_stellar_component_luminosity("Young stars", luminosity, self.fuv_filter.centerwavelength() * u("micron"))

        # SET NORMALIZATION (IS FREE PARAMETER)
        #self.ski_template.set_stellar_component_normalization_wavelength("Young stars", self.fuv_filter.centerwavelength() * u("micron"))
        #self.ski_template.set_labeled_value("fuv_young", luminosity)

    # -----------------------------------------------------------------

    def build_ionizing(self):

        """
        This function ...
        :return:
        """

    # -----------------------------------------------------------------

    def build_additional(self):

        """
        This function ...
        :return:
        """

    # -----------------------------------------------------------------

    def write(self):

        """
        This function ...
        :return:
        """

# -----------------------------------------------------------------

# The speed of light
speed_of_light = constants.c

# -----------------------------------------------------------------

def spectral_factor_hz_to_micron(wavelength):

    """
    This function ...
    :param wavelength:
    :return:
    """

    wavelength_unit = "micron"
    frequency_unit = "Hz"

    # Convert string units to Unit objects
    if isinstance(wavelength_unit, basestring): wavelength_unit = u(wavelength_unit)
    if isinstance(frequency_unit, basestring): frequency_unit = u(frequency_unit)

    conversion_factor_unit = wavelength_unit / frequency_unit

    # Calculate the conversion factor
    factor = (wavelength ** 2 / speed_of_light).to(conversion_factor_unit).value
    return 1. / factor

# -----------------------------------------------------------------

def fluxdensity_to_luminosity(fluxdensity, wavelength, distance):

    """
    This function ...
    :param fluxdensity:
    :param wavelength:
    :param distance:
    :return:
    """

    luminosity = (fluxdensity * 4. * math.pi * distance ** 2.).to("W/Hz")

    # 3 ways:
    #luminosity_ = luminosity.to("W/micron", equivalencies=spectral_density(wavelength)) # does not work
    luminosity_ = (speed_of_light * luminosity / wavelength**2).to("W/micron")
    luminosity = luminosity.to("W/Hz").value * spectral_factor_hz_to_micron(wavelength) * u("W/micron")
    #print(luminosity_, luminosity) # is OK!

    return luminosity

# -----------------------------------------------------------------
