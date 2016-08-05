#!/usr/bin/env python
# -*- coding: utf8 -*-
# *****************************************************************
# **       PTS -- Python Toolkit for working with SKIRT          **
# **       © Astronomical Observatory, Ghent University          **
# *****************************************************************

# Import the relevant PTS classes and modules
from .fetch import definition
from ...core.basics.host import find_host_ids

# -----------------------------------------------------------------

# Add required settings
definition.add_required("remote", "string", "the remote host to use for creating the GALEX and SDSS data", choices=find_host_ids())

# Add flags
definition.add_flag("errors", "also download the error frames from the DustPedia archive")

# -----------------------------------------------------------------
