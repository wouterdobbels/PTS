#!/usr/bin/env python
# -*- coding: utf8 -*-
# *****************************************************************
# **       PTS -- Python Toolkit for working with SKIRT          **
# **       © Astronomical Observatory, Ghent University          **
# *****************************************************************

# Import the relevant PTS classes and modules
from pts.core.basics.configuration import ConfigurationDefinition
from pts.modeling.core.environment import load_modeling_environment_cwd

# -----------------------------------------------------------------

# Load environment and model suite
environment = load_modeling_environment_cwd()
suite = environment.static_model_suite

# -----------------------------------------------------------------

dust_and_stellar = ["dust", "stellar"]

# -----------------------------------------------------------------

# Create the configuration
definition = ConfigurationDefinition(log_path="log", config_path="config")

# No models?
if not suite.has_models: raise ValueError("There are currently no models")

# The model name
definition.add_required("name", "string", "name of the model to be adapted", choices=suite.model_names)

# Dust or stellar
definition.add_positional_optional("dust_or_stellar", "string_list", "adapt dust or stellar component(s)", default=dust_and_stellar, choices=dust_and_stellar)

# Name of dust or stellar component to adapt
definition.add_positional_optional("component_name", "string", "name of the dust/stellar component to adapt (only when either 'stellar' or 'dust' is selected)")

# -----------------------------------------------------------------

# Show after adapting
definition.add_flag("show", "show the components after the model is built", True)

# -----------------------------------------------------------------

definition.add_flag("use_defaults", "use default parameter values", False)

# -----------------------------------------------------------------

definition.add_optional("metallicity", "positive_real", "metallicity for templates") # no default or it is used!

# -----------------------------------------------------------------

# Star formation (Mappings)
definition.add_optional("default_ionizing_compactness", "real", "compactness", 6.)
definition.add_optional("default_ionizing_pressure", "quantity", "pressure", "1e12 K/m3", convert_default=True)
definition.add_optional("default_covering_factor", "real", "covering factor", 0.2)

# -----------------------------------------------------------------