#!/usr/bin/env python
# -*- coding: utf8 -*-
# *****************************************************************
# **       PTS -- Python Toolkit for working with SKIRT          **
# **       © Astronomical Observatory, Ghent University          **
# *****************************************************************

# Import the relevant PTS classes and modules
from pts.core.basics.configuration import ConfigurationDefinition
from pts.magic.view.html import scales, colormaps, zooms

# -----------------------------------------------------------------

default_scale = "log"
default_colormap = "viridis"
default_zoom = "toFit"

# -----------------------------------------------------------------

# Create the configuration
definition = ConfigurationDefinition(log_path="log", config_path="config")
definition.add_flag("show", "show the page", False)

# Filters
definition.add_optional("filters", "filter_list", "filters")

# Preload
definition.add_flag("preload_all", "preload all images", False)
definition.add_optional("preload", "filter_list", "filters for which to preload the image")

# View settings
definition.add_optional("scale", "string", "scale", default_scale, choices=scales)
definition.add_optional("colormap", "string", "color map", default_colormap, choices=colormaps)
definition.add_optional("zoom", "string", "zoom function", default_zoom, choices=zooms)

definition.add_flag("png", "convert to png", False)
definition.add_flag("dynamic", "create the viewers dynamically", False)
definition.add_flag("menubar", "add menubars", True)

# -----------------------------------------------------------------