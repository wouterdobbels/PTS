#!/usr/bin/env python
# -*- coding: utf8 -*-
# *****************************************************************
# **       PTS -- Python Toolkit for working with SKIRT          **
# **       © Astronomical Observatory, Ghent University          **
# *****************************************************************

## \package pts.modeling.analysis.component Contains the AnalysisComponent class.

# -----------------------------------------------------------------

# Ensure Python 3 compatibility
from __future__ import absolute_import, division, print_function

# Import astronomical modules
from astropy.utils import lazyproperty

# Import the relevant PTS classes and modules
from ..component.galaxy import GalaxyModelingComponent
from ...core.tools import filesystem as fs
from ...core.launch.timing import TimingTable
from ...core.launch.memory import MemoryTable
from .info import AnalysisRunInfo
from .run import AnalysisRun

# -----------------------------------------------------------------

class AnalysisComponent(GalaxyModelingComponent):
    
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
        super(AnalysisComponent, self).__init__(*args, **kwargs)

        # -- Attributes --

        # The path to the timing table
        self.timing_table_path = None

        # The path to the memory table
        self.memory_table_path = None

    # -----------------------------------------------------------------

    def setup(self, **kwargs):

        """
        This function ...
        :return:
        """

        # Call the setup function of the base class
        super(AnalysisComponent, self).setup()

        # Timing table --

        # Set the path to the timing table
        self.timing_table_path = fs.join(self.analysis_path, "timing.dat")

        # Initialize the timing table if necessary
        if not fs.is_file(self.timing_table_path):

            # Create the table and save it
            timing_table = TimingTable()
            timing_table.saveto(self.timing_table_path)

        # Memory table --

        # Set the path to the memory table
        self.memory_table_path = fs.join(self.analysis_path, "memory.dat")

        # Initialize the memory table if necessary
        if not fs.is_file(self.memory_table_path):

            # Create the table and save it
            memory_table = MemoryTable()
            memory_table.saveto(self.memory_table_path)

    # -----------------------------------------------------------------

    @lazyproperty
    def timing_table(self):

        """
        This function ...
        :return:
        """

        return TimingTable.from_file(self.timing_table_path)

    # -----------------------------------------------------------------

    @lazyproperty
    def memory_table(self):

        """
        This function ...
        :return:
        """

        return MemoryTable.from_file(self.memory_table_path)

    # -----------------------------------------------------------------

    @property
    def analysis_run_names(self):

        """
        This function ...
        :return:
        """

        return fs.directories_in_path(self.analysis_path, returns="name")

    # -----------------------------------------------------------------

    def get_run_path(self, run_name):

        """
        This function ...
        :param run_name:
        :return:
        """

        path = fs.join(self.analysis_path, run_name)
        return path

    # -----------------------------------------------------------------

    def get_run_info(self, run_name):

        """
        This function ...
        :param run_name:
        :return:
        """

        path = fs.join(self.get_run_path(run_name), "info.dat")
        return AnalysisRunInfo.from_file(path)

    # -----------------------------------------------------------------

    def get_run(self, run_name):

        """
        This function ...
        :param run_name:
        :return:
        """

        info_path = fs.join(self.get_run_path(run_name), "info.dat")
        return AnalysisRun.from_info(info_path)

# -----------------------------------------------------------------
