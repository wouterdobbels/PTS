#!/usr/bin/env python
# -*- coding: utf8 -*-
# *****************************************************************
# **       PTS -- Python Toolkit for working with SKIRT          **
# **       © Astronomical Observatory, Ghent University          **
# *****************************************************************

## \package pts.modeling.modeling.base Contains the ModelerBase class, which is the base class for the specific modelers
#  such as the GalaxyModeler, SEDModeler and ImagesModeler.

# -----------------------------------------------------------------

# Ensure Python 3 compatibility
from __future__ import absolute_import, division, print_function

# Import standard modules
from abc import ABCMeta, abstractmethod

# Import the relevant PTS classes and modules
from ...core.basics.configurable import Configurable
from ...core.tools.logging import log
from ...core.tools import filesystem as fs
from ..fitting.explorer import ParameterExplorer
from ..fitting.sedfitting import SEDFitter
from ..component.component import load_modeling_history, get_config_file_path, load_modeling_configuration
from ...core.launch.synchronizer import RemoteSynchronizer
from ...core.prep.deploy import Deployer
from ..fitting.run import get_generations_table, get_ngenerations, has_unevaluated_generations, has_unfinished_generations, get_unevaluated_generations
from ...core.remote.moderator import PlatformModerator
from ...core.tools import stringify
from ...core.tools.loops import repeat
from ...core.remote.remote import Remote
from ..fitting.finisher import ExplorationFinisher

# -----------------------------------------------------------------

class ModelerBase(Configurable):

    """
    This class ...
    """

    __metaclass__ = ABCMeta

    # -----------------------------------------------------------------

    def __init__(self, config=None, interactive=False):

        """
        The constructor ...
        :param config:
        :param interactive:
        """

        # Call the constructor of the base class
        super(ModelerBase, self).__init__(config, interactive)

        # The path to the modeling directory
        self.modeling_path = None

        # The modeling environment
        self.environment = None

        # The modeling configuration
        self.modeling_config = None

        # Platform moderator
        self.moderator = None

        # The modeling history
        self.history = None

        # Fixed names for the fitting run and the model
        self.fitting_run_name = "run_1"
        self.model_name = "model_a"
        self.representation_name = "highres"

        # Parameter ranges
        self.parameter_ranges = None

        # The parameter explorer instance
        self.explorer = None

        # The SED fitter instance
        self.fitter = None

        # The exploration finisher
        self.finisher = None

    # -----------------------------------------------------------------

    @property
    def configured_fitting_host_ids(self):

        """
        This function ...
        :return:
        """

        if self.modeling_config.fitting_host_ids is None: return []
        else: return self.modeling_config.fitting_host_ids

    # -----------------------------------------------------------------

    @property
    def has_configured_fitting_host_ids(self):

        """
        This function ...
        :return:
        """

        return len(self.configured_fitting_host_ids) > 0

    # -----------------------------------------------------------------

    @property
    def multiple_generations(self):

        """
        This function ...
        :return:
        """

        return self.config.ngenerations > 1

    # -----------------------------------------------------------------

    def setup(self, **kwargs):

        """
        This function ...
        :param kwargs:
        :return:
        """

        # Call the setup function of the base class
        super(ModelerBase, self).setup(**kwargs)

        # Set the path to the modeling directory
        self.modeling_path = self.config.path

        # Check for the presence of the configuration file
        if not fs.is_file(get_config_file_path(self.modeling_path)): raise ValueError("The current working directory (" + self.config.path + ") is not a radiative transfer modeling directory (the configuration file is missing)")
        else: self.modeling_config = load_modeling_configuration(self.modeling_path)

        # Set execution platforms
        self.set_platforms()

        # Check the number of generations
        if self.config.ngenerations > 1 and self.moderator.any_remote: raise ValueError("When remote execution is enabled, the number of generations per run can only be one")

        # Load the modeling history
        self.history = load_modeling_history(self.modeling_path)

        # Clear remotes
        if self.config.clear_remotes:
            for host_id in self.moderator.all_host_ids:

                # Inform the user
                log.info("Clearing remote '" + host_id + "' ...")

                # Setup the remote
                remote = Remote()
                if not remote.setup(host_id): log.warning("Could not connect to remote host '" + host_id + "'")

                # Clear temporary directory
                remote.clear_pts_temp()

                # Clear sessions
                remote.close_all_screen_sessions()
                remote.close_all_tmux_sessions()

        # Deploy SKIRT and PTS
        if self.config.deploy: self.deploy()

    # -----------------------------------------------------------------

    def set_platforms(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Determining execution platforms ...")

        # Setup the platform moderator
        self.moderator = PlatformModerator()

        # Set platform(s) for fitting (simulations)
        if self.config.fitting_local: self.moderator.add_local("fitting")
        elif self.config.fitting_remotes is not None: self.moderator.add_ensemble("fitting", self.config.fitting_remotes)
        elif self.modeling_config.fitting_host_ids is None: self.moderator.add_local("fitting")
        else: self.moderator.add_ensemble("fitting", self.modeling_config.fitting_host_ids)

        # Other computations
        if self.config.local: self.moderator.add_local("other")
        elif self.config.remotes is not None: self.moderator.add_single("other", self.config.remotes)
        elif self.modeling_config.host_ids is None: self.moderator.add_local("other")
        else: self.moderator.add_single("other", self.modeling_config.host_ids)

        # Run the moderator
        self.moderator.run()

    # -----------------------------------------------------------------

    def deploy(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Deploying SKIRT and PTS ...")

        # Create the deployer
        deployer = Deployer()

        # Set the host ids
        deployer.config.host_ids = self.moderator.all_host_ids

        # Set the host id on which PTS should be installed (on the host for extra computations and the fitting hosts
        # that have a scheduling system to launch the pts run_queue command)
        deployer.config.pts_on = self.moderator.all_host_ids

        # Set
        deployer.config.check = self.config.check_versions

        # Set
        deployer.config.update_dependencies = self.config.update_dependencies

        # Run the deployer
        deployer.run()

    # -----------------------------------------------------------------

    def fit(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Fitting radiative transfer models ...")

        # Configure the fitting
        if not self.history.has_configured_fit: self.configure_fit()

        # Initialize the fitting
        if not self.history.has_initialized_fit: self.initialize_fit()

        # Load the generations table
        generations = get_generations_table(self.modeling_path, self.fitting_run_name)

        # If we do multiple generations at once
        if self.multiple_generations:

            # Start: launch the initial generation
            self.start()

            # Advance: launch generations 0 -> (n-1)
            repeat(self.advance, self.config.ngenerations)

            # Finish
            self.finish()

        # We just do one generation now, or finish
        else:

            # If finishing the generation is requested
            if self.config.finish: self.finish()

            # If this is the initial generation
            elif generations.last_generation_name is None: self.start()

            # Advance the fitting with a new generation
            else: self.advance()

    # -----------------------------------------------------------------

    @abstractmethod
    def configure_fit(self):

        """
        This function ...
        :return:
        """

        pass

    # -----------------------------------------------------------------

    @abstractmethod
    def initialize_fit(self):

        """
        This function ...
        :return:
        """

        pass

    # -----------------------------------------------------------------

    def start(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Starting with a randomly created generation ...")

        # Explore
        self.explore()

    # -----------------------------------------------------------------

    def advance(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Advancing the fitting with a new generation ...")

        # Load the generations table
        generations = get_generations_table(self.modeling_path, self.fitting_run_name)

        # Check whether there is a generation preceeding this one
        if generations.last_generation_name is None: raise RuntimeError("Preceeding generation cannot be found")

        # Debugging
        log.debug("Previous generation: " + generations.last_generation_name)

        # If some generations have not finished, check the status of and retrieve simulations
        if generations.has_unfinished and self.has_configured_fitting_host_ids: self.synchronize()

        # Debugging
        if generations.has_finished: log.debug("There are finished generations: " + stringify.stringify(generations.finished_generations)[1])
        if has_unevaluated_generations(self.modeling_path, self.fitting_run_name): log.debug("There are unevaluated generations: " + stringify.stringify(get_unevaluated_generations(self.modeling_path, self.fitting_run_name))[1])

        # If some generations have finished, fit the SED
        if generations.has_finished and has_unevaluated_generations(self.modeling_path, self.fitting_run_name): self.fit_sed()

        # If all generations have finished, explore new generation of models
        if generations.all_finished: self.explore()

        # Do SED fitting after the exploration step if it has been performed locally (simulations are done, evaluation can be done directly)
        #if self.moderator.single_is_local("fitting"): self.finish()

    # -----------------------------------------------------------------

    def synchronize(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Synchronizing with the remotes (retrieving and analysing finished models) ...")

        # Create the remote synchronizer
        synchronizer = RemoteSynchronizer()

        # Set the host IDs
        synchronizer.config.host_ids = self.modeling_config.fitting_host_ids

        # Run the remote synchronizer
        synchronizer.run()

    # -----------------------------------------------------------------

    def fit_sed(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Fitting the SED to the finished generations ...")

        # Configuration settings
        config = dict()
        config["name"] = self.fitting_run_name

        # Create the SED fitter
        self.fitter = SEDFitter(config)

        # Add an entry to the history
        self.history.add_entry(SEDFitter.command_name())

        # Run the fitter
        self.fitter.run()

        # Mark the end and save the history file
        self.history.mark_end()

    # -----------------------------------------------------------------

    def explore(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Exploring the parameter space ...")

        # Configuration settings
        config = dict()
        config["name"] = self.fitting_run_name

        # Create the parameter explorer
        self.explorer = ParameterExplorer(config)

        # Add an entry to the history
        self.history.add_entry(ParameterExplorer.command_name())

        # Set the working directory
        self.explorer.config.path = self.modeling_path

        # Set the remote host IDs
        self.explorer.config.remotes = self.moderator.host_ids_for_ensemble("fitting")
        self.explorer.config.attached = self.config.fitting_attached

        # Set the number of generations
        #if self.config.ngenerations is not None: explorer.config.ngenerations = self.config.ngenerations
        # NO: THIS ALWAYS HAVE TO BE ONE: BECAUSE HERE IN THIS CLASS WE ALREADY USE REPEAT(SELF.ADVANCE)
        # IF NGENERATIONS > 1, THE CONTINUOUSOPTIMIZER IS USED INSTEAD OF THE STEPWISEOPTIMIZER
        self.explorer.config.ngenerations = 1

        # Set the number of simulations per generation
        if self.config.nsimulations is not None: self.explorer.config.nsimulations = self.config.nsimulations

        # Set other settings
        self.explorer.config.npackages_factor = self.config.npackages_factor
        self.explorer.config.increase_npackages = self.config.increase_npackages
        #explorer.config.refine_wavelengths = self.config.refine_wavelengths
        self.explorer.config.refine_spectral = self.config.refine_spectral
        #explorer.config.refine_dust = self.config.refine_dust
        self.explorer.config.refine_spatial = self.config.refine_spatial
        self.explorer.config.selfabsorption = self.config.selfabsorption
        self.explorer.config.transient_heating = self.config.transient_heating

        # Set the input
        input_dict = dict()
        if self.parameter_ranges is not None: input_dict["ranges"] = self.parameter_ranges

        # Run the parameter explorer
        self.explorer.run(**input_dict)

        # Mark the end and save the history file
        self.history.mark_end()
        self.history.save()

    # -----------------------------------------------------------------

    def finish(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Finishing the parameter exploration ...")

        # Configuration settings
        settings = dict()
        settings["name"] = self.fitting_run_name

        # Set the input
        input_dict = dict()

        # Create the exploration finisher
        self.finisher = ExplorationFinisher(settings)

        # Add an entry to the history
        self.history.add_entry(ExplorationFinisher.command_name())

        # Run the finisher
        self.finisher.run(**input_dict)

        # Mark the end and save the history file
        self.history.mark_end()
        self.history.save()

    # -----------------------------------------------------------------

    def write(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Writing ...")

# -----------------------------------------------------------------
