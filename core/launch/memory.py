#!/usr/bin/env python
# -*- coding: utf8 -*-
# *****************************************************************
# **       PTS -- Python Toolkit for working with SKIRT          **
# **       © Astronomical Observatory, Ghent University          **
# *****************************************************************

## \package pts.core.launch.memory Contains the MemoryTable class.

# -----------------------------------------------------------------

# Ensure Python 3 compatibility
from __future__ import absolute_import, division, print_function

# Import the relevant PTS classes and modules
from ..basics.table import SmartTable

# -----------------------------------------------------------------

class MemoryTable(SmartTable):

    """
    This class ...
    """

    @classmethod
    def initialize(cls):

        """
        This function ...
        :return:
        """

        # Create the table
        names = ["Simulation name", "Timestamp", "Host id", "Cluster name", "Cores", "Threads per core",
                 "Processes", "Wavelengths", "Dust cells", "Self-absorption", "Transient heating", "Data-parallel",
                 "Number of pixels", "Peak memory usage"]
        dtypes = [str, str, str, str, int, int, int, int, int, bool, bool, bool, int, float]

        # Call the constructor of the base class
        table = cls(names=names, dtype=dtypes, masked=True)

        # Set the column units
        table["Peak memory usage"].unit = "GB" # memory usage is expressed in gigabytes

        # Set the path
        table.path = None

        # Return the memory table instance
        return table

    # -----------------------------------------------------------------

    @classmethod
    def from_file(cls, path):

        """
        This function ...
        :return:
        """

        # Open the table
        table = super(MemoryTable, cls).read(path, format="ascii.ecsv")

        # Set the path
        table.path = path

        # Return the table
        return table

    # -----------------------------------------------------------------

    def add_entry(self, name, timestamp, host_id, cluster_name, cores, threads_per_core, processes, wavelengths,
                  dust_cells, selfabsorption, transient_heating, data_parallel, npixels, peak_memory_usage):

        """
        This function ...
        :param name:
        :param timestamp:
        :param host_id:
        :param cluster_name:
        :param cores:
        :param threads_per_core:
        :param processes:
        :param wavelengths:
        :param dust_cells:
        :param selfabsorption:
        :param transient_heating:
        :param data_parallel:
        :param npixels
        :param peak_memory_usage:
        :return:
        """

        values = [name, timestamp, host_id, cluster_name, cores, threads_per_core, processes, wavelengths,
                  dust_cells, selfabsorption, transient_heating, data_parallel, npixels, peak_memory_usage]

        # Resize string columns for longer entries
        self._resize_string_columns(values)

        # Add a row to the table
        self.add_row(values)

# -----------------------------------------------------------------
