#!/usr/bin/env python
# -*- coding: utf8 -*-
# *****************************************************************
# **       PTS -- Python Toolkit for working with SKIRT          **
# **       © Astronomical Observatory, Ghent University          **
# *****************************************************************

# Import the relevant PTS classes and modules
from pts.core.config.launch import definition
from pts.core.remote.host import find_host_ids

# -----------------------------------------------------------------

# Add required arguments
definition.add_required("ski", "file_path", "the name/path of the ski file")

# Simulation settings
definition.add_flag("relative", "treats the given input and output paths as being relative to the ski/fski file")

# -----------------------------------------------------------------

# Add positional arguments
definition.add_positional_optional("remote", "string", "the remote host on which to run the simulation (if none is specified, the simulation is run locally", choices=find_host_ids())

# Remote and parallelization
definition.add_optional("cluster", "string", "the name of the cluster", letter="c")
definition.add_optional("parallel", "integer_tuple", "the parallelization scheme (processes, threads)", letter="p")
definition.add_optional("walltime", "duration", "an estimate for the walltime of the simulation for the specified parallelization scheme")
definition.add_flag("data_parallel", "enable data parallelization", None)

# -----------------------------------------------------------------
