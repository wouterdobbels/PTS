#!/usr/bin/env python
# -*- coding: utf8 -*-
# *****************************************************************
# **       PTS -- Python Toolkit for working with SKIRT          **
# **       © Astronomical Observatory, Ghent University          **
# *****************************************************************

## \package pts.modeling.fitting.modelgenerators.genetic Contains the GeneticModelGenerator class.

# -----------------------------------------------------------------

# Ensure Python 3 compatibility
from __future__ import absolute_import, division, print_function

# Import the relevant PTS classes and modules
from ....core.tools.logging import log
from .generator import ModelGenerator
from ....core.tools import filesystem as fs
from ....evolve.optimize.stepwise import StepWiseOptimizer
from ....evolve.optimize.continuous import ContinuousOptimizer
from ..evaluate import evaluate
from ....core.tools.stringify import tostr

# -----------------------------------------------------------------

class GeneticModelGenerator(ModelGenerator):

    """
    This function ...
    """

    def __init__(self, config=None, interactive=False):

        """
        The constructor ...
        :param interactive:
        """

        # Call the constructor of the base class
        super(GeneticModelGenerator, self).__init__(config, interactive)

        # The scores (only if this is not the initial generation)
        self.scores = None
        self.scores_check = None

        # The optimizer
        self.optimizer = None

        # Whether or not this is the initial generation
        self.initial = None

        # The evaluator function and its kwargs
        self.evaluator = None
        self.evaluator_kwargs = None

        # The names of the individuals
        self.individual_names = None

        # The parameter ranges
        self.parameter_ranges = None

    # -----------------------------------------------------------------

    def setup(self, **kwargs):

        """
        This function ...
        :param kwargs:
        :return:
        """

        # Call the constructor of the base class
        super(GeneticModelGenerator, self).setup(**kwargs)

        # Get the fitting run
        self.fitting_run = kwargs.pop("fitting_run")

        # If the number of generations in one run is more than one
        if self.config.ngenerations > 1:

            # Create a new continuous optimizer
            self.optimizer = ContinuousOptimizer()
            self.optimizer.config.output = self.fitting_run.path
            #self.optimizer.config.writing.engine_path = self.fitting_run.main_engine_path
            #self.optimizer.config.writing.prng_path = self.fitting_run.main_prng_path
            #self.optimizer.config.writing.config_path = self.fitting_run.optimizer_config_path
            #self.optimizer.config.writing.statistics_path = self.statistics_path
            #self.optimizer.config.writing.database_path = self.database_path

            self.optimizer.config.run_id = self.fitting_run.name

            # Set initial flag
            self.initial = True

            # Set the evaluator function
            self.evaluator = evaluate

            # Set the evaluator kwargs
            self.evaluator_kwargs = dict()
            self.evaluator_kwargs["fitting_run"] = self.fitting_run #self.fitting_run.name

        else:

            # Re-invoke existing optimizer run
            if fs.is_file(self.fitting_run.main_engine_path):

                # Load the optimizer from files
                self.optimizer = StepWiseOptimizer.from_paths(self.fitting_run.path,
                                                                self.fitting_run.main_engine_path,
                                                                self.fitting_run.main_prng_path,
                                                                self.fitting_run.optimizer_config_path,
                                                                self.statistics_path, self.database_path, self.fitting_run.name)
                # Set initial flag
                self.initial = False

            # New optimizer run
            else:

                # Create a new optimizer and set paths
                self.optimizer = StepWiseOptimizer()
                self.optimizer.config.output = self.fitting_run.path
                self.optimizer.config.writing.engine_path = self.fitting_run.main_engine_path
                self.optimizer.config.writing.prng_path = self.fitting_run.main_prng_path
                self.optimizer.config.writing.config_path = self.fitting_run.optimizer_config_path
                self.optimizer.config.writing.statistics_path = self.statistics_path
                self.optimizer.config.writing.database_path = self.database_path
                self.optimizer.config.run_id = self.fitting_run.name

                # Set initial flag
                self.initial = True

        # Get the parameter ranges
        if "parameter_ranges" in kwargs: self.parameter_ranges = kwargs.pop("parameter_ranges")

        # Set parameters
        self.set_parameters()

        # Set settings
        self.set_optimizer_settings()

    # -----------------------------------------------------------------

    def set_parameters(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Setting the parameter ranges ...")

        # Loop over the free parameters
        for label in self.fitting_run.free_parameter_labels:

            # Get range (=default range)
            default_parameter_range = self.fitting_run.free_parameter_ranges[label]

            # Get the name of the last generation
            # DOESN'T WORK: SEE BELOW WHY
            #generation_name = get_last_generation_name(self.fitting_run)

            # DOESN'T WORK: the generations table has not been updated at this point: only when write() is called from the ParameterExplorer (parent to this class)
            # parameter_range = self.fitting_run.parameter_ranges_for_generation(generation_name, label)

            # Set the parameter range
            if self.parameter_ranges is not None and label in self.parameter_ranges: parameter_range = self.parameter_ranges[label]
            else: parameter_range = default_parameter_range

            # Debugging
            log.debug("Parameter '" + label + "':")
            log.debug("")
            log.debug(" - default range: " + tostr(default_parameter_range))
            log.debug(" - range for this generation: " + tostr(parameter_range))
            log.debug("")

            # Add the parameter
            self.add_parameter(label, parameter_range)

    # -----------------------------------------------------------------

    def set_optimizer_settings(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Setting the settings for the optimizer ...")

        # Set the settings
        set_optimizer_settings(self.optimizer, self.fitting_run, self.config.ngenerations, self.config.nmodels)

    # -----------------------------------------------------------------

    def generate(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Generating the new models ...")

        # Set the scores
        if not self.initial: self.set_scores()

        # Run the optimizer
        self.optimizer.run(scores=self.scores, scores_check=self.scores_check, minima=self.parameter_minima_scalar,
                           maxima=self.parameter_maxima_scalar, evaluator=self.evaluator, evaluator_kwargs=self.evaluator_kwargs)

        # Get the parameter values of the new models
        self.get_model_parameters_named_individuals()
        #self.get_model_parameters_unnamed_individuals()

    # -----------------------------------------------------------------

    def set_scores(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Setting scores from previous generation ...")

        # Get the scores (and check)
        self.scores, self.scores_check = get_last_generation_scores(self.fitting_run)

    # -----------------------------------------------------------------

    def get_model_parameters_named_individuals(self):

        """
        THis function ...
        :return: 
        """

        # Inform the user
        log.info("Getting the model parameters ...")

        # Set the individual names
        self.individual_names = self.optimizer.population.names

        # Loop over the individual names
        for name in self.individual_names:

            # Get the individual
            individual = self.optimizer.population[name]

            # Loop over all the genes (parameters)
            for i in range(len(individual)):

                # Get the parameter value
                value = individual[i]

                # Add the parameter value to the dictionary
                self.parameters[self.fitting_run.free_parameter_labels[i]][name] = value

    # -----------------------------------------------------------------

    def get_model_parameters_unnamed_individuals(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Getting the model parameters ...")

        # Loop over the individuals of the population
        for individual in self.optimizer.population:

            # Loop over all the genes (parameters)
            for i in range(len(individual)):

                # Get the parameter value
                value = individual[i]

                # Add the parameter value to the dictionary
                self.parameters[self.fitting_run.free_parameter_labels[i]].append(value)

    # -----------------------------------------------------------------

    def write(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Writing ...")

        # Write the state of the optimizer
        #self.write_optimizer()

# -----------------------------------------------------------------

def set_optimizer_settings(optimizer, fitting_run, ngenerations=None, nmodels=None):

    """
    This function ...
    :param optimizer: 
    :param fitting_run: 
    :param ngenerations:
    :param nmodels:
    :return: 
    """

    ## In order of optimizer configuration

    # Parameters
    optimizer.config.nparameters = fitting_run.nfree_parameters

    # Number of generations and the number of individuals per generation
    optimizer.config.ngenerations = ngenerations
    optimizer.config.nindividuals = nmodels

    # User
    optimizer.config.mutation_rate = fitting_run.genetic_settings.mutation_rate
    optimizer.config.crossover_rate = fitting_run.genetic_settings.crossover_rate

    # Fixed
    optimizer.config.stats_freq = 1
    optimizer.config.best_raw_score = 0.

    # User
    optimizer.config.round_decimal = fitting_run.genetic_settings.round_decimal
    optimizer.config.mutation_method = fitting_run.genetic_settings.mutation_method

    # User, scaling
    optimizer.config.scaling_method = fitting_run.genetic_settings.scaling_method

    # User, selector
    optimizer.config.selector_method = fitting_run.genetic_settings.selector_method

    # Fixed
    optimizer.config.min_or_max = "minimize"
    # self.optimizer.config.run_id = self.fitting_run.name # THIS IS NOW DONE IN THE SETUP
    optimizer.config.database_frequency = 1
    optimizer.config.statistics_frequency = 1

    # Fixed
    # self.optimizer.config.output = self.fitting_run.path

    # Fixed
    optimizer.config.elitism = True

    # Fixed
    optimizer.config.nelite_individuals = fitting_run.genetic_settings.nelite_individuals

    # Set heterogeneous flag
    optimizer.config.heterogeneous = True

    # Set named_individuals flag
    optimizer.config.named_individuals = True

# -----------------------------------------------------------------

def get_last_generation_name(fitting_run, or_initial=True):

    """
    This function ...
    :param fitting_run: 
    :param or_initial: 
    :return: 
    """

    # Get the corresponding generation name
    if or_initial: generation_name = fitting_run.last_genetic_or_initial_generation_name
    else: generation_name = fitting_run.last_genetic_generation_name

    # Return the name
    return generation_name

# -----------------------------------------------------------------

def get_last_generation_scores(fitting_run, or_initial=True):

    """
    This function ...
    :param fitting_run:
    :param or_initial:
    :return: 
    """

    # Get the generation name
    generation_name = get_last_generation_name(fitting_run, or_initial=or_initial)

    # Load the parameters table from the previous generation
    parameters_table = fitting_run.parameters_table_for_generation(generation_name)

    # Load the chi squared table from the previous generation
    chi_squared_table = fitting_run.chi_squared_table_for_generation(generation_name)

    # List of chi squared values in the same order as the parameters table
    chi_squared_values = []

    # Check whether the chi-squared and parameter tables match
    for i in range(len(parameters_table)):
        simulation_name = parameters_table["Simulation name"][i]
        chi_squared = chi_squared_table.chi_squared_for(simulation_name)
        chi_squared_values.append(chi_squared)

    # Check individual values with parameter table of the last generation
    check = []
    for label in fitting_run.free_parameter_labels:
        values = parameters_table[label]
        check.append(values)

    # Set the scores
    scores = chi_squared_values

    # Return
    return scores, check

# -----------------------------------------------------------------
