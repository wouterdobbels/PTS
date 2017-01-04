#!/usr/bin/env python
# -*- coding: utf8 -*-
# *****************************************************************
# **       PTS -- Python Toolkit for working with SKIRT          **
# **       © Astronomical Observatory, Ghent University          **
# *****************************************************************

## \package pts.core.plot.timeline Contains the TimeLinePlotter class, which is used to create timeline diagrams
#  of the different phases of a SKIRT simulation.

# -----------------------------------------------------------------

# Ensure Python 3 compatibility
from __future__ import absolute_import, division, print_function

# Import standard modules
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.ticker import FormatStrFormatter
from matplotlib import rc

# Import the relevant PTS classes and modules
from .plotter import Plotter
from ..tools.logging import log
from ..tools import filesystem as fs
from ..extract.timeline import TimeLineExtractor
from ..basics.configurable import Configurable
from ..simulation.discover import SimulationDiscoverer

# -----------------------------------------------------------------

rc('text', usetex=True)

# -----------------------------------------------------------------

# Define the colors for the different simulation phases in the plot
colors = {"setup": 'r',         # setup -> red
          "stellar": 'g',       # stellar emission -> green
          "comm": '#FF7626',    # communication -> orange
          "spectra": 'm',       # spectra calculation -> magenta
          "dust": 'c',          # dust emission -> cyan
          "write": 'y',         # writing -> yellow
          "wait": 'b',          # waiting -> blue
          "other": 'k'}         # other -> black

# Define the names identifying the different phases in the plot
phase_label_names = {"setup": "setup",
                     "stellar": "stellar",
                     "comm": "communication",
                     "spectra": "spectra",
                     "dust": "dust",
                     "write": "write",
                     "wait": "waiting",
                     "other": "other"}

# -----------------------------------------------------------------

class BatchTimeLinePlotter(Configurable):

    """
    This class ...
    """

    def __init__(self, config=None):

        """
        The constructor ...
        :param config:
        """

        # Call the constructor of the base class
        super(BatchTimeLinePlotter, self).__init__(config)

        # The simulations
        self.simulations = []

        # The timelines
        self.timelines = dict()

        # The data
        self.single_data = dict()
        self.multi_data = None

    # -----------------------------------------------------------------

    def run(self, **kwargs):

        """
        This function ...
        :param kwargs:
        :return:
        """

        # 1. Call the setup function
        self.setup(**kwargs)

        # 2. Extract
        self.extract()

        # 3. Prepare
        self.prepare()

        # 4. Writing
        self.write()

        # 5. Plot
        self.plot()

    # -----------------------------------------------------------------

    def setup(self, **kwargs):

        """
        This function ...
        :param kwargs:
        :return:
        """

        # Call the setup function of the base class
        super(BatchTimeLinePlotter, self).setup(**kwargs)

        # Load simulations from working directory if none have been added
        if len(self.simulations) == 0:

            # Inform the user
            log.info("Loading simulations ...")

            # Create the simulation discoverer
            discoverer = SimulationDiscoverer()
            discoverer.config.path = self.config.path
            discoverer.config.list = False

            # Run the simulation discoverer
            discoverer.run()

            # Set the simulations
            self.simulations = discoverer.simulations_single_ski

    # -----------------------------------------------------------------

    @property
    def simulation_prefix(self):

        """
        This function ...
        :return:
        """

        return self.simulations[0].prefix()

    # -----------------------------------------------------------------

    def extract(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Extracting the timelines ...")

        # Loop over the simulations
        for simulation in self.simulations:

            # Create a TimeLineExtractor instance
            extractor = TimeLineExtractor()

            # Run the timeline extractor
            timeline = extractor.run(simulation)

            # Get the simulation output path
            output_path = simulation.output_path

            # Check whether unique
            if output_path in self.timelines: raise RuntimeError("Multiple simulations have their output in the '" + output_path + "' directory")

            # Add the timeline
            self.timelines[output_path] = timeline

    # -----------------------------------------------------------------

    @property
    def has_multi(self):

        """
        This function ...
        :return:
        """

        return len(self.timelines) > 1

    # -----------------------------------------------------------------

    def prepare(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Preparing the data for plotting ...")

        # Prepare data for single-simulation plots
        self.prepare_single()

        # Prepare for multi-simulation plot
        if self.has_multi: self.prepare_multi()

    # -----------------------------------------------------------------

    def prepare_single(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Preparing the timeline data for making single-simulation plots ...")

        # Loop over the timelines
        for output_path in self.timelines:

            # Get the timeline
            timeline = self.timelines[output_path]

            # Check the timeline
            check_timeline(timeline)

            # Get a list of the different process ranks
            ranks = np.unique(timeline["Process rank"])

            # Initialize the data structure to contain the start times and endtimes for the different processes,
            # indexed on the phase
            data = []

            # Skipped entries
            skipped = []

            nphases = 0

            counter = 0

            previous_rank = 0

            # Iterate over the different entries in the timeline table
            for i in range(len(timeline)):

                rank = timeline["Process rank"][i]

                if rank == 0:

                    nphases += 1

                    # Few special cases where we want the phase indicator to just say 'other'
                    phase = timeline["Phase"][i]
                    if phase is None or phase == "start" or isinstance(phase, np.ma.core.MaskedConstant): phase = "other"

                    # Don't plot 'other' phases
                    if phase == "other" and not self.config.other:
                        skipped.append(i)
                        continue

                    # Add the data
                    data.append([phase, [], []])
                    data[len(data) - 1][1].append(timeline["Start time"][i])
                    data[len(data) - 1][2].append(timeline["End time"][i])

                else:

                    if rank != previous_rank: counter = 0

                    # Few special cases where we want the phase indicator to just say 'other'
                    phase = timeline["Phase"][i]
                    if phase is None or phase == "start" or isinstance(phase, np.ma.core.MaskedConstant): phase = "other"

                    # Don't plot 'other' phases
                    if phase == "other" and not self.config.other:
                        skipped.append(i)
                        continue

                    #index = i % nphases
                    #if index in skipped:
                    #    continue # skip skipped entries

                    index = counter

                    data[index][1].append(timeline["Start time"][i])
                    data[index][2].append(timeline["End time"][i])

                    counter += 1
                    previous_rank = rank

            # Add the data
            self.single_data[output_path] = (ranks, data)

    # -----------------------------------------------------------------

    def prepare_multi(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Preparing the timeline data for making multi-simulation plots ...")

        # Initialize data structures
        data = []
        nprocs_list = []

        data.append(["setup", [], []])
        data.append(["stellar", [], []])
        data.append(["spectra", [], []])
        data.append(["dust", [], []])
        data.append(["write", [], []])
        data.append(["wait", [], []])
        data.append(["comm", [], []])

        # The simulation names
        simulation_names = []

        # Loop over the timelines
        for output_path in self.timelines:

            # Get the timeline
            timeline = self.timelines[output_path]

            # Get the number of processes
            nprocesses = timeline.nprocesses

            # Get the average runtimes for the different phases corresponding to the current processor count
            setup_time = timeline.setup * nprocesses
            stellar_time = timeline.stellar * nprocesses
            spectra_time = timeline.spectra * nprocesses
            dust_time = timeline.dust * nprocesses
            writing_time = timeline.writing * nprocesses
            waiting_time = timeline.waiting * nprocesses
            communication_time = timeline.communication * nprocesses

            total = 0.0

            # Setup
            data[0][1].append(total)
            total += setup_time
            data[0][2].append(total)

            # Stellar
            data[1][1].append(total)
            total += stellar_time
            data[1][2].append(total)

            # Spectra
            data[2][1].append(total)
            total += spectra_time
            data[2][2].append(total)

            # Dust
            data[3][1].append(total)
            total += dust_time
            data[3][2].append(total)

            # Writing
            data[4][1].append(total)
            total += writing_time
            data[4][2].append(total)

            # Waiting
            data[5][1].append(total)
            total += waiting_time
            data[5][2].append(total)

            # Communication
            data[6][1].append(total)
            total += communication_time
            data[6][2].append(total)

            # Add the process count
            nprocs_list.append(nprocesses)

            # Add the simulation name
            simulation_name = fs.name(output_path)
            simulation_names.append(simulation_name)

        # Set the data
        self.multi_data = (nprocs_list, simulation_names, data)

    # -----------------------------------------------------------------

    def write(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Writing ...")

        # Write the extracted timelines
        self.write_timelines()

        # Write the data
        self.write_data()

    # -----------------------------------------------------------------

    def write_timelines(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Writing the timelines ...")

        # Loop over the data
        for output_path in self.timelines:

            # Determine path
            if self.config.output is not None: path = fs.join(self.config.output, "timeline_" + fs.name(output_path) + ".dat")
            else: path = fs.join(output_path, "timeline.dat")

            # Write the timeline
            self.timelines[output_path].saveto(path)

    # -----------------------------------------------------------------

    def write_data(self):

        """
        This function ...
        :return:
        """

        pass

    # -----------------------------------------------------------------

    def plot(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Plotting ...")

        # Plot single
        self.plot_single()

        # Plot multi
        if self.has_multi: self.plot_multi()

    # -----------------------------------------------------------------

    def plot_single(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Plotting timelines of individual simulations ...")

        # Loop over the data
        for output_path in self.single_data:

            # Debugging
            log.debug("Plotting timeline for the " + fs.name(output_path) + " path simulation ...")

            # Get the data
            ranks, data = self.single_data[output_path]

            # Determine path
            if self.config.output is not None: path = fs.join(self.config.output, "timeline_" + fs.name(output_path) + ".pdf")
            else: path = fs.join(output_path, "timeline.pdf")

            # Create the plot
            create_timeline_plot(data, ranks, path)

    # -----------------------------------------------------------------

    def plot_multi(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Plotting a timeline of the CPU time of all simulations ...")

        # Set the plot title
        title = "Timeline of CPU time"

        # Get the data
        nprocs_list, simulation_names, data = self.multi_data

        # Determine the path
        if self.config.output is not None: path = fs.join(self.config.output, "timeline_cputime.pdf")
        else: path = fs.join(self.config.path, "timeline_cputime.pdf")

        # Create the plot
        create_timeline_plot(data, nprocs_list, path, percentages=True, totals=True, unordered=True, cpu=True, title=title, ylabels=simulation_names, yaxis="Simulations")

# -----------------------------------------------------------------

class TimeLinePlotter(Plotter):

    """
    An instance of the TimeLinePlotter class is used to create timeline diagrams for the different simulation phases
    """

    def __init__(self):

        """
        The constructor ...
        :return:
        """

        # Call the constructor of the base class
        super(TimeLinePlotter, self).__init__()

        # -- Attributes --

        # A list of the process ranks
        self.ranks = None

    # -----------------------------------------------------------------

    @staticmethod
    def default_input():

        """
        This function ...
        :return:
        """

        return "timeline.dat"

    # -----------------------------------------------------------------

    def prepare_data(self):

        """
        This function ...
        :return:
        """

        # Get a list of the different process ranks
        self.ranks = np.unique(self.table["Process rank"])

        # Initialize the data structure to contain the start times and endtimes for the different processes,
        # indexed on the phase
        self.data = []

        # Iterate over the different entries in the timeline table
        for i in range(len(self.table)):

            if self.table["Process rank"][i] == 0:

                phase = self.table["Phase"][i]

                # Few special cases where we want the phase indicator to just say 'other'
                if phase is None or phase == "start" or isinstance(phase, np.ma.core.MaskedConstant): phase = "other"

                # Add the data
                self.data.append([phase, [], []])
                self.data[len(self.data) - 1][1].append(self.table["Start time"][i])
                self.data[len(self.data) - 1][2].append(self.table["End time"][i])

            else:

                nphases = len(self.data)
                self.data[i % nphases][1].append(self.table["Start time"][i])
                self.data[i % nphases][2].append(self.table["End time"][i])

    # -----------------------------------------------------------------

    def plot(self):

        """
        This function ...
        :param path:
        :return:
        """

        # Inform the user
        log.info("Making the plots...")

        # Create the plot
        plot_path = fs.join(self.output_path, "timeline.pdf")
        create_timeline_plot(self.data, self.ranks, plot_path)

# -----------------------------------------------------------------

def create_timeline_plot(data, procranks, path=None, figsize=(12, 8), percentages=False, totals=False, unordered=False,
                         cpu=False, title=None, ylabels=None, yaxis=None, rpc="r", add_border=False):

    """
    This function actually plots the timeline based on a data structure containing the starttimes and endtimes
    for the different simulation phases
    :param data:
    :param path:
    :param procranks:
    :param figsize:
    :param percentages:
    :param totals:
    :param unordered:
    :param cpu:
    :param title:
    :param ylabels:
    :param yaxis:
    :param rpc: 'rank', 'processes' or 'cores'
    :return:
    """

    # Initialize figure
    plt.figure(figsize=figsize)
    plt.clf()

    ax = plt.gca()

    # Set x axis grid
    ax.xaxis.grid(linestyle="dotted", linewidth=2.0)

    legend_entries = []
    legend_names = []
    unique_phases = []   # A LIST OF THE UNIQUE PHASE NAMES

    # Determine the number of processes
    nprocs = len(procranks)

    # Get the ordering
    if unordered: yticks = np.array(procranks).argsort().argsort()
    else: yticks = procranks

    durations_list = []
    totaldurations = np.zeros(nprocs)
    patch_handles = []

    # Make the timeline plot, consisting of a set of bars of the same color for each simulation phase
    for phase, starttimes, endtimes in data:

        durations = np.array(endtimes) - np.array(starttimes)
        durations_list.append(durations)

        totaldurations += durations

        patch_handle = ax.barh(yticks, durations, color=colors[phase], align='center', left=starttimes, alpha=0.8, lw=0)
        patch_handles.append(patch_handle)

        if phase not in unique_phases and not (phase == "comm" and nprocs == 1):

            unique_phases.append(phase)
            legend_entries.append(patch_handle)
            legend_names.append(phase_label_names[phase])

    if percentages:

        # For the different phases
        for phase, patch_handle in enumerate(patch_handles):

            durations = durations_list[phase]

            for sorting_number, rectangle in enumerate(patch_handle.get_children()):

                duration = durations[sorting_number]
                percentage = float(duration) / float(totaldurations[sorting_number]) * 100.0

                x = 0.5 * rectangle.get_width() + rectangle.get_x()
                y = 0.5 * rectangle.get_height() + rectangle.get_y()

                if rectangle.get_width() > 2000:

                    plt.text(x, y, "%d%%" % percentage, ha='center', va='center', fontsize=10)

    if totals:

        for sorting_number, rectangle in enumerate(patch_handles[-1].get_children()):

            width = rectangle.get_width()
            label_text = str(int(totaldurations[sorting_number]))
            plt.text(rectangle.get_x() + width + 0.02*rectangle.get_x(), rectangle.get_y() + rectangle.get_height() / 2., label_text, ha="left", va="center", fontsize=10)

    if unordered:

        plt.yticks(yticks, procranks)

    else:

        ax.set_yticks(procranks)
        ax.set_yticklabels(procranks)

    ax.xaxis.set_major_formatter(FormatStrFormatter('%d'))
    ax.yaxis.set_major_formatter(FormatStrFormatter('%d'))

    if not add_border:
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.spines['bottom'].set_visible(False)
        ax.spines['left'].set_visible(False)
        ax.tick_params(axis=u'both', which=u'both', length=0)

    # Format the axis ticks and labels
    if cpu: ax.set_xlabel('CPU time (s)', fontsize='large')
    else: ax.set_xlabel('Time (s)', fontsize='large')

    # Set y label
    if rpc == 'r': ax.set_ylabel('Process rank', fontsize='large')
    elif rpc == 'p': ax.set_ylabel('Number of processes', fontsize='large')
    elif rpc == 'c': ax.set_ylabel('Number of cores', fontsize='large')

    #ax.yaxis.grid(True)

    # Custom y labels
    if ylabels is not None:
        plt.yticks(yticks, ylabels)
        ax.set_ylabel("")

    # Custom y axis label
    if yaxis is not None: ax.set_ylabel(yaxis)

    if nprocs == 1:

        ax.set_frame_on(False)
        fig = plt.gcf()
        fig.set_size_inches(10,2)
        ax.xaxis.tick_bottom()
        ax.yaxis.set_visible(False)

    # Shrink current axis's height by 20% on the bottom
    box = ax.get_position()
    ax.set_position([box.x0, box.y0 + box.height * 0.2, box.width, box.height * 0.8])

    # Set the plot title
    #if title is None: plt.title("Timeline of the different simulation phases")
    #else: plt.title(title)
    if title is not None: plt.suptitle(title, fontsize=20)

    # Put a legend below current axis
    ax.legend(legend_entries, legend_names, loc='upper center', bbox_to_anchor=(0.5, -0.10), fancybox=True, shadow=False, ncol=4, prop={'size': 12})

    # Save the figure
    if path is not None: plt.savefig(path, bbox_inches="tight", pad_inches=0.40)
    else: plt.show()
    plt.close()

# -----------------------------------------------------------------

def check_timeline(timeline):

    """
    This function ...
    :param timeline:
    :return:
    """

    phases = []

    # Iterate over the different entries in the timeline table
    for i in range(len(timeline)):

        if timeline["Process rank"][i] == 0:

            phase = timeline["Phase"][i]

            phases.append(phase)

        else:

            nphases = len(phases)
            index = i % nphases

            phase = timeline["Phase"][i]

            #print(phases[index], phase)

            if phases[index] != phase: raise RuntimeError("Timeline is not consistent")

# -----------------------------------------------------------------
