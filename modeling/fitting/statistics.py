#!/usr/bin/env python
# -*- coding: utf8 -*-
# *****************************************************************
# **       PTS -- Python Toolkit for working with SKIRT          **
# **       © Astronomical Observatory, Ghent University          **
# *****************************************************************

## \package pts.modeling.fitting.statistics Contains the FittingStatistics class.

# -----------------------------------------------------------------

# Ensure Python 3 compatibility
from __future__ import absolute_import, division, print_function

# Import standard modules
import numpy as np
from collections import OrderedDict

# Import the relevant PTS classes and modules
from ...core.basics.configurable import InteractiveConfigurable
from ...core.basics.configuration import ConfigurationDefinition
from ...core.basics.log import log
from ...core.tools.utils import lazyproperty
from ..core.environment import load_modeling_environment
from ...core.tools import strings
from ...core.plot.distribution import plot_distribution
from ...core.tools.utils import memoize_method
from .sedfitting import chi_squared_table_to_probabilities
from ...core.basics.distribution import Distribution
from ...core.plot.sed import SEDPlotter
from ...core.tools import sequences
from .refitter import show_best_simulations_impl
from ...core.plot.sed import plot_seds
from ...core.tools import formatting as fmt
from ...core.plot.distribution import plot_distributions
from ...core.tools.stringify import tostr, yes_or_no
from ...core.basics.containers import DefaultOrderedDict
from ...core.tools import filesystem as fs
from ...core.plot.transmission import plot_filters
from ...core.tools import types

# -----------------------------------------------------------------

# Standard commands
_help_command_name = "help"
_history_command_name = "history"
_status_command_name = "status"

# Commands
_generations_command_name = "generations"
_simulations_command_name = "simulations"
_best_command_name = "best"
_counts_command_name = "counts"
_parameters_command_name = "parameters"
_compare_command_name = "compare"
_closest_command_name = "closest"
_plot_command_name = "plot"

# Compare
_fluxes_command_name = "fluxes"

# Plotting
_terms_command_name = "terms"
_ranks_command_name = "ranks"
_chisquared_command_name = "chisquared"
_prob_command_name = "prob"
_seds_command_name = "seds"
_sed_command_name = "sed"
_filters_command_name = "filters"

# -----------------------------------------------------------------

# Define commands
commands = OrderedDict()

# Standard commands
commands[_help_command_name] = ("show_help", False, "show help", None)
commands[_history_command_name] = ("show_history_command", True, "show history of executed commands", None)
commands[_status_command_name] = ("show_status_command", True, "show generation status", None)

# Show stuff
commands[_generations_command_name] = ("show_generations", False, "show generations", None)
commands[_simulations_command_name] = ("show_simulations_command", True, "show simulations of a generation", "generation")
commands[_best_command_name] = ("show_best_command", True, "show best models", "generation")
commands[_counts_command_name] = ("show_counts_command", True, "show counts statistics", "generation")
commands[_parameters_command_name] = ("show_parameters_command", True, "show parameters statistics", "generation")

# Commands with subcommands
commands[_compare_command_name] = (None, None, "compare simulations", None)
commands[_closest_command_name] = (None, None, "compare closest simulations between generations", None)
commands[_plot_command_name] = (None, None, "plotting", None)

# -----------------------------------------------------------------

# Compare commands
compare_commands = OrderedDict()
compare_commands[_parameters_command_name] = ("compare_parameters_command", True, "compare parameters between two simulations", "two_generation_simulations")
compare_commands[_seds_command_name] = ("compare_seds_command", True, "compare SEDs between two simulations", "two_generation_simulations")
compare_commands[_fluxes_command_name] = ("compare_fluxes_command", True, "compare fluxes between two simulations", "two_generation_simulations")

# Closest commands
closest_commands = OrderedDict()
closest_commands[_parameters_command_name] = ("show_closest_parameters_command", True, "compare closest simulation parameters between generations", "two_generations")
closest_commands[_seds_command_name] = ("plot_closest_seds_command", True, "compare simulated SEDs of closest simulations between generations", "two_generations")
closest_commands[_fluxes_command_name] = ("plot_closest_fluxes_command", True, "compare mock fluxes of closest simulations between generations", "two_generations")

# -----------------------------------------------------------------

# Plot commands
plot_commands = OrderedDict()
plot_commands[_terms_command_name] = ("plot_terms_command", True, "plot the chi squared terms", "generation_simulation")
plot_commands[_ranks_command_name] = ("plot_ranks_command", True, "plot the chi squared as a function of rank", "generation")
plot_commands[_chisquared_command_name] = ("plot_chi_squared_command", True, "plot the distribution of chi squared values", "generation")
plot_commands[_prob_command_name] = ("plot_probabilities_command", True, "plot the distribution of probabilities", "generation")
plot_commands[_seds_command_name] = ("plot_seds_command", True, "plot the simulation SEDs of a generation", "generation")
plot_commands[_best_command_name] = ("plot_best_command", True, "plot the SEDs (simulated or mock) of the best simulation(s) of a generation", "generation")
plot_commands[_sed_command_name] = ("plot_sed_command", True, "plot the SED (simulated or mock) of a particular simulation", "generation_simulation")
plot_commands[_counts_command_name] = ("plot_counts_command", True, "plot the best parameter counts", "generation")
plot_commands[_filters_command_name] = ("plot_filters", False, "plot the fitting filters", None)

# Set subcommands
subcommands = OrderedDict()
subcommands[_compare_command_name] = compare_commands
subcommands[_closest_command_name] = closest_commands
subcommands[_plot_command_name] = plot_commands

# -----------------------------------------------------------------

simulated_choice = "simulated"
mock_choice = "mock"
simulated_or_mock = [simulated_choice, mock_choice]

chisquared_choice = "chisquared"
prob_choice = "prob"
chisquared_or_prob = [chisquared_choice, prob_choice]

# -----------------------------------------------------------------

class FittingStatistics(InteractiveConfigurable):
    
    """
    This class...
    """

    _commands = commands
    _subcommands = subcommands

    # -----------------------------------------------------------------

    def __init__(self, *args, **kwargs):

        """
        The constructor ...
        :param args:
        :param kwargs:
        :return:
        """

        # Call the constructor of the base class
        super(FittingStatistics, self).__init__(*args, **kwargs)

    # -----------------------------------------------------------------

    @property
    def do_commands(self):

        """
        This function ...
        :return:
        """

        return self.config.commands is not None and len(self.config.commands) > 0

    # -----------------------------------------------------------------

    @property
    def do_interactive(self):

        """
        This function ...
        :return:
        """

        return self.config.interactive

    # -----------------------------------------------------------------

    def run(self, **kwargs):

        """
        This function ...
        :param kwargs:
        :return:
        """

        # 1. Call the setup function
        self.setup(**kwargs)

        # 2. Run commands
        if self.do_commands: self.run_commands()

        # 3. Interactive
        if self.do_interactive: self.interactive()

        # 4. Show
        self.show()

        # 5. Write the history
        if self.has_commands: self.write_history()

    # -----------------------------------------------------------------

    def setup(self, **kwargs):

        """
        This function ...
        :param kwargs:
        :return:
        """

        # Call the setup function of the base class
        super(FittingStatistics, self).setup(**kwargs)

    # -----------------------------------------------------------------

    def get_generation_command_definition(self, command_definition=None, required_to_optional=True):

        """
        This function ...
        :param command_definition:
        :param required_to_optional:
        :return:
        """

        # Create definition
        definition = ConfigurationDefinition(write_config=False)
        definition.add_required("generation", "string", "generation name", choices=self.generation_names)

        # Add definition settings
        if command_definition is not None:
            if required_to_optional: definition.import_settings(command_definition, required_to="optional")
            else: definition.import_settings(command_definition)

        # Return the definition
        return definition

    # -----------------------------------------------------------------

    def parse_generation_command(self, command, command_definition=None, name=None, index=1, required_to_optional=True,
                                interactive=False):

        """
        This function ...
        :param command:
        :param command_definition:
        :param name:
        :param index:
        :param required_to_optional:
        :param interactive:
        :return:
        """

        # Parse
        splitted = strings.split_except_within_double_quotes(command, add_quotes=False)
        if name is None: name = splitted[0]

        # Set parse command
        if command_definition is not None: parse_command = splitted[index:]
        else: parse_command = splitted[index:index + 1]  # only generation name

        # Get the definition
        definition = self.get_generation_command_definition(command_definition, required_to_optional=required_to_optional)

        # Get the configuration
        config = self.get_config_from_definition(name, definition, parse_command, interactive=interactive)

        # Get generation name
        generation_name = config.pop("generation")

        # Return
        return splitted, generation_name, config

    # -----------------------------------------------------------------

    def get_generation_name_from_command(self, command, name=None, interactive=False):

        """
        This function ...
        :param command:
        :param name:
        :param interactive:
        :return:
        """

        # Parse the command
        splitted, generation_name, config = self.parse_generation_command(command, name=name, interactive=interactive)

        # Return the image name
        return generation_name

    # -----------------------------------------------------------------

    def get_generation_name_and_config_from_command(self, command, command_definition, name=None, interactive=False):

        """
        This function ...
        :param command:
        :param command_definition:
        :param name:
        :param interactive:
        :return:
        """

        # Parse the command
        splitted, generation_name, config = self.parse_generation_command(command, command_definition=command_definition, name=name, interactive=interactive)

        # Return image name and config
        return generation_name, config

    # -----------------------------------------------------------------

    def get_generation_simulation_command_definition(self, command_definition=None, required_to_optional=True):

        """
        This function ...
        :param command_definition:
        :param required_to_optional:
        :return:
        """

        # Create definition
        definition = ConfigurationDefinition(write_config=False)
        definition.add_required("generation", "string", "generation name", choices=self.generation_names)
        definition.add_required("simulation", "string", "simulation name")

        # Add definition settings
        if command_definition is not None:
            if required_to_optional: definition.import_settings(command_definition, required_to="optional")
            else: definition.import_settings(command_definition)

        # Return the definition
        return definition

    # -----------------------------------------------------------------

    def parse_generation_simulation_command(self, command, command_definition=None, name=None, index=1, required_to_optional=True, interactive=False):

        """
        This function ...
        :param command:
        :param command_definition:
        :param name:
        :param index:
        :param required_to_optional:
        :param interactive:
        :return:
        """

        # Parse
        splitted = strings.split_except_within_double_quotes(command, add_quotes=False)
        if name is None: name = splitted[0]

        # Set parse command
        if command_definition is not None: parse_command = splitted[index:]
        else: parse_command = splitted[index:index + 1]  # only generation name

        # Get the definition
        definition = self.get_generation_simulation_command_definition(command_definition, required_to_optional=required_to_optional)

        # Get the configuration
        config = self.get_config_from_definition(name, definition, parse_command, interactive=interactive)

        # Get generation name
        generation_name = config.pop("generation")
        simulation_name = config.pop("simulation")

        # Return
        return splitted, generation_name, simulation_name, config

    # -----------------------------------------------------------------

    def get_generation_name_and_simulation_name_from_command(self, command, name=None, interactive=False):

        """
        This function ...
        :param command:
        :param name:
        :param interactive:
        :return:
        """

        # Parse the command
        splitted, generation_name, simulation_name, config = self.parse_generation_simulation_command(command, name=name, interactive=interactive)

        # Return the names
        return generation_name, simulation_name

    # -----------------------------------------------------------------

    def get_generation_name_simulation_name_and_config_from_command(self, command, command_definition, name=None, interactive=False):

        """
        This function ...
        :param command:
        :param command_definition:
        :param name:
        :param interactive:
        :return:
        """

        # Parse the command
        splitted, generation_name, simulation_name, config = self.parse_generation_simulation_command(command, command_definition, name=name, interactive=interactive)

        # Return the names
        return generation_name, simulation_name, config

    # -----------------------------------------------------------------

    def get_two_generations_command_definition(self, command_definition=None, required_to_optional=True):

        """
        This function ...
        :param command_definition:
        :param required_to_optional:
        :return:
        """

        # Create definition
        definition = ConfigurationDefinition(write_config=False)
        definition.add_required("generation_a", "integer_or_string", "generation a index or name", choices=self.generation_names)
        definition.add_required("generation_b", "integer_or_string", "generation b index or name", choices=self.generation_names)

        # Add definition settings
        if command_definition is not None:
            if required_to_optional: definition.import_settings(command_definition, required_to="optional")
            else: definition.import_settings(command_definition)

        # Return the definition
        return definition

    # -----------------------------------------------------------------

    def parse_two_generations_command(self, command, command_definition=None, name=None, index=1, required_to_optional=True, interactive=False):

        """
        This function ...
        :param command:
        :param command_definition:
        :param name:
        :param index:
        :param required_to_optional:
        :param interactive:
        :return:
        """

        # Parse
        splitted = strings.split_except_within_double_quotes(command, add_quotes=False)
        if name is None: name = splitted[0]

        # Set parse command
        if command_definition is not None: parse_command = splitted[index:]
        else: parse_command = splitted[index:index + 1]  # only generation name

        # Get the definition
        definition = self.get_two_generations_command_definition(command_definition, required_to_optional=required_to_optional)

        # Get the configuration
        config = self.get_config_from_definition(name, definition, parse_command, interactive=interactive)

        # Get generation a name
        if types.is_integer_type(config.generation_a): generation_a_name = self.generation_names[config.generation_a]
        else: generation_a_name = config.generation_a

        # Get generation b name
        if types.is_integer_type(config.generation_b): generation_b_name = self.generation_names[config.generation_b]
        else: generation_b_name = config.generation_b

        # Return
        return splitted, generation_a_name, generation_b_name, config

    # -----------------------------------------------------------------

    def get_two_generation_names_from_command(self, command, name=None, interactive=False):

        """
        This function ...
        :param command:
        :param name:
        :param interactive:
        :return:
        """

        # Parse the command
        splitted, generation_a_name, generation_b_name, config = self.parse_two_generations_command(command, name=name, interactive=interactive)

        # Return the names
        return generation_a_name, generation_b_name

    # -----------------------------------------------------------------

    def get_two_generation_names_and_config_from_command(self, command, command_definition, name=None, interactive=False):

        """
        This function ...
        :param command:
        :param command_definition:
        :param name:
        :param interactive:
        :return:
        """

        # Parse the command
        splitted, generation_a_name, generation_b_name, config = self.parse_two_generations_command(command, command_definition, name=name, interactive=interactive)

        # Return the names
        return generation_a_name, generation_b_name, config

    # -----------------------------------------------------------------

    def get_two_generation_simulations_command_definition(self, command_definition=None, required_to_optional=True):
        
        """
        This function ...
        :param command_definition: 
        :param required_to_optional: 
        :return: 
        """

        # Create definition
        definition = ConfigurationDefinition(write_config=False)
        definition.add_required("generation_simulation_a", "integer_or_string_pair", "generation and simulation index or name of simulation a")
        definition.add_required("generation_simulation_b", "integer_or_string_pair", "generation and simulation index or name of simulation b")

        # Add definition settings
        if command_definition is not None:
            if required_to_optional: definition.import_settings(command_definition, required_to="optional")
            else: definition.import_settings(command_definition)

        # Return the definition
        return definition

    # -----------------------------------------------------------------

    def parse_two_generation_simulations_command(self, command, command_definition=None, name=None, index=1, required_to_optional=True, interactive=False):
        
        """
        This function ...
        :param command: 
        :param command_definition: 
        :param name: 
        :param index: 
        :param required_to_optional: 
        :param interactive: 
        :return: 
        """

        # Parse
        splitted = strings.split_except_within_double_quotes(command, add_quotes=False)
        if name is None: name = splitted[0]

        # Set parse command
        if command_definition is not None: parse_command = splitted[index:]
        else: parse_command = splitted[index:index + 1]  # only generation name

        # Get the definition
        definition = self.get_two_generation_simulations_command_definition(command_definition, required_to_optional=required_to_optional)

        # Get the configuration
        config = self.get_config_from_definition(name, definition, parse_command, interactive=interactive)

        # Get generation_simulation_a
        generation_simulation_a_name = (None, None)
        if types.is_integer_type(config.generation_simulation_a[0]): generation_simulation_a_name[0] = self.generation_names[config.generation_simulation_a[0]]
        else: generation_simulation_a_name[0] = config.generation_simulation_a[0]
        if types.is_integer_type(config.generation_simulation_a[1]): generation_simulation_a_name[1] = self.get_simulation_names(generation_simulation_a_name[0])[config.generation_simulation_a[1]]
        else: generation_simulation_a_name[1] = config.generation_simulation_a[1]

        # Get generation_simulation_b_name
        generation_simulation_b_name = (None, None)
        if types.is_integer_type(config.generation_simulation_b[0]): generation_simulation_b_name[0] = self.generation_names[config.generation_simulation_b[0]]
        else: generation_simulation_b_name[0] = config.generation_simulation_b[0]
        if types.is_integer_type(config.generation_simulation_b[1]): generation_simulation_b_name[1] = self.get_simulation_names(generation_simulation_b_name[0])[config.generation_simulation_b[1]]
        else: generation_simulation_b_name[1] = config.generation_simulation_b[1]

        # Return
        return splitted, generation_simulation_a_name, generation_simulation_b_name, config

    # -----------------------------------------------------------------

    def get_two_generation_simulation_names(self, command, name=None, interactive=False):

        """
        This function ...
        :param command:
        :param name:
        :param interactive:
        :return:
        """

        # Parse
        splitted, generation_simulation_a_name, generation_simulation_b_name, config = self.parse_two_generation_simulations_command(command, name=name, interactive=interactive)

        # Return
        return generation_simulation_a_name, generation_simulation_b_name

    # -----------------------------------------------------------------

    def get_two_generation_simulation_names_and_config_from_command(self, command, command_definition, name=None, interactive=False):

        """
        This function ...
        :param command:
        :param command_definition:
        :param name:
        :param interactive:
        :return:
        """

        # Parse
        splitted, generation_simulation_a_name, generation_simulation_b_name, config = self.parse_two_generation_simulations_command(command, command_definition, name=name, interactive=interactive)

        # Return
        return generation_simulation_a_name, generation_simulation_b_name, config

    # -----------------------------------------------------------------

    @lazyproperty
    def show_status_definition(self):

        """
        This function ...
        :return:
        """

        definition = ConfigurationDefinition(write_config=False)
        return definition

    # -----------------------------------------------------------------

    def show_status_command(self, command, **kwargs):

        """
        This function ...
        :param command:
        :param kwargs:
        :return:
        """

        # Get the config
        config = self.get_config_from_command(command, self.show_status_definition, **kwargs)

        # Show
        self.show_status(extra=config.extra_columns, path=config.path, refresh=config.refresh)

    # -----------------------------------------------------------------

    def show_status(self, extra=None, path=None, refresh=None):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Showing the generation status ...")

    # -----------------------------------------------------------------

    @lazyproperty
    def modeling_environment(self):

        """
        This function ...
        :return:
        """

        return load_modeling_environment(self.config.path)

    # -----------------------------------------------------------------

    @property
    def clipped_sed(self):

        """
        This function ...
        :return:
        """

        return self.modeling_environment.observed_sed

    # -----------------------------------------------------------------

    @property
    def truncated_sed(self):

        """
        This function ...
        :return:
        """

        return self.modeling_environment.truncated_sed

    # -----------------------------------------------------------------

    def get_reference_seds(self, additional_error=None):

        """
        This function ...
        :param additional_error:
        :return:
        """

        # Debugging
        log.debug("Loading the observed SEDs ...")

        # Create dictionary
        seds = OrderedDict()

        # Add relative error
        if additional_error is not None:
            clipped_sed = self.clipped_sed.copy()
            truncated_sed = self.truncated_sed.copy()
            clipped_sed.add_relative_error(additional_error)
            truncated_sed.add_relative_error(additional_error)
        else: clipped_sed, truncated_sed = self.clipped_sed, self.truncated_sed

        # Add observed SEDs
        seds["Clipped observed fluxes"] = clipped_sed
        seds["Truncated observed fluxes"] = truncated_sed

        # Return the seds
        return seds

    # -----------------------------------------------------------------

    @lazyproperty
    def fitting_runs(self):

        """
        This function ...
        :return:
        """

        return self.modeling_environment.fitting_runs

    # -----------------------------------------------------------------

    @lazyproperty
    def fitting_run(self):

        """
        This function ...
        :return:
        """

        return self.fitting_runs.load(self.config.run)

    # -----------------------------------------------------------------

    @property
    def fitting_filters(self):

        """
        This function ...
        :return:
        """

        return self.fitting_run.fitting_filters

    # -----------------------------------------------------------------

    @property
    def parameter_ranges(self):

        """
        This function ...
        :return:
        """

        return self.fitting_run.free_parameter_ranges

    # -----------------------------------------------------------------

    @property
    def parameter_labels(self):

        """
        This function ...
        :return:
        """

        return self.parameter_ranges.keys()

    # -----------------------------------------------------------------

    @property
    def parameter_units(self):

        """
        This function ...
        :return:
        """

        return self.fitting_run.parameter_units

    # -----------------------------------------------------------------

    def get_parameter_unit(self, label):

        """
        Thisf unction ...
        :param label:
        :return:
        """

        return self.parameter_units[label]

    # -----------------------------------------------------------------

    @property
    def initial_parameter_values(self):

        """
        This function ...
        :return:
        """

        return self.fitting_run.first_guess_parameter_values

    # -----------------------------------------------------------------

    @property
    def grid_settings(self):

        """
        This function ...
        :return:
        """

        return self.fitting_run.grid_settings

    # -----------------------------------------------------------------

    @lazyproperty
    def parameter_scales(self):

        """
        This function ...
        :return:
        """

        # Initialize dictionary for the scales
        scales = dict()

        # Get the scales for each free parameter
        for label in self.parameter_labels:
            key = label + "_scale"
            scales[label] = self.grid_settings[key]

        # Return the scales dict
        return scales

    # -----------------------------------------------------------------

    @property
    def timing_table(self):

        """
        This function ...
        :return:
        """

        return self.fitting_run.timing_table

    # -----------------------------------------------------------------

    @property
    def memory_table(self):

        """
        This function ...
        :return:
        """

        return self.fitting_run.memory_table

    # -----------------------------------------------------------------

    @property
    def generation_names(self):

        """
        This function ...
        :return:
        """

        return self.fitting_run.generation_names

    # -----------------------------------------------------------------

    @memoize_method
    def get_generation_index(self, generation_name):

        """
        This function ...
        :param generation_name:
        :return:
        """

        return self.generation_names.index(generation_name)

    # -----------------------------------------------------------------

    @memoize_method
    def get_generation(self, generation_name):

        """
        This function ...
        :param generation_name:
        :return:
        """

        return self.fitting_run.get_generation(generation_name)

    # -----------------------------------------------------------------

    def get_simulation_names(self, generation_name):

        """
        This function ...
        :param generation_name:
        :return:
        """

        return self.get_generation(generation_name).simulation_names

    # -----------------------------------------------------------------

    @memoize_method
    def get_sorted_simulation_indices(self, generation_name):

        """
        This function ...
        :param generation_name:
        :return:
        """

        return sequences.argsort(self.get_chi_squared_values_simulations(generation_name))

    # -----------------------------------------------------------------

    @memoize_method
    def get_sorted_simulation_names(self, generation_name):

        """
        This function ...
        :param generation_name:
        :return:
        """

        return [self.get_simulation_names(generation_name)[index] for index in self.get_sorted_simulation_indices(generation_name)]

    # -----------------------------------------------------------------

    @memoize_method
    def get_nsimulations(self, generation_name):

        """
        This function ...
        :param generation_name:
        :return:
        """

        return self.get_generation(generation_name).nsimulations

    # -----------------------------------------------------------------

    @memoize_method
    def get_simulation_index(self, generation_name, simulation_name):

        """
        This function ...
        :param generation_name:
        :param simulation_name:
        :return:
        """

        return self.get_simulation_names(generation_name).index(simulation_name)

    # -----------------------------------------------------------------

    @memoize_method
    def get_best_simulation_index(self, generation_name):

        """
        This function ...
        :param generation_name:
        :return:
        """

        return self.get_chi_squared_table(generation_name).best_simulation_index

    # -----------------------------------------------------------------

    @memoize_method
    def get_best_simulation_name(self, generation_name):

        """
        This function ...
        :param generation_name:
        :return:
        """

        return self.get_chi_squared_table(generation_name).best_simulation_name

    # -----------------------------------------------------------------

    def is_best_simulation(self, generation_name, simulation_name):

        """
        This function ...
        :param generation_name:
        :param simulation_name:
        :return:
        """

        return self.get_best_simulation_name(generation_name) == simulation_name

    # -----------------------------------------------------------------

    @memoize_method
    def get_best_simulation_chi_squared(self, generation_name):

        """
        This function ...
        :param generation_name:
        :return:
        """

        return self.get_chi_squared(generation_name, self.get_best_simulation_name(generation_name))

    # -----------------------------------------------------------------

    @memoize_method
    def get_best_simulation_parameters(self, generation_name):

        """
        This function ...
        :param generation_name:
        :return:
        """

        return self.get_parameter_values(generation_name, self.get_best_simulation_name(generation_name))

    # -----------------------------------------------------------------

    def get_most_probable_simulation_name(self, generation_name):

        """
        This function ...
        :param generation_name:
        :return:
        """

        return self.get_generation(generation_name).most_probable_model

    # -----------------------------------------------------------------

    @memoize_method
    def get_simulation(self, generation_name, simulation_name):

        """
        This function ...
        :param generation_name:
        :param simulation_name:
        :return:
        """

        return self.get_generation(generation_name).get_simulation_or_basic(simulation_name)

    # -----------------------------------------------------------------

    def get_simulation_output(self, generation_name, simulation_name):

        """
        This function ...
        :param generation_name:
        :param simulation_name:
        :return:
        """

        return self.get_generation(generation_name).get_simulation_output(simulation_name)

    # -----------------------------------------------------------------

    def get_extraction_output(self, generation_name, simulation_name):

        """
        This function ...
        :param generation_name:
        :param simulation_name:
        :return:
        """

        return self.get_generation(generation_name).get_extraction_output(simulation_name)

    # -----------------------------------------------------------------

    def get_plotting_output(self, generation_name, simulation_name):

        """
        This function ...
        :param generation_name:
        :param simulation_name:
        :return:
        """

        return self.get_generation(generation_name).get_plotting_output(simulation_name)

    # -----------------------------------------------------------------

    def get_misc_output(self, generation_name, simulation_name):

        """
        This function ...
        :param generation_name:
        :param simulation_name:
        :return:
        """

        return self.get_generation(generation_name).get_misc_output(simulation_name)

    # -----------------------------------------------------------------

    @memoize_method
    def has_flux_differences(self, generation_name, simulation_name):

        """
        This function ...
        :param generation_name:
        :param simulation_name:
        :return:
        """

        return self.get_generation(generation_name).has_misc_differences(simulation_name)

    # -----------------------------------------------------------------

    @memoize_method
    def get_flux_differences(self, generation_name, simulation_name):

        """
        This function ...
        :param generation_name:
        :param simulation_name:
        :return:
        """

        return self.get_generation(generation_name).get_simulation_misc_differences(simulation_name)

    # -----------------------------------------------------------------

    @memoize_method
    def get_flux_differences_wavelengths(self, generation_name, simulation_name):

        """
        This function ...
        :param generation_name:
        :param simulation_name:
        :return:
        """

        return self.get_flux_differences(generation_name, simulation_name).wavelengths(unit="micron", add_unit=False)

    # -----------------------------------------------------------------

    @memoize_method
    def get_flux_differences_terms(self, generation_name, simulation_name):

        """
        This function ...
        :param generation_name:
        :param simulation_name:
        :return:
        """

        return self.get_flux_differences(generation_name, simulation_name).chi_squared_terms()

    # -----------------------------------------------------------------

    def get_chi_squared_terms_distribution(self, generation_name, simulation_name):

        """
        This function ...
        :param generation_name:
        :param simulation_name:
        :return:
        """

        # Get the values
        wavelengths = self.get_flux_differences_wavelengths(generation_name, simulation_name)
        terms = self.get_flux_differences_terms(generation_name, simulation_name)

        # Create distribution over the wavelength range
        return Distribution.from_columns("Wavelength", wavelengths, terms, unit="micron", y_name="Weighed squared difference")

    # -----------------------------------------------------------------

    @memoize_method
    def has_sed(self, generation_name, simulation_name):

        """
        This function ...
        :param generation_name:
        :param simulation_name:
        :return:
        """

        return self.get_generation(generation_name).has_simulation_sed(simulation_name)

    # -----------------------------------------------------------------

    @memoize_method
    def get_sed(self, generation_name, simulation_name):

        """
        This function ...
        :param generation_name:
        :param simulation_name:
        :return:
        """

        return self.get_generation(generation_name).get_simulation_sed(simulation_name)

    # -----------------------------------------------------------------

    @memoize_method
    def has_mock_sed(self, generation_name, simulation_name):

        """
        This function ...
        :param generation_name:
        :param simulation_name:
        :return:
        """

        return self.get_generation(generation_name).has_mock_sed(simulation_name)

    # -----------------------------------------------------------------

    @memoize_method
    def get_mock_sed(self, generation_name, simulation_name):

        """
        This function ...
        :param generation_name:
        :param simulation_name:
        :return:
        """

        return self.get_generation(generation_name).get_mock_sed(simulation_name)

    # -----------------------------------------------------------------

    def has_sed_plot(self, generation_name, simulation_name):

        """
        This function ...
        :param generation_name:
        :param simulation_name:
        :return:
        """

        return self.get_generation(generation_name).has_sed_plot(simulation_name)

    # -----------------------------------------------------------------

    def get_sed_plot_path(self, generation_name, simulation_name):

        """
        This function ...
        :param generation_name:
        :param simulation_name:
        :return:
        """

        return self.get_generation(generation_name).get_simulation_sed_plot_path(simulation_name)

    # -----------------------------------------------------------------

    def has_mock_sed_plot(self, generation_name, simulation_name):

        """
        This function ...
        :param generation_name:
        :param simulation_name:
        :return:
        """

        return self.get_generation(generation_name).has_mock_sed_plot(simulation_name)

    # -----------------------------------------------------------------

    def get_mock_sed_plot_path(self, generation_name, simulation_name):

        """
        This function ...
        :param generation_name:
        :param simulation_name:
        :return:
        """

        return self.get_generation(generation_name).get_mock_sed_plot_path(simulation_name)

    # -----------------------------------------------------------------

    def get_chi_squared_table(self, generation_name):

        """
        This fucntion ...
        :param generation_name:
        :return:
        """

        return self.get_generation(generation_name).chi_squared_table

    # -----------------------------------------------------------------

    @memoize_method
    def get_chi_squared(self, generation_name, simulation_name):

        """
        This function ...
        :param generation_name:
        :param simulation_name:
        :return:
        """

        return self.get_chi_squared_table(generation_name).chi_squared_for(simulation_name)

    # -----------------------------------------------------------------

    @memoize_method
    def get_chi_squared_values(self, generation_name):

        """
        This function ...
        :param generation_name:
        :return:
        """

        return self.get_chi_squared_table(generation_name).chi_squared_values

    # -----------------------------------------------------------------

    @memoize_method
    def get_chi_squared_values_simulations(self, generation_name):

        """
        This function ...
        :param generation_name:
        :return:
        """

        # IN THE SAME ORDER AS THE GET_SIMULATION_NAMES

        values = []
        for simulation_name in self.get_simulation_names(generation_name): values.append(self.get_chi_squared(generation_name, simulation_name))
        return values

    # -----------------------------------------------------------------

    @memoize_method
    def get_chi_squared_distribution(self, generation_name, nbins=50, clip_above=None):

        """
        This function ...
        :param generation_name:
        :param nbins:
        :param clip_above:
        :return:
        """

        # Get the values
        values = self.get_chi_squared_values(generation_name)

        # Create and return distribution
        return Distribution.from_values("Chi squared", values, nbins=nbins, clip_above=clip_above, density=False)

    # -----------------------------------------------------------------

    @memoize_method
    def get_chi_squared_ranks_distribution(self, generation_name):

        """
        This function ...
        :param generation_name:
        :return:
        """

        # Get the values
        values = self.get_chi_squared_values(generation_name)

        # Create and return the distribution
        return Distribution.by_rank("Simulation rank", values, y_name="Chi squared")

    # -----------------------------------------------------------------

    @memoize_method
    def get_best_simulation_names(self, generation_name, nsimulations):

        """
        This function ...
        :param generation_name:
        :param nsimulations:
        :return:
        """

        # Return the list of simulation names
        return self.get_chi_squared_table(generation_name).get_best_simulation_names(nsimulations)

    # -----------------------------------------------------------------

    @memoize_method
    def get_best_simulations_chi_squared_values(self, generation_name, nsimulations):

        """
        This function ...
        :param generation_name:
        :param nsimulations:
        :return:
        """

        # Create list for chi squared values
        chi_squared_values = []

        # Loop over the simulations
        for simulation_name in self.get_best_simulation_names(generation_name, nsimulations=nsimulations):

            # Get the chi squared value
            chisq = self.get_chi_squared(generation_name, simulation_name)

            # Add the value
            chi_squared_values.append(chisq)

        # Return the list of chi squared values
        return chi_squared_values

    # -----------------------------------------------------------------

    @memoize_method
    def get_best_simulations_parameters(self, generation_name, nsimulations):

        """
        This function ...
        :param generation_name:
        :param nsimulations:
        :return:
        """

        # Create list for parameter values
        parameters = []

        # Loop over the simulations
        for simulation_name in self.get_best_simulation_names(generation_name, nsimulations=nsimulations):

            # Get parameter values
            parameter_values = self.get_parameter_values(generation_name, simulation_name)

            # Add the value
            parameters.append(parameter_values)

        # Return the list of parameter dictionaries
        return parameters

    # -----------------------------------------------------------------

    @memoize_method
    def get_best_simulations_parameter_counts(self, generation_name, nsimulations):

        """
        This function ...
        :param generation_name:
        :param nsimulations:
        :return:
        """

        # Initialize the counts dictionary
        counts = OrderedDict()
        for label in self.parameter_labels: counts[label] = DefaultOrderedDict(int)

        # Get unique values
        unique_values = self.get_unique_parameter_values_scalar(generation_name)

        # Fill with zeros
        for label in self.parameter_labels:
            for value in unique_values[label]: counts[label][value] = 0

        # Get best simulation names
        simulation_names = self.get_best_simulation_names(generation_name, nsimulations)

        # Loop over the simulations
        for index, simulation_name in enumerate(simulation_names):

            # Get parameter values
            parameter_values = self.get_parameter_values(generation_name, simulation_name)

            # Get the counts
            for label in parameter_values:

                # Get properties
                unit = self.get_parameter_unit(label)
                value = parameter_values[label]
                value_scalar = value.to(unit).value

                # Add count for this parameter
                counts[label][value_scalar] += 1

        # Return the counts dictionary
        return counts

    # -----------------------------------------------------------------

    @memoize_method
    def get_best_simulations_parameter_count_distributions(self, generation_name, nsimulations):

        """
        This function ...
        :param generation_name:
        :param nsimulations:
        :return:
        """

        # Initialize dictionary
        counts_distributions = OrderedDict()

        # Get the counts
        counts = self.get_best_simulations_parameter_counts(generation_name, nsimulations)

        # Make counts distributions
        for label in self.parameter_labels: counts_distributions[label] = Distribution.from_counts(label, counts[label].values(), counts[label].keys(), sort=True)

        # Return
        return counts_distributions

    # -----------------------------------------------------------------

    @memoize_method
    def get_probabilities_table(self, generation_name):

        """
        This function ...
        :param generation_name:
        :return:
        """

        # Get tables
        chi_squared = self.get_chi_squared_table(generation_name)
        parameters = self.get_parameters_table(generation_name)

        # Create the probabilities table and return it
        return chi_squared_table_to_probabilities(chi_squared, parameters)

    # -----------------------------------------------------------------

    @memoize_method
    def get_probabilities(self, generation_name):

        """
        This function ...
        :param generation_name:
        :return:
        """

        return self.get_probabilities_table(generation_name).probabilities

    # -----------------------------------------------------------------

    @memoize_method
    def get_probability_distribution(self, generation_name, nbins=50, clip_below=None):

        """
        This function ...
        :param generation_name:
        :param nbins:
        :param clip_below:
        :return:
        """

        # Get the values
        values = self.get_probabilities(generation_name)

        # Create and return the distribution
        return Distribution.from_values("Probability", values, nbins=nbins, ignore_value=0, clip_below=clip_below, density=False)

    # -----------------------------------------------------------------

    @memoize_method
    def get_probability_ranks_distribution(self, generation_name):

        """
        This function ...
        :param generation_name:
        :return:
        """

        # Get the values
        values = self.get_probabilities(generation_name)

        # Create and return the distribution
        return Distribution.by_rank("Simulation rank", values, y_name="Probability")

    # -----------------------------------------------------------------

    def get_probabilities_nzeros(self, generation_name):

        """
        This function ...
        :param generation_name:
        :return:
        """

        return self.get_probabilities_table(generation_name).nzeros

    # -----------------------------------------------------------------

    def get_assignment_table(self, generation_name):

        """
        This function ...
        :param generation_name:
        :return:
        """

        return self.get_generation(generation_name).assignment_table

    # -----------------------------------------------------------------

    def get_individuals_table(self, generation_name):

        """
        This function ...
        :param generation_name:
        :return:
        """

        return self.get_generation(generation_name).individuals_table

    # -----------------------------------------------------------------

    def get_parameters_table(self, generation_name):

        """
        This function ...
        :param generation_name:
        :return:
        """

        return self.get_generation(generation_name).parameters_table

    # -----------------------------------------------------------------

    @memoize_method
    def get_parameter_values(self, generation_name, simulation_name):

        """
        This function ...
        :param generation_name:
        :param simulation_name:
        :return:
        """

        return self.get_parameters_table(generation_name).parameter_values_for_simulation(simulation_name)

    # -----------------------------------------------------------------

    @memoize_method
    def get_parameter_values_scalar(self, generation_name, simulation_name):

        """
        This function ...
        :param generation_name:
        :param simulation_name:
        :return:
        """

        # Initialize dictionary
        values_scalar = OrderedDict()

        # Get the values
        values = self.get_parameter_values(generation_name, simulation_name)

        # Loop over the parameters
        for label in values:
            value = values[label].to(self.get_parameter_unit(label)).value
            values_scalar[label] = value

        # Return the scalar values
        return values_scalar

    # -----------------------------------------------------------------

    @memoize_method
    def get_unique_parameter_values(self, generation_name):

        """
        This function ...
        :param generation_name:
        :return:
        """

        # Create list of unique values for each free parameter
        return self.get_parameters_table(generation_name).unique_parameter_values

    # -----------------------------------------------------------------

    @memoize_method
    def get_unique_parameter_values_scalar(self, generation_name):

        """
        This function ...
        :param generation_name:
        :return:
        """

        # Initialize dictionary
        unique_values_scalar = OrderedDict()

        # Get values
        unique_values = self.get_unique_parameter_values(generation_name)

        # Loop over the parameters
        for label in unique_values:
            values = list(sorted([value.to(self.get_parameter_unit(label)).value for value in unique_values[label]]))
            unique_values_scalar[label] = values

        # Return the scalar values
        return unique_values_scalar

    # -----------------------------------------------------------------

    def get_scores_table(self, generation_name):

        """
        This function ...
        :param generation_name:
        :return:
        """

        return self.get_generation(generation_name).scores_table

    # -----------------------------------------------------------------

    def get_elitism_table(self, generation_name):

        """
        This function ...
        :param generation_name:
        :return:
        """

        return self.get_generation(generation_name).elitism_table

    # -----------------------------------------------------------------

    def get_recurrence_table(self, generation_name):

        """
        This function ...
        :param generation_name:
        :return:
        """

        return self.get_generation(generation_name).recurrence_table

    # -----------------------------------------------------------------

    def get_crossover_table(self, generation_name):

        """
        This function ...
        :param generation_name:
        :return:
        """

        return self.get_generation(generation_name).crossover_table

    # -----------------------------------------------------------------

    def get_model_probabilities_table(self, generation_name):

        """
        This function ...
        :param generation_name:
        :return:
        """

        return self.get_generation(generation_name).model_probabilities_table

    # -----------------------------------------------------------------

    @memoize_method
    def get_parameter_probabilities_table(self, generation_name, label):

        """
        This function ...
        :param generation_name:
        :param label:
        :return:
        """

        return self.get_generation(generation_name).get_parameter_probabilities_table(label)

    # -----------------------------------------------------------------

    @memoize_method
    def get_most_probable_parameter_value(self, generation_name, label):

        """
        This function ...
        :param generation_name:
        :param label:
        :return:
        """

        return self.get_parameter_probabilities_table(generation_name, label).most_probable_value

    # -----------------------------------------------------------------

    @memoize_method
    def get_most_probable_parameter_values(self, generation_name):

        """
        This function ...
        :param generation_name:
        :return:
        """

        values = OrderedDict()
        for label in self.parameter_labels: values[label] = self.get_most_probable_parameter_value(generation_name, label)
        return values

    # -----------------------------------------------------------------

    @memoize_method
    def get_most_probable_parameter_labels_for_simulation(self, generation_name, simulation_name):

        """
        This function ...
        :param generation_name:
        :param simulation_name:
        :return:
        """

        # Get values for simulation
        #values = self.get_parameter_values(generation_name, simulation_name)
        values = self.get_parameter_values_scalar(generation_name, simulation_name)

        # Initialize list for the labels
        labels = []

        # Loop over the labels
        for label in self.parameter_labels:

            value = values[label]
            most_probable_value = self.get_most_probable_parameter_value(generation_name, label)
            #print(value, most_probable_value, value == most_probable_value, numbers.is_close(value, most_probable_value))

            # Check whether most probable
            if value == most_probable_value: labels.append(label)
            #if numbers.is_close(value, most_probable_value): labels.append(label)

        # Return the labels
        return labels

    # -----------------------------------------------------------------

    def show_generations(self, **kwargs):

        """
        This function ...
        :param kwargs:
        :return:
        """

        # Debugging
        log.debug("Showing the generations ...")

        # Loop over the generations
        for generation_name in self.generation_names:

            # Show name
            print(fmt.underlined + fmt.yellow + generation_name + fmt.reset)
            print("")

            # Show info
            self.show_generation_info(generation_name)

    # -----------------------------------------------------------------

    def show_generation_info(self, generation_name):

        """
        This function ...
        :param generation_name:
        :return:
        """

        # Get the generation
        generation = self.get_generation(generation_name)

        # Show info of generation
        show_generation_info(generation)
        print("")

    # -----------------------------------------------------------------

    @lazyproperty
    def show_simulations_definition(self):

        """
        This function ...
        :return:
        """

        # Create the definition
        definition = ConfigurationDefinition(write_config=False)

        # Add options
        definition.add_flag("sort", "sort the simulations based on their chi squared value", False)

        # Return the definition
        return definition

    # -----------------------------------------------------------------

    def show_simulations_command(self, command, **kwargs):

        """
        This function ...
        :param command:
        :param kwargs:
        :return:
        """

        # Get the generation name
        generation_name, config = self.get_generation_name_and_config_from_command(command, self.show_simulations_definition, **kwargs)

        # Show
        self.show_simulations(generation_name, sort=config.sort)

    # -----------------------------------------------------------------

    def show_simulations(self, generation_name, sort=False):

        """
        This function ...
        :param generation_name:
        :param sort:
        :return:
        """

        # Debugging
        log.debug("Showing simulations of generation '" + generation_name + "' ...")

        table = None

        print("")

        # Get the indices
        if sort: indices = self.get_sorted_simulation_indices(generation_name)
        else: indices = range(self.get_nsimulations(generation_name))

        # Print in columns
        with fmt.print_in_columns() as print_row:

            # Loop over the simulations
            for index in indices:

                # Get the simulation name
                simulation_name = self.get_simulation_names(generation_name)[index]
                #print(simulation_name)

                # Get index string
                index_string = "[" + strings.integer(index, 3, fill=" ") + "] "

                # Get chi squared
                chisq = self.get_chi_squared(generation_name, simulation_name)
                chisq_string = tostr(chisq, decimal_places=3)

                # Set parts
                parts = []
                parts.append(" - ")
                parts.append(index_string)
                parts.append(fmt.bold + simulation_name + fmt.reset_bold)
                parts.append(chisq_string)

                labels_most_probable = self.get_most_probable_parameter_labels_for_simulation(generation_name, simulation_name)
                parts.append(", ".join(labels_most_probable))

                # Set color
                if self.is_best_simulation(generation_name, simulation_name): color = "green"
                else: color = None

                # Print the row
                print_row(*parts, color=color)

                # Add to the columns
                #if columns is not None:
                #    for j, part in enumerate(parts): columns[j].append(part)

        print("")

    # -----------------------------------------------------------------

    @lazyproperty
    def show_best_definition(self):

        """
        This function ...
        :return:
        """

        # Create the definition
        definition = ConfigurationDefinition(write_config=False)

        # Add options
        definition.add_positional_optional("nsimulations", "positive_integer", "number of simulations to show", 5)

        # Return the definition
        return definition

    # -----------------------------------------------------------------

    def show_best_command(self, command, **kwargs):

        """
        This function ...
        :param command:
        :return:
        """

        # Get generation name
        generation_name, config = self.get_generation_name_and_config_from_command(command, self.show_best_definition, **kwargs)

        # Show
        self.show_best(generation_name, nsimulations=config.nsimulations)

    # -----------------------------------------------------------------

    def show_best(self, generation_name, nsimulations=5):

        """
        This function ...
        :param generation_name:
        :param nsimulations:
        :return:
        """

        # Debugging
        log.debug("Showing best " + str(nsimulations) + " simulations for generation '" + generation_name + "' ...")

        # Show ranges
        print("")
        print("Parameter ranges:")
        print("")
        for label in self.parameter_labels: print(" - " + fmt.bold + label + fmt.reset + ": " + tostr(self.parameter_ranges[label]))

        # Get the simulation names
        simulation_names = self.get_best_simulation_names(generation_name, nsimulations=nsimulations)

        # Get chi squared values and parameters of the best simulations
        chi_squared_values = self.get_best_simulations_chi_squared_values(generation_name, nsimulations=nsimulations)
        parameters = self.get_best_simulations_parameters(generation_name, nsimulations=nsimulations)

        # Get unique parameter values for generation
        unique_values = self.get_unique_parameter_values_scalar(generation_name)

        # Show
        show_best_simulations_impl(simulation_names, chi_squared_values, parameters, self.parameter_units, unique_values, self.parameter_scales, self.initial_parameter_values)
        print("")

    # -----------------------------------------------------------------

    @lazyproperty
    def show_counts_definition(self):

        """
        This function ...
        :return:
        """

        # Create definition
        definition = ConfigurationDefinition(write_config=False)
        definition.add_positional_optional("nsimulations", "positive_integer", "number of best simulations to count", 10)

        # Return the definition
        return definition

    # -----------------------------------------------------------------

    def show_counts_command(self, command, **kwargs):

        """
        This function ...
        :param command:
        :param kwargs:
        :return:
        """

        # Get the generation name
        generation_name, config = self.get_generation_name_and_config_from_command(command, self.show_counts_definition, **kwargs)

        # Show
        self.show_counts(generation_name, nsimulations=config.nsimulations)

    # -----------------------------------------------------------------

    def show_counts(self, generation_name, nsimulations=10):

        """
        This function ...
        :param generation_name:
        :param nsimulations:
        :return:
        """

        # Debugging
        log.debug("Showing the counts statistics of generation '" + generation_name + "' ...")

        # Get the counts
        counts = self.get_best_simulations_parameter_counts(generation_name, nsimulations)

        # Show counts
        print("Counts in best simulations:")

        # Loop over the parameters
        for label in self.parameter_labels:

            print("")
            print(" - " + fmt.bold + label + fmt.reset + ":")
            print("")
            for value in sorted(counts[label].keys()):

                count = counts[label][value]
                relcount = float(count) / nsimulations
                print("    * " + tostr(value) + ": " + str(counts[label][value]) + " (" + tostr(relcount * 100) + "%)")

    # -----------------------------------------------------------------

    @lazyproperty
    def show_parameters_definition(self):

        """
        This function ...
        :return:
        """

        # Create the definition
        definition = ConfigurationDefinition(write_config=False)

        # Return the definition
        return definition

    # -----------------------------------------------------------------

    def show_parameters_command(self, command, **kwargs):

        """
        This function ...
        :param command:
        :param kwargs:
        :return:
        """

        # Get the generation name
        generation_name, config = self.get_generation_name_and_config_from_command(command, self.show_parameters_definition, **kwargs)

        # Show
        self.show_parameters(generation_name)

    # -----------------------------------------------------------------

    def show_parameters(self, generation_name, nsimulations=10):

        """
        This function ...
        :param generation_name:
        :param nsimulations:
        :return:
        """

        # Debugging
        log.debug("Showing the parameter statistics of generation '" + generation_name + "' ...")

        # Get best simulation and its parameter values
        best_simulation_name = self.get_best_simulation_name(generation_name)
        best_parameter_values = self.get_best_simulation_parameters(generation_name)

        # Most probable model: should be same as simulation with lowest chi squared
        most_probable_simulation_name = self.get_most_probable_simulation_name(generation_name)
        assert most_probable_simulation_name == best_simulation_name

        # Get counts distributions
        if nsimulations > 1: counts_distributions = self.get_best_simulations_parameter_count_distributions(generation_name, nsimulations)
        else: counts_distributions = None

        print("")
        print("Statistics:")

        # Loop over the free parameter labels
        for label in self.parameter_labels:

            print("")
            print(" - " + fmt.bold + label + fmt.reset + ":")
            print("")

            # Get most probable parameter value
            most_probable_value = self.get_most_probable_parameter_value(generation_name, label)

            # Show
            print("    * Initial guess value: " + tostr(self.initial_parameter_values[label], ndigits=3))
            print("    * Best simulation value: " + tostr(best_parameter_values[label], ndigits=3))
            print("    * Most probable value: " + tostr(most_probable_value, ndigits=3) + " " + tostr(self.parameter_units[label]))
            if nsimulations > 1: print("    * Most counted in " + str(nsimulations) + " best simulations: " + tostr(counts_distributions[label].most_frequent, ndigits=3) + " " + tostr(self.parameter_units[label]))

        print("")

    # -----------------------------------------------------------------

    @memoize_method
    def get_simulation_matches(self, generation_a_name, generation_b_name):

        """
        This function ...
        :param generation_a_name:
        :param generation_b_name:
        :return:
        """

        # Get the parameters tables
        parameters_a = self.get_parameters_table(generation_a_name)
        parameters_b = self.get_parameters_table(generation_b_name)

        # Initialize dictionary
        closest = dict()

        # Loop over the simulations of one generation
        for index in range(len(parameters_a)):

            # Get the simulation name
            simulation_name = parameters_a.get_simulation_name(index)

            # Get parameter values
            values = parameters_a.get_parameter_values(index)

            # Find the simulation with the closest parameter values for the other generation
            closest_index = parameters_b.closest_simulation_for_parameter_values(values, return_index=True)
            closest_simulation_name = parameters_b.get_simulation_name(closest_index)

            # Get the closest values
            closest_values = parameters_b.get_parameter_values(closest_index)

            # Loop over the labels
            diff_keys = []
            for label in self.parameter_labels:

                # Get both values
                value = values[label]
                closest_value = closest_values[label]

                # Calculate the difference
                diff = np.exp(abs(np.log(value / closest_value)))

                # Add the difference
                diff_keys.append(diff)

            # Calculate difference
            diff = np.sqrt(np.sum(np.power(diff_keys, 2)))

            # Add to the dictionary
            if closest_simulation_name in closest:
                current_diff = closest[closest_simulation_name][1]
                if diff < current_diff: closest[closest_simulation_name] = (simulation_name, diff)
            else: closest[closest_simulation_name] = (simulation_name, diff)

        # Return the dictionary
        return closest

    # -----------------------------------------------------------------

    @memoize_method
    def get_closest_simulations(self, generation_a_name, generation_b_name, nsimulations):

        """
        This function ...
        :param generation_a_name:
        :param generation_b_name:
        :param nsimulations:
        :return:
        """

        # Get matches
        closest = self.get_simulation_matches(generation_a_name, generation_b_name)

        # Keep only the closest matches
        matches = []

        # Sort from best match to worse match
        for closest_simulation_name in sorted(closest, key=lambda name: closest[name][1]):

            simulation_name = closest[closest_simulation_name][0]
            diff = closest[closest_simulation_name][1]
            matches.append((simulation_name, closest_simulation_name, diff))
            if len(matches) == nsimulations: break

        # Return the pairs
        return matches

    # -----------------------------------------------------------------

    @lazyproperty
    def compare_parameters_definition(self):

        """
        This function ...
        :return:
        """

        definition = ConfigurationDefinition(write_config=False)
        return definition

    # -----------------------------------------------------------------

    def compare_parameters_command(self, command, **kwargs):

        """
        This function ...
        :param command:
        :param kwargs:
        :return:
        """

        # Get
        generation_simulation_name_a, generation_simulation_name_b = self.get_two_generation_simulation_names_and_config_from_command(command, self.compare_parameters_definition, **kwargs)

        # Compare
        self.compare_parameters(generation_simulation_name_a, generation_simulation_name_b)

    # -----------------------------------------------------------------

    def compare_parameters(self, generation_simulation_name_a, generation_simulation_name_b):

        """
        This function ...
        :param generation_simulation_name_a:
        :param generation_simulation_name_b:
        :return:
        """

        # Debugging
        log.debug("Comparing parameters between simulation '" + tostr(generation_simulation_name_a) + "' and '" + tostr(generation_simulation_name_b) + "' ...")

        # Get generation names and simulation names
        generation_a_name = generation_simulation_name_a[0]
        generation_b_name = generation_simulation_name_b[0]
        simulation_a_name = generation_simulation_name_a[1]
        simulation_b_name = generation_simulation_name_b[1]

        # Get the parameters tables
        parameters_a = self.get_parameters_table(generation_a_name)
        parameters_b = self.get_parameters_table(generation_b_name)

        # Get parameter values
        values_a = parameters_a.parameter_values_for_simulation(simulation_a_name)
        values_b = parameters_b.parameter_values_for_simulation(simulation_b_name)

        # Loop over the parameter values
        for label in self.parameter_labels:

            # Convert to scalar values
            unit = self.get_parameter_unit(label)
            value_a = values_a[label].to(unit).value
            value_b = values_b[label].to(unit).value

            # Calculate relative difference
            reldiff = np.exp(abs(np.log(value_a / value_b))) - 1

            # Show
            print(" - " + fmt.bold + label + fmt.reset + ": " + fmt.yellow + tostr(value_a, decimal_places=4) + fmt.reset + ", " + fmt.cyan + tostr(value_b, decimal_places=4) + fmt.reset + " " + tostr(unit) + " (" + tostr(reldiff * 100, decimal_places=3) + "%)")

        print("")

    # -----------------------------------------------------------------

    @lazyproperty
    def compare_seds_definition(self):

        """
        This function ...
        :return:
        """

        definition = ConfigurationDefinition(write_config=False)
        return definition

    # -----------------------------------------------------------------

    def compare_seds_command(self, command, **kwargs):

        """
        This function ...
        :param command:
        :param kwargs:
        :return:
        """

        # Get
        generation_simulation_name_a, generation_simulation_name_b = self.get_two_generation_simulation_names_and_config_from_command(command, self.compare_seds_definition, **kwargs)

        # Compare
        self.compare_seds(generation_simulation_name_a, generation_simulation_name_b)

    # -----------------------------------------------------------------

    def compare_seds(self, generation_simulation_name_a, generation_simulation_name_b, add_references=False,
                     additional_error=None):

        """
        This function ...
        :param generation_simulation_name_a:
        :param generation_simulation_name_b:
        :param add_references:
        :param additional_error:
        :return:
        """

        # Debugging
        log.debug("Comparing simulated SEDs between simulation '" + tostr(generation_simulation_name_a) + "' and '" + tostr(generation_simulation_name_b) + "' ...")

        # Get generation names and simulation names
        generation_a_name = generation_simulation_name_a[0]
        generation_b_name = generation_simulation_name_b[0]
        simulation_a_name = generation_simulation_name_a[1]
        simulation_b_name = generation_simulation_name_b[1]

        # Get the generations
        generation_a = self.get_generation(generation_a_name)
        generation_b = self.get_generation(generation_b_name)

        # Create SEDs
        seds = OrderedDict()
        if add_references: seds.update(self.get_reference_seds(additional_error=additional_error))
        seds["Generation a"] = generation_a.get_simulation_sed(simulation_a_name)
        seds["Generation b"] = generation_b.get_simulation_sed(simulation_b_name)

        # Plot
        plot_seds(seds, models_residuals=True)

    # -----------------------------------------------------------------

    @lazyproperty
    def compare_fluxes_definition(self):

        """
        This function ...
        :return:
        """

        definition = ConfigurationDefinition(write_config=False)
        return definition

    # -----------------------------------------------------------------

    def compare_fluxes_command(self, command, **kwargs):

        """
        This function ...
        :param command:
        :param kwargs:
        :return:
        """

        # Get
        generation_simulation_name_a, generation_simulation_name_b = self.get_two_generation_simulation_names_and_config_from_command(command, self.compare_fluxes_definition, **kwargs)

        # Compare
        self.compare_fluxes(generation_simulation_name_a, generation_simulation_name_b)

    # -----------------------------------------------------------------

    def compare_fluxes(self, generation_simulation_name_a, generation_simulation_name_b, add_references=True,
                       additional_error=None):

        """
        This function ...
        :param generation_simulation_name_a:
        :param generation_simulation_name_b:
        :param add_references:
        :param additional_error:
        :return:
        """

        # Debugging
        log.debug("Comparing mock SEDs between simulation '" + tostr(generation_simulation_name_a) + "' and '" + tostr(generation_simulation_name_b) + "' ...")

        # Get generation names and simulation names
        generation_a_name = generation_simulation_name_a[0]
        generation_b_name = generation_simulation_name_b[0]
        simulation_a_name = generation_simulation_name_a[1]
        simulation_b_name = generation_simulation_name_b[1]

        # Get the generations
        generation_a = self.get_generation(generation_a_name)
        generation_b = self.get_generation(generation_b_name)

        # Create SEDs
        seds = OrderedDict()
        if add_references: seds.update(self.get_reference_seds(additional_error=additional_error))
        seds["Generation a"] = generation_a.get_mock_sed(simulation_a_name)
        seds["Generation b"] = generation_b.get_mock_sed(simulation_b_name)

        # Plot
        plot_seds(seds)

    # -----------------------------------------------------------------

    @lazyproperty
    def show_closest_parameters_definition(self):

        """
        This function ...
        :return:
        """

        # Create the definition
        definition = ConfigurationDefinition(write_config=False)

        # Number of best maching simulations
        definition.add_optional("nsimulations", "positive_integer", "number of best matching simulations", 5)

        # Return the definition
        return definition

    # -----------------------------------------------------------------

    def show_closest_parameters_command(self, command, **kwargs):

        """
        This function ...
        :param command:
        :param kwargs:
        :return:
        """

        # Get the generation names
        generation_a_name, generation_b_name, config = self.get_two_generation_names_and_config_from_command(command, self.show_closest_parameters_definition, **kwargs)

        # Compare
        self.show_closest_parameters(generation_a_name, generation_b_name, nsimulations=config.nsimulations)

    # -----------------------------------------------------------------

    def show_closest_parameters(self, generation_a_name, generation_b_name, nsimulations=5):

        """
        This function ...
        :param generation_a_name:
        :param generation_b_name:
        :param nsimulations:
        :return:
        """

        # Get the matches
        closest = self.get_closest_simulations(generation_a_name, generation_b_name, nsimulations)

        # Loop over the matches
        for index, match in enumerate(closest):

            # Get simulation names
            name_a, name_b = match[0], match[1]

            # Show simulation names
            print(str(index + 1) + ". " + fmt.underlined + fmt.green + name_a + fmt.reset + ", " + fmt.underlined + fmt.green + name_b + fmt.reset + ":")
            print("")

            # Make generation simulation combinations
            generation_simulation_name_a = (generation_a_name, name_a)
            generation_simulation_name_b = (generation_b_name, name_b)

            # Compare
            self.compare_parameters(generation_simulation_name_a, generation_simulation_name_b)

    # -----------------------------------------------------------------

    @lazyproperty
    def plot_closest_seds_definition(self):

        """
        This function ...
        :return:
        """

        definition = ConfigurationDefinition(write_config=False)
        return definition

    # -----------------------------------------------------------------

    def plot_closest_seds_command(self, command, **kwargs):

        """
        This function ...
        :param command:
        :param kwargs:
        :return:
        """

        # Get the generation names
        generation_a_name, generation_b_name, config = self.get_two_generation_names_and_config_from_command(command, self.plot_closest_seds_definition, **kwargs)

        # Compare
        self.plot_closest_seds(generation_a_name, generation_b_name, nsimulations=config.nsimulations)

    # -----------------------------------------------------------------

    def plot_closest_seds(self, generation_a_name, generation_b_name, nsimulations=1):

        """
        This function ...
        :param generation_a_name:
        :param generation_b_name:
        :param nsimulations:
        :return:
        """

        # Get the matches
        closest = self.get_closest_simulations(generation_a_name, generation_b_name, nsimulations)

        # Loop over the matches
        for index, match in enumerate(closest):

            # Get simulation names
            name_a, name_b = match[0], match[1]

            # Show simulation names
            print(str(index + 1) + ". " + fmt.underlined + fmt.green + name_a + fmt.reset + ", " + fmt.underlined + fmt.green + name_b + fmt.reset + ":")
            print("")

            # Make generation simulation combinations
            generation_simulation_name_a = (generation_a_name, name_a)
            generation_simulation_name_b = (generation_b_name, name_b)

            # Compare
            self.compare_seds(generation_simulation_name_a, generation_simulation_name_b)

    # -----------------------------------------------------------------

    @lazyproperty
    def plot_closest_fluxes_definition(self):

        """
        This function ...
        :return:
        """

        definition = ConfigurationDefinition(write_config=False)
        return definition

    # -----------------------------------------------------------------

    def plot_closest_fluxes_command(self, command, **kwargs):

        """
        This function ...
        :param command:
        :param kwargs:
        :return:
        """

        # Get the generation names
        generation_a_name, generation_b_name, config = self.get_two_generation_names_and_config_from_command(command, self.plot_closest_fluxes_definition, **kwargs)

        # Compare
        self.plot_closest_fluxes(generation_a_name, generation_b_name, nsimulations=config.nsimulations)

    # -----------------------------------------------------------------

    def plot_closest_fluxes(self, generation_a_name, generation_b_name, nsimulations=1):

        """
        This function ...
        :param generation_a_name:
        :param generation_b_name:
        :param nsimulations:
        :return:
        """

        # Get the matches
        closest = self.get_closest_simulations(generation_a_name, generation_b_name, nsimulations)

        # Loop over the matches
        for index, match in enumerate(closest):

            # Get simulation names
            name_a, name_b = match[0], match[1]

            # Show simulation names
            print(str(index + 1) + ". " + fmt.underlined + fmt.green + name_a + fmt.reset + ", " + fmt.underlined + fmt.green + name_b + fmt.reset + ":")
            print("")

            # Make generation simulation combinations
            generation_simulation_name_a = (generation_a_name, name_a)
            generation_simulation_name_b = (generation_b_name, name_b)

            # Compare
            self.compare_fluxes(generation_simulation_name_a, generation_simulation_name_b)

    # -----------------------------------------------------------------

    @lazyproperty
    def plot_best_definition(self):

        """
        This function ...
        :return:
        """

        # Create
        definition = ConfigurationDefinition(write_config=False)

        # Add options
        definition.add_positional_optional("nsimulations", "positive_integer", "number of simulations to show", 1)
        definition.add_positional_optional("simulated_or_mock", "string", "plot simulated SED or mock fluxes", choices=simulated_or_mock, default=simulated_choice)
        definition.add_optional("path", "string", "save the plot file")
        definition.add_optional("additional_error", "percentage", "additional percentual error for the observed flux points")

        # Return the definition
        return definition

    # -----------------------------------------------------------------

    def plot_best_command(self, command, **kwargs):

        """
        This function ...
        :param command:
        :param kwargs:
        :return:
        """

        # Get generation name
        generation_name, config = self.get_generation_name_and_config_from_command(command, self.plot_best_definition, **kwargs)

        # Simulated SEDs
        if config.simulated_or_mock == simulated_choice: self.plot_best_seds(generation_name, nsimulations=config.nsimulations, additional_error=config.additional_error, path=config.path)

        # Mock SEDs
        elif config.simulated_or_mock == mock_choice: self.plot_best_fluxes(generation_name, nsimulations=config.nsimulations, additional_error=config.additional_error, path=config.path)

        # Invalid
        else: raise ValueError("Invalid value for 'simulated_or_mock'")

    # -----------------------------------------------------------------

    def plot_best_seds(self, generation_name, nsimulations=5, additional_error=None, path=None):

        """
        This function ...
        :param generation_name:
        :param nsimulations:
        :param additional_error:
        :param path:
        :return:
        """

        # Debugging
        log.debug("Plotting the simulated SEDs for the best " + str(nsimulations) + " simulations of generation '" + generation_name + "' ...")

        # Create the SED plotter
        plotter = SEDPlotter()

        # Debugging
        log.debug("Adding the observed SEDs ...")

        # Add observed SEDs
        seds = self.get_reference_seds(additional_error=additional_error)
        for label in seds: plotter.add_sed(seds[label], label)

        # Debugging
        log.debug("Adding the simulated SEDs ...")

        # Loop over the simulation names
        for index, simulation_name in enumerate(self.get_best_simulation_names(generation_name, nsimulations)):

            # Debugging
            log.debug("Adding SED of the '" + simulation_name + "' simulation (" + str(index + 1) + " of " + str(nsimulations) + ") ...")

            # Get the simulated SED
            sed = self.get_sed(generation_name, simulation_name)

            # Add the SED
            plotter.add_sed(sed, simulation_name, ghost=True, residuals=False)

        # Run the plotter
        plotter.run(output=path)

    # -----------------------------------------------------------------

    def plot_best_fluxes(self, generation_name, nsimulations=1, additional_error=None, path=None):

        """
        This function ...
        :param generation_name:
        :param nsimulations:
        :param additional_error:
        :param path:
        :return:
        """

        # Debugging
        log.debug("Plotting the mock fluxes for the best " + str(nsimulations) + " simulations of generation '" + generation_name + "' ...")

        # Create the SED plotter
        plotter = SEDPlotter()

        # Debugging
        log.debug("Adding the observed SEDs ...")

        # Add observed SEDs
        seds = self.get_reference_seds(additional_error=additional_error)
        for label in seds: plotter.add_sed(seds[label], label)

        # Debugging
        log.debug("Adding the mock SEDs ...")

        # Loop over the simluation names
        for index, simulation_name in enumerate(self.get_best_simulation_names(generation_name, nsimulations)):

            # Debugging
            log.debug("Adding SED of the '" + simulation_name + "' simulation (" + str(index + 1) + " of " + str(nsimulations) + ") ...")

            # Get the mock SED
            fluxes = self.get_mock_sed(generation_name, simulation_name)

            # Add the SED
            plotter.add_sed(fluxes, simulation_name)

        # Run the plotter
        plotter.run(output=path)

    # -----------------------------------------------------------------

    @lazyproperty
    def plot_terms_definition(self):

        """
        This function ...
        :return:
        """

        # Create the definition
        definition = ConfigurationDefinition(write_config=False)

        # Add options
        definition.add_optional("path", "string", "write the plot file")

        # Return the definition
        return definition

    # -----------------------------------------------------------------

    def plot_terms_command(self, command, **kwargs):

        """
        This function ...
        :param command:
        :param kwargs:
        :return:
        """

        # Get generation name
        generation_name, simulation_name, config = self.get_generation_name_simulation_name_and_config_from_command(command, self.plot_terms_definition, **kwargs)

        # Plot
        self.plot_terms(generation_name, simulation_name, path=config.path)

    # -----------------------------------------------------------------

    def plot_terms(self, generation_name, simulation_name, path=None):

        """
        This function ...
        :param generation_name:
        :param simulation_name:
        :param path:
        :return:
        """

        # Get the distribution
        distribution = self.get_chi_squared_terms_distribution(generation_name, simulation_name)

        # Plot
        plot_distribution(distribution, logscale=True, statistics=False, color="xkcd:orange", path=path)

    # -----------------------------------------------------------------

    @lazyproperty
    def plot_ranks_definition(self):

        """
        This function ...
        :return:
        """

        # Create definition
        definition = ConfigurationDefinition(write_config=False)

        # Add options
        definition.add_required("chisquared_or_prob", "string", "plot chi squared values or probabilities", choices=chisquared_or_prob)
        definition.add_optional("path", "string", "write the plot file")

        # Return the definition
        return definition

    # -----------------------------------------------------------------

    @lazyproperty
    def plot_ranks_kwargs(self):

        """
        This function ...
        :return:
        """

        kwargs = dict()
        kwargs["required_to_optional"] = False
        return kwargs

    # -----------------------------------------------------------------

    def plot_ranks_command(self, command, **kwargs):

        """
        This function ...
        :param command:
        :param kwargs:
        :return:
        """

        # Set all kwargs
        kwargs.update(self.plot_ranks_kwargs)

        # Get generation name
        generation_name, config = self.get_generation_name_and_config_from_command(command, self.plot_ranks_definition, **kwargs)

        # Chi squared values
        if config.chisquared_or_prob == chisquared_choice: self.plot_ranks_chisquared(generation_name)

        # Probabilities
        elif config.chisquared_or_prob == prob_choice: self.plot_ranks_probabilities(generation_name)

        # Invalid
        else: raise ValueError("Invalid value for 'chisquared_or_prob'")

    # -----------------------------------------------------------------

    def plot_ranks_chisquared(self, generation_name, path=None):

        """
        This function ...
        :param generation_name:
        :param path:
        :return:
        """

        # Get the rank distribution
        distribution = self.get_chi_squared_ranks_distribution(generation_name)

        # Plot histogram of the chi squared values w.r.t. simulation rank
        plot_distribution(distribution, statistics=False, path=path)

    # -----------------------------------------------------------------

    def plot_ranks_probabilities(self, generation_name, path=None):

        """
        This function ...
        :param generation_name:
        :param path:
        :return:
        """

        # Get the rank distribution
        distribution = self.get_probability_ranks_distribution(generation_name)

        # Plot histogram of the probability values w.r.t. simulation rank
        plot_distribution(distribution, statistics=False, color="red", logfrequency=True, path=path)

    # -----------------------------------------------------------------

    @lazyproperty
    def plot_chi_squared_definition(self):

        """
        This function ...
        :return:
        """

        # Create the definition
        definition = ConfigurationDefinition(write_config=False)

        # Add options
        definition.add_optional("nbins", "positive_integer", "number of bins", 50)
        definition.add_optional("max_chisquared", "positive_real", "maximum chi squared to show")
        definition.add_optional("path", "string", "save the plot file")

        # Return the definition
        return definition

    # -----------------------------------------------------------------

    def plot_chi_squared_command(self, command, **kwargs):

        """
        This function ...
        :param command:
        :param kwargs:
        :return:
        """

        # Get generation name
        generation_name, config = self.get_generation_name_and_config_from_command(command, self.plot_chi_squared_definition, **kwargs)

        # Plot
        self.plot_chi_squared(generation_name, path=config.path, nbins=config.nbins, max_chisquared=config.max_chisquared)

    # -----------------------------------------------------------------

    def plot_chi_squared(self, generation_name, path=None, nbins=50, max_chisquared=None):

        """
        This function ...
        :param generation_name:
        :param path:
        :param nbins:
        :param max_chisquared:
        :return:
        """

        # Make distribution of chi squared values and plot histogram
        distribution = self.get_chi_squared_distribution(generation_name, nbins=nbins, clip_above=max_chisquared)

        # Plot
        plot_distribution(distribution, path=path)

    # -----------------------------------------------------------------

    @lazyproperty
    def plot_probabilities_definition(self):

        """
        This function ...
        :return:
        """

        # Create the definition
        definition = ConfigurationDefinition(write_config=False)

        # Add options
        definition.add_optional("nbins", "positive_integer", "number of bins", 50)
        definition.add_optional("min_probability", "positive_real", "minimum probability to show")
        definition.add_optional("path", "string", "save the plot file")

        # Return the definition
        return definition

    # -----------------------------------------------------------------

    def plot_probabilities_command(self, command, **kwargs):

        """
        This function ...
        :param command:
        :param kwargs:
        :return:
        """

        # Get generation name
        generation_name, config = self.get_generation_name_and_config_from_command(command, self.plot_probabilities_definition, **kwargs)

        # Plot
        self.plot_probabilities(generation_name, path=config.path, nbins=config.nbins, min_probability=config.min_probability)

    # -----------------------------------------------------------------

    def plot_probabilities(self, generation_name, path=None, nbins=50, min_probability=None):

        """
        This function ...
        :param generation_name:
        :param path:
        :param nbins:
        :param min_probability:
        :return:
        """

        # Make distribution of probability values and plot histogram
        distribution = self.get_probability_distribution(generation_name, nbins=nbins, clip_below=min_probability)

        # Plot the distribution
        plot_distribution(distribution, color="red", path=path)

    # -----------------------------------------------------------------

    @lazyproperty
    def plot_sed_definition(self):

        """
        This function ...
        :return:
        """

        # Create the definition
        definition = ConfigurationDefinition(write_config=False)

        # Add options
        definition.add_positional_optional("simulated_or_mock", "string", "plot simulated SED or mock fluxes", choices=simulated_or_mock, default=simulated_choice)
        definition.add_optional("path", "string", "save the plot file")
        definition.add_flag("from_file", "use an already existing plot file", False)

        # Return
        return definition

    # -----------------------------------------------------------------

    def plot_sed_command(self, command, **kwargs):

        """
        This function ...
        :param command:
        :param kwargs:
        :return:
        """

        # Get generation and simulation name
        generation_name, simulation_name, config = self.get_generation_name_simulation_name_and_config_from_command(command, self.plot_sed_definition, **kwargs)

        # Simulated
        if config.simulated_or_mock == simulated_choice: self.plot_sed(generation_name, simulation_name, from_file=config.from_file)

        # Mock
        elif config.simulated_or_mock == mock_choice: self.plot_fluxes(generation_name, simulation_name, from_file=config.from_file)

        # Invalid
        else: raise ValueError("Invalid value for 'simulated_or_mock'")

    # -----------------------------------------------------------------

    def plot_sed(self, generation_name, simulation_name, additional_error=None, path=None, from_file=False):

        """
        This function ...
        :param generation_name:
        :param simulation_name:
        :param additional_error:
        :param path:
        :param from_file:
        :return:
        """

        # Checks
        if from_file:
            if not self.has_sed_plot(generation_name, simulation_name): raise ValueError("No SED plot for simulation '" + simulation_name + "' of generation '" + generation_name + "'")
            if additional_error is not None: log.warning("The SED plot was probably not made with the same additional relative error for the observed points of " + str(additional_error) + ": ignoring ...")

        # Load from file
        if from_file: self.get_sed_plot(generation_name, simulation_name, path=path)

        # Make new plot
        else: self.make_sed_plot(generation_name, simulation_name, additional_error=additional_error, path=path)

    # -----------------------------------------------------------------

    def get_sed_plot(self, generation_name, simulation_name, path=None):

        """
        This function ...
        :param generation_name:
        :param simulation_name:
        :param path:
        :return:
        """

        # Get the plot filepath
        filepath = self.get_sed_plot_path(generation_name, simulation_name)

        # Copy plot file to destination?
        if path is not None: fs.copy_file(filepath, path)

        # No destination path given, show the plot
        else: fs.open_file(filepath)

    # -----------------------------------------------------------------

    def make_sed_plot(self, generation_name, simulation_name, additional_error=None, path=None):

        """
        This function ...
        :param generation_name:
        :param simulation_name:
        :param additional_error:
        :param path:
        :return:
        """

        # Debugging
        log.debug("Plotting simulated SED for simulation '" + simulation_name + "' of generation '" + generation_name + "' ...")

        # Get the simulated SED
        sed = self.get_sed(generation_name, simulation_name)

        # Get the reference SEDs
        observed_seds = self.get_reference_seds(additional_error=additional_error)

        # Set SEDs
        seds = OrderedDict()
        seds.update(observed_seds)
        seds["Simulation"] = sed

        # Make (and show) the plot
        plot_seds(seds, path=path, show_file=True)

    # -----------------------------------------------------------------

    def plot_fluxes(self, generation_name, simulation_name, additional_error=None, path=None, from_file=False):

        """
        This function ...
        :param generation_name:
        :param simulation_name:
        :param additional_error:
        :param path:
        :param from_file:
        :return:
        """

        # Checks
        if from_file:
            if not self.has_mock_sed_plot(generation_name, simulation_name): raise ValueError("No mock fluxes plot for simulation '" + simulation_name + "' of generation '" + generation_name + "'")
            if additional_error is not None: log.warning("The fluxes plot was probably not made with the same additional relative error for the observed points of " + str(additional_error) + ": ignoring ...")

        # Load from file
        if from_file: self.get_fluxes_plot(generation_name, simulation_name, path=path)

        # Make new plot
        else: self.make_fluxes_plot(generation_name, simulation_name)

    # -----------------------------------------------------------------

    def get_fluxes_plot(self, generation_name, simulation_name, path=None):

        """
        This function ...
        :param generation_name:
        :param simulation_name:
        :param path:
        :return:
        """

        # Get the plot filepath
        filepath = self.get_mock_sed_plot_path(generation_name, simulation_name)

        # Copy plot file to destination?
        if path is not None: fs.copy_file(filepath, path)

        # No destination path given, show the plot
        else: fs.open_file(filepath)

    # -----------------------------------------------------------------

    def make_fluxes_plot(self, generation_name, simulation_name, additional_error=None, path=None):

        """
        This function ...
        :param generation_name:
        :param simulation_name:
        :param additional_error:
        :param path:
        :return:
        """

        # Debugging
        log.debug("Plotting mock fluxes for simulation '" + simulation_name + "' of generation '" + generation_name + "' ...")

        # Get the mock fluxes
        fluxes = self.get_mock_sed(generation_name, simulation_name)

        # Get the reference SEDs
        observed_seds = self.get_reference_seds(additional_error=additional_error)

        # Set SEDs
        seds = OrderedDict()
        seds.update(observed_seds)
        seds["Mock fluxes"] = fluxes

        # Make (and show) the plot
        plot_seds(seds, path=path, show_file=True)

    # -----------------------------------------------------------------

    @lazyproperty
    def plot_seds_definition(self):

        """
        This function ...
        :return:
        """

        # Create the definition
        definition = ConfigurationDefinition(write_config=False)

        # Add options
        definition.add_optional("path", "string", "save the plot file")
        definition.add_optional("additional_error", "percentage", "additional percentual error for the observed flux points")
        definition.add_optional("random", "positive_integer", "pick a specified number of random simulations to plot")

        # Return the definition
        return definition

    # -----------------------------------------------------------------

    def plot_seds_command(self, command, **kwargs):

        """
        This function ...
        :param command:
        :param kwargs:
        :return:
        """

        # Get the generation name
        generation_name, config = self.get_generation_name_and_config_from_command(command, self.plot_seds_definition, **kwargs)

        # Plot
        self.plot_seds(generation_name, path=config.path, additional_error=config.additional_error, random=config.random)

    # -----------------------------------------------------------------

    def plot_seds(self, generation_name, path=None, additional_error=None, random=None):

        """
        This function ...
        :param generation_name:
        :param path:
        :param additional_error:
        :param random:
        :return:
        """

        # Debugging
        log.debug("Plotting the model SEDs of generation '" + generation_name + "' ...")

        # Create the SED plotter
        plotter = SEDPlotter()

        # Get the reference SEDs
        seds = self.get_reference_seds(additional_error=additional_error)

        # Inform the user
        log.info("Adding the observed SEDs ...")

        # Add observed SEDs
        for name in seds: plotter.add_sed(seds[name], name)

        # Add simulation SEDs
        log.info("Adding the simulated SEDs ...")

        # Get the simulation names
        names = self.get_simulation_names(generation_name)
        nsimulations = len(names)

        # Set number of SEDs
        if random is not None: nseds = random
        else: nseds = nsimulations

        # Get selected simulation names
        if random is not None: names = sequences.random_subset(names, random, avoid_duplication=True)

        # Loop over the simulation names
        for index, simulation_name in enumerate(names):

            # Debugging
            log.debug("Adding SED of the '" + simulation_name + "' simulation (" + str(index + 1) + " of " + str(nseds) + ") ...")

            # Get the simulated SED
            sed = self.get_sed(generation_name, simulation_name)

            # Add the SED
            plotter.add_sed(sed, simulation_name, ghost=True, residuals=False)

        # Run the plotter
        plotter.run(output=path)

    # -----------------------------------------------------------------

    @lazyproperty
    def plot_counts_definition(self):

        """
        This function ...
        :return:
        """

        # Create the definition
        definition = ConfigurationDefinition(write_config=False)

        # Add options
        definition.add_positional_optional("nsimulations", "positive_integer", "number of simulations to show", 10)

        # Return the definition
        return definition

    # -----------------------------------------------------------------

    def plot_counts_command(self, command, **kwargs):

        """
        This function ...
        :param command:
        :param kwargs:
        :return:
        """

        # Get generation name
        generation_name, config = self.get_generation_name_and_config_from_command(command, self.plot_counts_definition, **kwargs)

        # Plot
        self.plot_counts(generation_name, nsimulations=config.nsimulations)

    # -----------------------------------------------------------------

    def plot_counts(self, generation_name, nsimulations=10):

        """
        This function ...
        :param generation_name:
        :param nsimulations:
        :return:
        """

        # Debugging
        log.debug("Plotting best parameter counts distributions for generation '" + generation_name + "' ...")

        # Get counts distributions
        counts_distributions = self.get_best_simulations_parameter_count_distributions(generation_name, nsimulations)

        # Plot the distributions
        plot_distributions(counts_distributions, logscale=True, panels=True, frequencies=True)

    # -----------------------------------------------------------------

    def plot_filters(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Plotting the fitting filters ...")

        # Plot the fitting filters
        plot_filters(self.fitting_filters)

    # -----------------------------------------------------------------

    def show(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Showing ...")

        # Show status
        self.show_status()

    # -----------------------------------------------------------------

    @property
    def history_filename(self):

        """
        This function ...
        :return:
        """

        return "statistics"

# -----------------------------------------------------------------

def show_generation_info(generation):

    """
    This function ...
    :param generation:
    :return:
    """

    print(" - " + fmt.bold + "Method: " + fmt.reset + generation.method)
    print(" - " + fmt.bold + "Wavelength grid: " + fmt.reset + generation.wavelength_grid_name)
    print(" - " + fmt.bold + "Representation: " + fmt.reset + generation.model_representation_name)
    print(" - " + fmt.bold + "Number of photon packages: " + fmt.reset + yes_or_no(generation.npackages))
    print(" - " + fmt.bold + "Dust self-absorption: " + fmt.reset + yes_or_no(generation.selfabsorption))
    print(" - " + fmt.bold + "Transient heating: " + fmt.reset + yes_or_no(generation.transient_heating))
    print(" - " + fmt.bold + "Spectral convolution: " + fmt.reset + yes_or_no(generation.spectral_convolution))
    print(" - " + fmt.bold + "Use images: " + fmt.reset + yes_or_no(generation.use_images))

# -----------------------------------------------------------------
