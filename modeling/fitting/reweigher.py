#!/usr/bin/env python
# -*- coding: utf8 -*-
# *****************************************************************
# **       PTS -- Python Toolkit for working with SKIRT          **
# **       © Astronomical Observatory, Ghent University          **
# *****************************************************************

## \package pts.modeling.fitting.reweigher Contains the Reweigher class

# -----------------------------------------------------------------

# Ensure Python 3 compatibility
from __future__ import absolute_import, division, print_function

# Import standard modules
import numpy as np
from collections import OrderedDict, defaultdict

# Import the relevant PTS classes and modules
from .component import FittingComponent
from ...core.basics.log import log
from .initialization.base import calculate_weights_filters
from ...core.tools.utils import lazyproperty
from .tables import WeightsTable
from ...core.tools import filesystem as fs
from ...core.tools import tables
from .modelanalyser import FluxDifferencesTable

# -----------------------------------------------------------------

earth_instrument_name = "earth"

# -----------------------------------------------------------------

class Reweigher(FittingComponent):
    
    """
    This class...
    """

    def __init__(self, *args, **kwargs):

        """
        The constructor ...
        :param kwargs:
        :return:
        """

        # Call the constructor of the base class
        super(Reweigher, self).__init__(*args, **kwargs)

        # -- Attributes --

        # The fitting run
        self.fitting_run = None

        # The table of weights for each band
        self.weights = None

        # The flux differences
        self.differences = defaultdict(lambda: defaultdict)

    # -----------------------------------------------------------------

    def run(self, **kwargs):

        """
        This function ...
        :param kwargs:
        :return:
        """

        # 1. Call the setup function
        self.setup(**kwargs)

        # 2. Calculate the new weights
        self.calculate_weights()

        # 2. Calculate the differences
        self.calculate_differences()

        # 3. Calculate the chi squared for this model
        self.calculate_chi_squared()

        # 2. Get the parameters of the best models for each generation
        self.get_best_parameters()

        # 3. Calculate the probabilities
        self.calculate_probabilities()

        # 4. Calculate the probability distributions
        self.create_distributions()

        # 3. Writing
        self.write()

        # Show
        if self.config.show: self.show()

        # Plot
        if self.config.plot: self.plot()

    # -----------------------------------------------------------------

    @lazyproperty
    def path(self):

        """
        This function ...
        :return:
        """

        return fs.create_directory_in(self.fitting_run.reweighing_path, self.config.name)

    # -----------------------------------------------------------------

    def setup(self, **kwargs):

        """
        This function ...
        :param kwargs:
        :return:
        """

        # Call the setup function of the base class
        super(Reweigher, self).setup(**kwargs)

        # Load the fitting run
        self.fitting_run = self.load_fitting_run(self.config.fitting_run)

        # Create the table to contain the weights
        self.weights = WeightsTable()

        # Only UV
        if self.config.only_uv:

            if self.config.no_uv: raise ValueError("Error")
            self.config.uv = 1.
            self.config.optical = self.config.nir = self.config.mir = self.config.fir = self.config.submm = 0.

        # Only optical
        if self.config.only_optical:

            if self.config.no_optical: raise ValueError("Error")
            self.config.optical = 1.
            self.config.uv = self.config.nir = self.config.mir = self.config.fir = self.config.submm = 0.

        # Only NIR
        if self.config.only_nir:

            if self.config.no_nir: raise ValueError("Error")
            self.config.nir = 1.
            self.config.uv = self.config.optical = self.config.mir = self.config.fir = self.config.submm = 0.

        # Only MIR
        if self.config.only_mir:

            if self.config.no_mir: raise ValueError("Error")
            self.config.mir = 1.
            self.config.uv = self.config.optical = self.config.nir = self.config.fir = self.config.submm = 0.

        # Only FIR
        if self.config.only_fir:

            if self.config.no_fir: raise ValueError("Error")
            self.config.fir = 1.
            self.config.uv = self.config.optical = self.config.nir = self.config.mir = self.config.submm = 0.

        # Only submm
        if self.config.only_submm:

            if self.config.no_submm: raise ValueError("Error")
            self.config.submm = 1.
            self.config.uv = self.config.optical = self.config.nir = self.config.mir = self.config.fir = 0.

        # Set weights
        if self.config.no_uv: self.config.uv = 0.
        if self.config.no_optical: self.config.optical = 0.
        if self.config.no_nir: self.config.nir = 0.
        if self.config.no_mir: self.config.mir = 0.
        if self.config.no_fir: self.config.fir = 0.
        if self.config.no_submm: self.config.submm = 0.

    # -----------------------------------------------------------------

    @lazyproperty
    def generation_names(self):

        """
        This function ...
        :return:
        """

        if self.config.generations is not None: return self.config.generations
        else: return self.fitting_run.generation_names

    # -----------------------------------------------------------------

    @lazyproperty
    def generations(self):

        """
        This function ...
        :return:
        """

        gens = OrderedDict()
        for name in self.generation_names: gens[name] = self.fitting_run.get_generation(name)
        return gens

    # -----------------------------------------------------------------

    @lazyproperty
    def filters(self):

        """
        This function ...
        :return:
        """

        if self.config.filters is not None: return self.config.filters
        else: return self.fitting_run.fitting_filters

    # -----------------------------------------------------------------

    def calculate_weights(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Calculating the weight to give to each band ...")

        # Get the weights
        weights = calculate_weights_filters(self.filters, uv=self.config.uv, optical=self.config.optical, nir=self.config.nir, mir=self.config.mir, fir=self.config.fir, submm=self.config.submm)

        # Add to weights table
        for fltr in weights: self.weights.add_point(fltr, weights[fltr])

    # -----------------------------------------------------------------

    def calculate_differences(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Calculating the differences between observed and simulated fluxes ...")

        # Loop over the generations
        for generation_name in self.generation_names:

            # Debugging
            log.debug("Calculating differences for the '" + generation_name + "' generation ...")

            # Get the generation
            generation = self.generations[generation_name]

            # Loop over the simulations
            for simulation in generation.analysed_simulations_basic:

                # Get simulation name
                simulation_name = simulation.name

                # Initialize the differences table
                differences = FluxDifferencesTable()

                # Get mock SED
                if generation.has_mock_sed(simulation_name): mock_sed = generation.get_simulation_mock_sed(simulation_name)
                else:



                # Loop over the entries in the fluxdensity table (SED) derived from the simulation
                for i in range(len(mock_sed)):

                    # Get instrument, band and flux density
                    instrument = mock_sed["Instrument"][i]
                    band = mock_sed["Band"][i]
                    fluxdensity = mock_sed["Photometry"][i]

                    # Find the corresponding flux in the SED derived from observation
                    observed_fluxdensity = self.observed_sed.photometry_for_band(instrument, band, unit="Jy").value

                    # Find the corresponding flux error in the SED derived from observation
                    observed_fluxdensity_error = self.observed_sed.error_for_band(instrument, band, unit="Jy").average.to("Jy").value

                    # If no match with (instrument, band) is found in the observed SED
                    if observed_fluxdensity is None:
                        log.warning("The observed flux density could not be found for the " + instrument + " " + band + " band")
                        continue

                    difference = fluxdensity - observed_fluxdensity
                    relative_difference = difference / observed_fluxdensity

                    # Find the index of the current band in the weights table
                    index = tables.find_index(self.weights, key=[instrument, band], column_name=["Instrument", "Band"])
                    if index is None: continue  # Skip this band if a weight is not found
                    weight = self.weights["Weight"][index]

                    # Calculate the chi squared term
                    chi_squared_term = weight * difference ** 2 / observed_fluxdensity_error ** 2

                    # Add entry to the table
                    differences.add_entry(instrument, band, difference, relative_difference, chi_squared_term)

                # Set table
                self.differences[generation_name][simulation_name] = differences

    # -----------------------------------------------------------------

    # @property
    # def ndifferences(self):
    #
    #     """
    #     This function ...
    #     :return:
    #     """
    #
    #     return len(self.differences)

    # -----------------------------------------------------------------

    @property
    def nfree_parameters(self):

        """
        This function ...
        :return:
        """

        return self.fitting_run.nfree_parameters

    # -----------------------------------------------------------------

    # @property
    # def ndof(self):
    #
    #     """
    #     This function ...
    #     :return:
    #     """
    #
    #     return self.ndifferences - self.nfree_parameters - 1 # number of data points - number of fitted parameters - 1

    # -----------------------------------------------------------------

    def calculate_chi_squared(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Calculating chi squared values ...")

        # Loop over the generations
        for generation_name in self.generation_names:

            # Loop over the simulations
            for simulation_name in self.differences[generation_name]:

                # Get the differences table
                differences = self.differences[generation_name][simulation_name]

                # Inform the user
                log.info("Calculating the chi squared value for this model ...")

                # The (reduced) chi squared value is the sum of all the terms (for each band),
                # divided by the number of degrees of freedom
                chi_squared = np.sum(differences["Chi squared term"]) / self.ndof

                # Debugging
                log.debug("Found a (reduced) chi squared value of " + str(chi_squared))

    # -----------------------------------------------------------------

    def get_best_parameters(self):

        """
        This function ...
        :return:
        """

    # -----------------------------------------------------------------

    def calculate_probabilities(self):

        """
        This function ...
        :return:
        """

    # -----------------------------------------------------------------

    def create_distributions(self):

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

        # Inform the user
        log.info("Writing ...")

        # Weights
        self.write_weights()

    # -----------------------------------------------------------------

    @property
    def weights_table_path(self):

        """
        This function ...
        :return:
        """

        return fs.join(self.path, "weights.dat")

    # -----------------------------------------------------------------

    def write_weights(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Writing the table with weights to " + self.weights_table_path + " ...")

        # Write the table with weights
        self.weights.saveto(self.weights_table_path)

    # -----------------------------------------------------------------

    def show(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Showing ...")

    # -----------------------------------------------------------------

    def plot(self):


        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Plotting ...")

# -----------------------------------------------------------------
