#!/usr/bin/env python
# -*- coding: utf8 -*-
# *****************************************************************
# **       PTS -- Python Toolkit for working with SKIRT          **
# **       © Astronomical Observatory, Ghent University          **
# *****************************************************************

## \package pts.core.basics.configuration Contains the configuration class.

# -----------------------------------------------------------------

# Ensure Python 3 compatibility
from __future__ import absolute_import, division, print_function

# Import standard modules
from abc import ABCMeta, abstractmethod
from types import NoneType
import sys
import argparse
from collections import OrderedDict

# Import the relevant PTS classes and modules
from .map import Map
from ..tools import parsing
from ..tools import filesystem as fs
from ..tools.logging import log

# -----------------------------------------------------------------

class Configuration(Map):

    """
    This function ...
    """

    @classmethod
    def from_file(cls, path):

        """
        This function ...
        :param path:
        :return:
        """

        # Create the config
        config = cls()

        # Load the settings
        with open(path, 'r') as configfile: load_mapping(configfile, config)

        # Return the config
        return config

    # -----------------------------------------------------------------

    @classmethod
    def from_string(cls, string):

        """
        This function ...
        :param string:
        :return:
        """

        # Create the config
        config = cls()

        # Load the settings
        lines = string.split("\n")
        load_mapping(iter(lines), config)

        # Return the config
        return config

    # -----------------------------------------------------------------

    def to_string(self):

        """
        This function ...
        :return:
        """

        lines = []
        mapping_to_lines(lines, self)
        return "\n".join(lines)

    # -----------------------------------------------------------------

    def save(self, path):

        """
        This function ...
        :param path:
        :return:
        """

        with open(path, 'w') as configfile: write_mapping(configfile, self)

# -----------------------------------------------------------------

def load_mapping(mappingfile, mapping, indent=""):

    """
    This function ...
    :param mappingfile
    :param mapping:
    :param indent:
    :return:
    """

    # STATES:
    # 0: empty line
    # 1: have description
    # 2: we got everything for a certain name
    # 3: section will begin (we expect a { now)
    # 4: inside section

    state = 0
    description = None

    # Loop over the lines in the file
    for line in mappingfile:

        # Strip end-of-line character
        line = line.rstrip("\n")

        # Remove the indent
        line = line.lstrip(indent)

        # Empty line
        if line == "":

            #print("empty", line)
            if state != 2 and state != 0: raise RuntimeError("At empty line and previous state was " + str(state))

            state = 0
            description = None
            continue

        # Description
        if line.startswith("#"):

            #print("comment", line)

            if description is not None:
                assert state == 1
                state = 1
                description += line.split("#")[1].strip()
            else:
                assert state == 0
                state = 1
                description = line.split("#")[1].strip()
            continue

        elif ":" in line:

            # Remove comment after the declaration
            if "#" in line: line = line.split("#")[0]

            try:
                before, after = line.split(":")
            except ValueError: print(line)

            #print("declaration", before, after)

            if after.strip() == "":

                state = 3  # state 3: just before "{" is expected to start subdefinition
                continue

            else:

                state = 2

                if before.endswith("]"):

                    name = before.split("[")[0].strip()
                    specification = before.split("[")[1].split("]")[0].strip()

                else:

                    name = before
                    specification = None

                # Should not happen
                if specification is None: raise ValueError("Invalid line (no specification): " + line)

                # Strip away leading or trailing spaces
                value = after.strip()

                #if specification is None:
                #    value = eval(value)

                if value == "None": value = None
                else:

                    parsing_function = getattr(parsing, specification)
                    value = parsing_function(value)

                #print("definition", value)

                # TODO: incorporate descriptions ??
                mapping[name] = value

                description = None

        # Start of section
        elif line.startswith("{"):

            assert state == 3
            state = 4

            if before.endswith("]"):

                name = before.split("[")[0].strip()
                specification = before.split("[")[1].split("]")[0].strip()

                assert specification == "section"

            else: name = before

            # Initialize the submapping
            mapping[name] = Map()

            # Load the submapping
            load_mapping(mappingfile, mapping[name], indent=indent+"    ")

            state = 2
            description = None

        # End of section or complete definition
        elif line.startswith("}"): return

# -----------------------------------------------------------------

def write_mapping(mappingfile, mapping, indent=""):

    """
    This function ...
    :param mappingfile:
    :param mapping:
    :param indent:
    :return:
    """

    index = 0
    length = len(mapping)
    for name in mapping:

        value = mapping[name]

        if isinstance(value, Map):

            print(indent + name + ":", file=mappingfile)
            print(indent + "{", file=mappingfile)
            write_mapping(mappingfile, value, indent=indent+"    ")
            print(indent + "}", file=mappingfile)

        else:
            ptype, string = stringify(mapping[name])
            print(indent + name + "[" + ptype + "]: " + string, file=mappingfile)

        if index != length - 1: print("", file=mappingfile)
        index += 1

# -----------------------------------------------------------------

def mapping_to_lines(lines, mapping, indent=""):

    """
    This function ...
    :param lines:
    :param mapping:
    :param indent:
    :return:
    """

    index = 0
    length = len(mapping)
    for name in mapping:

        value = mapping[name]

        if isinstance(value, Map):

            lines.append(indent + name + ":")
            lines.append(indent + "{")
            mapping_to_lines(lines, value, indent=indent+"    ")
            lines.append(indent + "}")

        else:

            ptype, string = stringify(mapping[name])
            lines.append(indent + name + " [" + ptype + "]: " + string)

        if index != length - 1: lines.append("")
        index += 1

# -----------------------------------------------------------------

def stringify(value):

    """
    This function ...
    :param value:
    :return:
    """

    if isinstance(value, list):

        strings = []
        ptype = None
        for entry in value:

            parsetype, val = stringify_not_list(entry)

            if ptype is None: ptype = parsetype
            elif ptype != parsetype: raise ValueError("Nonuniform list")

            strings.append(val)

        return ptype + "_list", ",".join(strings)

    else: return stringify_not_list(value)

# -----------------------------------------------------------------

def stringify_not_list(value):

    """
    This function ...
    :param value:
    :return:
    """

    from astropy.units import Quantity
    from astropy.coordinates import Angle

    if isinstance(value, bool): return "boolean", str(value)
    elif isinstance(value, int): return "integer", str(value)
    elif isinstance(value, float): return "real", repr(value)
    elif isinstance(value, basestring): return "string", value
    elif isinstance(value, Quantity): return "quantity", repr(value.value) + " " + str(value.unit)
    elif isinstance(value, Angle): return "angle", repr(value.value) + " " + str(value.unit)
    else: raise ValueError("Unrecognized type: " + str(type(value)))

# -----------------------------------------------------------------

class ConfigurationDefinition(object):

    """
    This function ...
    """

    def __init__(self, prefix=None):

        """
        This function ...
        :param prefix:
        """

        # Prefix
        self.prefix = prefix

        # Dictionary of sections
        self.sections = OrderedDict()
        self.section_descriptions = dict()

        # Dictionary of fixed parameters
        self.fixed = OrderedDict()

        # Dictionary of required parameters
        self.required = OrderedDict()

        # Dictionary of positional optional parameters
        self.pos_optional = OrderedDict()

        # Dictionary of optional parameters
        self.optional = OrderedDict()

        # Dictionary of flags
        self.flags = OrderedDict()

    # -----------------------------------------------------------------

    @classmethod
    def from_file(cls, path):

        """
        This function ...
        :param path:
        :return:
        """

        # Create the definition
        definition = cls()

        # Load the definition
        with open(path, 'r') as configfile: load_definition(configfile, definition)

        # Return the definition
        return definition

    # -----------------------------------------------------------------

    def save(self, path):

        """
        This function ...
        :param path:
        :return:
        """

        # Write the definition
        with open(path, 'w') as configfile: write_definition(self, configfile)

    # -----------------------------------------------------------------

    def set_arguments(self, parser):

        """
        This function ...
        :param parser:
        :return:
        """

        # Required
        for name in self.required:

            real_type = self.required[name][0]
            description = self.required[name][1]
            choices = self.required[name][2]

            # Add prefix
            if self.prefix is not None: name = self.prefix + "/" + name

            # Add argument to argument parser
            parser.add_argument(name, type=real_type, help=description, choices=choices)

        # Positional optional
        for name in self.pos_optional:

            real_type = self.pos_optional[name][0]
            description = self.pos_optional[name][1]
            default = self.pos_optional[name][2]
            choices = self.pos_optional[name][3]

            # Add prefix
            if self.prefix is not None: name = self.prefix + "/" + name

            # Add argument to argument parser
            parser.add_argument(name, type=real_type, help=description, default=default, nargs='?', choices=choices)

        # Optional
        for name in self.optional:

            # (real_type, description, default, letter)
            real_type = self.optional[name][0]
            description = self.optional[name][1]
            default = self.optional[name][2]
            choices = self.optional[name][3]
            letter = self.optional[name][4]

            # Add prefix
            if self.prefix is not None: name = self.prefix + "/" + name

            # Add the argument
            if letter is None: parser.add_argument("--" + name, type=real_type, help=description, default=default, choices=choices)
            else: parser.add_argument("-" + letter, "--" + name, type=real_type, help=description, default=default, choices=choices)

        # Flag
        for name in self.flags:

            # (description, letter)
            description = self.flags[name][0]
            letter = self.flags[name][1]
            default = self.flags[name][2] # True or False

            # Add prefix
            if self.prefix is not None: name = self.prefix + "/" + name

            # Add the argument
            if letter is None:
                if default is False: parser.add_argument("--" + name, action="store_true", help=description)
                else: parser.add_argument("--!" + name, action="store_true", help=description)
            else:
                if default is False: parser.add_argument("-" + letter, "--" + name, action="store_true", help=description)
                else: parser.add_argument("-!" + letter, "--!" + name, action="store_true", help=description)

        # Add arguments of sections
        for section_name in self.sections: self.sections[section_name].set_arguments(parser)

    # -----------------------------------------------------------------

    def get_settings(self, settings, arguments):

        """
        This function ...
        :param settings:
        :param arguments:
        :return:
        """

        # Add fixed
        for name in self.fixed: settings[name] = self.fixed[name][1]

        # Add required
        for name in self.required:

            if self.prefix is not None: argument_name = self.prefix + "/" + name
            else: argument_name = name

            settings[name] = getattr(arguments, argument_name)

        # Add positional optional
        for name in self.pos_optional:

            if self.prefix is not None: argument_name = self.prefix + "/" + name
            else: argument_name = name

            settings[name] = getattr(arguments, argument_name)

        # Add optional
        for name in self.optional:

            if self.prefix is not None: argument_name = self.prefix + "/" + name
            else: argument_name = name

            settings[name] = getattr(arguments, argument_name)

        # Add flags
        for name in self.flags:

            if self.prefix is not None: argument_name = self.prefix + "/" + name
            else: argument_name = name

            default = self.flags[name][2]

            if default: # if default == True

                argument_name = "!" + argument_name
                settings[name] = not getattr(arguments, argument_name)

            else: settings[name] = getattr(arguments, argument_name)

        # Add the configuration settings of the various sections
        for name in self.sections:

            # Create a map for the settings
            settings[name] = Map()

            # Recursively add the settings
            definition = self.sections[name]
            description = self.section_descriptions[name]
            definition.get_settings(settings[name], arguments)

    # -----------------------------------------------------------------

    def add_section(self, name, description):

        """
        This function ...
        :param name:
        :param description:
        :return:
        """

        # Add the section
        self.sections[name] = ConfigurationDefinition(prefix=name)
        self.section_descriptions[name] = description

    # -----------------------------------------------------------------

    def add_fixed(self, name, description, value):

        """
        This function ...
        :param name:
        :param description:
        :param value:
        :return:
        """

        self.fixed[name] = (description, value)

    # -----------------------------------------------------------------

    def add_required(self, name, user_type, description, choices=None):

        """
        This function ...
        :param name:
        :param user_type:
        :param description:
        :param choices:
        :return:
        """

        # Get the real type
        real_type = get_real_type(user_type)

        # Add
        self.required[name] = (real_type, description, choices)

    # -----------------------------------------------------------------

    def add_positional_optional(self, name, user_type, description, default=None, choices=None, convert_default=False):

        """
        This function ...
        :param name:
        :param user_type:
        :param description:
        :param default:
        :param choices:
        :param convert_default:
        :return:
        """

        # Get the real type
        real_type = get_real_type(user_type)

        # Get the real default value
        if convert_default: default = get_real_value(default, real_type)

        # Add
        self.pos_optional[name] = (real_type, description, default, choices)

    # -----------------------------------------------------------------

    def add_optional(self, name, user_type, description, default=None, choices=None, letter=None, convert_default=False):

        """
        This function ...
        :param name:
        :param user_type:
        :param description:
        :param default:
        :param choices:
        :param letter:
        :param convert_default:
        :return:
        """

        if self.prefix is not None and letter is not None: raise ValueError("Cannot assign letter argument for child configuration definition")

        # Get the real type
        real_type = get_real_type(user_type)

        # Get the real default value
        if convert_default: default = get_real_value(default, real_type)

        # Add
        self.optional[name] = (real_type, description, default, choices, letter)

    # -----------------------------------------------------------------

    def add_flag(self, name, description, default=False, letter=None):

        """
        This function ...
        :param name:
        :param description:
        :param default:
        :param letter:
        :return:
        """

        # Add
        self.flags[name] = (description, letter, default)

# -----------------------------------------------------------------

class ConfigurationSetter(object):

    """
    This class ...
    """

    __metaclass__ = ABCMeta

    # -----------------------------------------------------------------

    def __init__(self, name, description=None, add_logging=True, add_cwd=True, log_path=None):

        """
        This function ...
        :param name:
        :param description:
        :param add_logging:
        :param add_cwd:
        :param log_path:
        """

        # Set the name and description
        self.name = name
        self.description = description

        # The configuration definition
        self.definition = None

        # Set options
        self.add_logging = add_logging
        self.add_cwd = add_cwd
        self.log_path = log_path

        # The configuration
        self.config = Configuration()

    # -----------------------------------------------------------------

    @abstractmethod
    def run(self):

        """
        This function ...
        :return:
        """

        pass

    # -----------------------------------------------------------------

    def set_logging_and_cwd(self):

        """
        This function ...
        :return:
        """

        # Add logging options
        if self.add_logging:

            # Log path to absolute path
            log_path = fs.absolute(self.log_path) if self.log_path is not None else fs.cwd()
            self.definition.add_fixed("log_path", "the directory for the log file be written to", log_path)
            self.definition.add_flag("debug", "enable debug output")
            self.definition.add_flag("report", "write a report file")

        # Add the path to the current working directory
        if self.add_cwd: self.definition.add_fixed("path", "the working directory", fs.cwd())

# -----------------------------------------------------------------

class InteractiveConfigurationSetter(ConfigurationSetter):

    """
    This class ...
    """

    def __init__(self, name, description=None, add_logging=True, add_cwd=True, log_path=None):

        """
        The constructor ...
        :param name:
        :param description:
        :param add_logging:
        :param add_cwd:
        :param log_path:
        """

        # Call the constructor of the base class
        super(InteractiveConfigurationSetter, self).__init__(name, description, add_logging, add_cwd, log_path)

    # -----------------------------------------------------------------

    def run(self, definition, prompt_optional=None):

        """
        This function ...
        :param definition:
        :param prompt_optional:
        :return:
        """

        # Set the definition
        self.definition = definition

        # Set logging and cwd
        self.set_logging_and_cwd()

        # Do interactive
        self.interactive(prompt_optional)

        # Return the config
        return self.config

    # -----------------------------------------------------------------

    def interactive(self, prompt_optional):

        """
        This function ...
        :param prompt_optional:
        :return:
        """

        if prompt_optional is None:

            # Ask whether optional parameters have to be shown, or to just use the default values
            log.info("Do you want to configure optional settings (y or n)?")
            log.info("Press ENTER to use the default (True)")

            answer = raw_input("   : ")
            if answer == "": prompt_optional = True
            else: prompt_optional = parsing.boolean(answer)

        add_settings_interactive(self.config, self.definition, prompt_optional=prompt_optional)

# -----------------------------------------------------------------

class ArgumentConfigurationSetter(ConfigurationSetter):

    """
    This class ...
    """

    def __init__(self, name, description=None, add_logging=True, add_cwd=True, log_path=None):

        """
        This function ...
        :param name:
        :param description:
        :param add_logging:
        :param add_cwd:
        :param log_path:
        """

        # Call the constructor of the base class
        super(ArgumentConfigurationSetter, self).__init__(name, description, add_logging, add_cwd, log_path)

        # Create the command-line parser
        self.parser = argparse.ArgumentParser(prog=name, description=description)

        # The parsed arguments
        self.arguments = None

    # -----------------------------------------------------------------

    @staticmethod
    def get_arguments():

        """
        This function ...
        :return:
        """

        return sys.argv[1:]

    # -----------------------------------------------------------------

    def run(self, definition):

        """
        This function ...
        :param definition:
        :return:
        """

        # Set definition
        self.definition = definition

        # Set logging and cwd
        self.set_logging_and_cwd()

        # Parse
        self.parse()

        # Create config
        self.create_config()

        # Return the config
        return self.config

    # -----------------------------------------------------------------

    def parse(self):

        """
        This function ...
        :return:
        """

        # Set arguments
        self.definition.set_arguments(self.parser)

        # Let the parser parse
        self.arguments = self.parser.parse_args()

    # -----------------------------------------------------------------

    def create_config(self):

        """
        This function ...
        :return:
        """

        # Add the settings
        self.definition.get_settings(self.config, self.arguments)

# -----------------------------------------------------------------

class FileConfigurationSetter(ConfigurationSetter):

    """
    This class ...
    """

    def __init__(self, path, name, description=None, add_logging=True, add_cwd=True, log_path=None):

        """
        This function ...
        :param name:
        :param description:
        :param add_logging:
        :param add_cwd:
        :param log_path:
        """

        # Call the constructor of the base class
        super(FileConfigurationSetter, self).__init__(name, description, add_logging, add_cwd, log_path)

        # Set the path to the specified configuration file
        self.path = path

        # The user-provided configuration
        self.user_config = None

    # -----------------------------------------------------------------

    def run(self, definition):

        """
        This function ...
        :param definition:
        :return:
        """

        # Set definition
        self.definition = definition

        # Set logging and cwd
        self.set_logging_and_cwd()

        # Load the user provided configuration
        self.load_config()

        # Create the config (check it against the definition)
        self.create_config()

        # Return the config
        return self.config

    # -----------------------------------------------------------------

    def load_config(self):

        """
        This function ...
        :return:
        """

        self.user_config = Configuration.from_file(self.path)

    # -----------------------------------------------------------------

    def create_config(self):

        """
        This function ...
        :return:
        """

        # TODO: TEMPORARY

        self.config = self.user_config

# -----------------------------------------------------------------

class GraphicalConfigurationSetter(ConfigurationSetter):

    """
    This class ...
    """

    def __init__(self, path, name, description=None, add_logging=True, add_cwd=True, log_path=None):

        """
        This function ...
        :param name:
        :param description:
        :param add_logging:
        :param add_cwd:
        :param log_path:
        """

        # Call the constructor of the base class
        super(GraphicalConfigurationSetter, self).__init__(name, description, add_logging, add_cwd, log_path)



    # -----------------------------------------------------------------

    def run(self, definition):

        """
        This function ...
        :param definition:
        :return:
        """

        # Set definition
        self.definition = definition

        # Set logging and cwd
        self.set_logging_and_cwd()

# -----------------------------------------------------------------

def get_real_type(user_type):

    """
    This function ...
    :param user_type:
    :return:
    """

    if isinstance(user_type, basestring): return getattr(parsing, user_type)
    else: return user_type

# -----------------------------------------------------------------

def get_real_value(default, user_type):

    """
    This function ...
    :param default:
    :param user_type:
    :return:
    """

    return user_type(default)

# -----------------------------------------------------------------

def load_definition(configfile, definition):

    """
    This function ...
    :param configfile:
    :param definition:
    :return:
    """

    # STATES:
    # 0: empty line
    # 1: have description
    # 2: we got everything for a certain name
    # 3: section will begin (we expect a { now)

    state = 0
    description = None

    # Loop over the lines in the file
    for line in configfile:

        # Strip end-of-line character
        line = line.rstrip("\n")

        # Empty line
        if line == "":
            assert state == 2  # 2 means we got everything for a certain name
            state = 0
            description = None
            continue

        # Description
        if line.startswith("#"):

            if description is not None:
                assert state == 1
                state = 1
                description += line.split("#")[1].strip()
            else:
                assert state == 0
                state = 1
                description = line.split("#")[1].strip()
            continue

        elif ":" in line:

            before, after = line.split(":")

            if after.strip() == "":

                state = 3  # state 3: just before "{" is expected to start subdefinition
                continue

            else:

                state = 2
                name = before.split("[")[0].strip()
                specification = before.split("[")[1].split("]")[0].strip().split(", ")

                # value = eval(after)
                value = after

                kind = specification[0]
                user_type = specification[1] if kind != "flag" else None

                if user_type == "str": user_type = str
                elif user_type == "int": user_type = int
                elif user_type == "float": user_type = float
                elif user_type == "bool": user_type = bool # for fixed flags ...
                elif user_type == "None": # for fixed things that should be None

                    user_type = NoneType
                    value = None

                if kind == "fixed":

                    value = user_type(value) if value is not None else None # convert here because the add_fixed function doesn't bother with types now

                    definition.add_fixed(name, description, value)

                elif kind == "required":

                    definition.add_required(name, user_type, description, choices=None)

                elif kind == "pos_optional":

                    definition.add_positional_optional(name, user_type, description, default=value, choices=None, convert_default=True)

                elif kind == "optional":

                    definition.add_optional(name, user_type, description, default=value, choices=None, letter=None, convert_default=True)

                elif kind == "flag":

                    definition.add_flag(name, description, default=value, letter=None)

                else:
                    raise ValueError("Invalid kind of argument: " + kind)

                description = None

        # Start of
        elif line.startswith("{"):

            assert state == 3
            state = 4

            name = before.split("[")[0].strip()
            specification = before.split("[")[1].split("]")[0].strip()

            assert specification == "section"

            # Initialize the configuration definition
            definition.add_section(name, description)

            # Load into the section
            load_definition(configfile, definition.sections[name])

            state = 2
            description = None

        # End of section or complete definition
        elif line.startswith("}"): return

# -----------------------------------------------------------------

def write_definition(definition, configfile, indent=""):

    """
    This function ...
    :param definition:
    :param configfile:
    :param indent:
    :return:
    """

    # Fixed
    for name in definition.fixed:

        description = definition.fixed[name][0]
        value = definition.fixed[name][1]

        print(indent + "# " + description, file=configfile)
        print(indent + name + " [fixed]: " + str(value), file=configfile)

    # Required
    for name in definition.required:

        real_type = definition.required[name][0]
        description = definition.required[name][1]
        choices = definition.required[name][2]

        print(indent + "# " + description, file=configfile)
        print(indent + name + " [required, " + str(real_type) + "]: None", file=configfile)

    # Positional optional
    for name in definition.pos_optional:

        real_type = definition.pos_optional[name][0]
        description = definition.pos_optional[name][1]
        default = definition.pos_optional[name][2]
        choices = definition.pos_optional[name][3]

        print(indent + "# " + description, file=configfile)
        print(indent + name + " [pos_optional, " + str(real_type) + "]: " + str(default), file=configfile)

    # Optional
    for name in definition.optional:

        real_type = definition.optional[name][0]
        description = definition.optional[name][1]
        default = definition.optional[name][2]
        choices = definition.optional[name][3]
        letter = definition.optional[name][4]

        print(indent + "# " + description, file=configfile)
        print(indent + name + " [optional, " + str(real_type) + "]: " + str(default), file=configfile)

    # Flag
    for name in definition.flags:

        # (description, letter)
        description = definition.flags[name][0]
        letter = definition.flags[name][1]
        default = definition.flags[name][2]  # True or False

        print(indent + "# " + description, file=configfile)
        print(indent + name + " [flag]: " + str(default), file=configfile)

    # Sections
    for section_name in definition.sections:

        section_definition = definition.sections[section_name]
        section_description = definition.section_descriptions[section_name]

        print(indent + "# " + section_description, file=configfile)
        print(indent + section_name + "[section]:", file=configfile)
        print(indent + "{", file=configfile)

        # Write the section definition
        write_definition(section_definition, configfile, indent + "    ")

        print(indent + "}", file=configfile)

# -----------------------------------------------------------------

def add_settings_interactive(config, definition, prompt_optional=True):

    """
    This function ...
    :return:
    """

    # Fixed
    for name in definition.fixed:

        description = definition.fixed[name][0]
        value = definition.fixed[name][1]

        # Give name and description
        log.success(name + ": " + description + "")

        # Inform the user
        log.info("Using fixed value for " + str(value))

        # Set the value
        config[name] = value

    # Required
    for name in definition.required:

        real_type = definition.required[name][0]
        description = definition.required[name][1]
        choices = definition.required[name][2]

        # Give name and description
        log.success(name + ": " + description + ")")

        if choices is not None:

            log.info("Choose one of the options")

            for index, label in enumerate(choices):
                log.info(" - [" + str(index) + "] " + label)
            log.info("")

            # Get the number of the choice
            answer = raw_input("   : ")
            index = int(answer)
            value = choices[index]

        else:

            log.info("Provide a value")

            answer = raw_input("   : ")
            value = real_type(answer)

        # Set the value
        config[name] = value

    # Positional optional
    for name in definition.pos_optional:

        real_type = definition.pos_optional[name][0]
        description = definition.pos_optional[name][1]
        default = definition.pos_optional[name][2]
        choices = definition.pos_optional[name][3]

        # Give name and description
        log.success(name + ": " + description + ")")

        #
        log.info("Press ENTER to use the default value (" + str(default) + ")")

        if choices is not None:

            log.info("or choose one of the options")

            for index, label in enumerate(choices):
                log.info(" - [" + str(index) + "] " + label)
            log.info("")

            # Get the number of the choice
            answer = raw_input("   : ")

            if answer == "": value = default
            else:
                index = int(answer)
                value = choices[index]

        else:

            log.info("or provide another value")

            answer = raw_input("   : ")
            if answer == "": value = default
            else: value = real_type(answer)

        # Set the value
        config[name] = value

    # Optional
    for name in definition.optional:

        # (real_type, description, default, letter)
        real_type = definition.optional[name][0]
        description = definition.optional[name][1]
        default = definition.optional[name][2]
        choices = definition.optional[name][3]
        letter = definition.optional[name][4]

        # Give name and description
        log.success(name + ": " + description + ")")

        #
        log.info("Press ENTER to use the default value (" + str(default) + ")")

        if choices is not None:

            log.info("or choose one of the options")

            for index, label in enumerate(choices):
                log.info(" - [" + str(index) + "] " + label)
            log.info("")

            # Get the number of the choice
            answer = raw_input("   : ")

            if answer == "": value = default
            else:
                index = int(answer)
                value = choices[index]

        else:

            log.info("or provide another value")

            answer = raw_input("   : ")
            if answer == "": value = default
            else: value = real_type(answer)

        # Set the value
        config[name] = value

    # Flag
    for name in definition.flags:

        # (description, letter)
        description = definition.flags[name][0]
        letter = definition.flags[name][1]
        default = definition.flags[name][2]  # True or False

        # Give name and description
        log.success(name + ": " + description)

        # Ask the question
        log.info("Do you want '" + name + "' to be enabled or not (y or n) or press ENTER for the default (" + str(default) + ")")

        answer = raw_input("   : ")

        if answer == "": value = default
        else: value = parsing.boolean(answer)

        # Set the value
        config[name] = value

    # Add the configuration settings of the various sections
    for name in definition.sections:

        # Create a map for the settings
        config[name] = Map()

        # Recursively add the settings
        section_definition = definition.sections[name]
        section_description = definition.section_descriptions[name]

        # Give name and description
        log.success(name + ": " + section_description + " (section)")

        # Add the settings
        add_settings_interactive(config[name], section_definition, prompt_optional=prompt_optional)

# -----------------------------------------------------------------
