#!/usr/bin/env python
# -*- coding: utf8 -*-
# *****************************************************************
# **       PTS -- Python Toolkit for working with SKIRT          **
# **       © Astronomical Observatory, Ghent University          **
# *****************************************************************

## \package pts.core.basics.table Contains the SmartTable class.

# -----------------------------------------------------------------

# Ensure Python 3 compatibility
from __future__ import absolute_import, division, print_function

# Import standard modules
import numpy as np
import StringIO
import warnings
from collections import OrderedDict, defaultdict

# Import astronomical modules
from astropy.table import Table, MaskedColumn

# Import the relevant PTS classes and modules
from ..units.unit import PhotometricUnit
from ..units.parsing import parse_unit as u
from ..tools import filesystem as fs
from ..tools import types
from ..tools import sequences
from .containers import DefaultOrderedDict

# -----------------------------------------------------------------

def has_same_values_for_column(tables, column_name, reference_column_name, reference_values):

    """
    This function ...
    :param tables:
    :param column_name:
    :param reference_column_name:
    :param reference_values:
    :return:
    """

    from ..tools.tables import find_index

    for value in reference_values:

        table_column_values = []

        for table in tables:

            index = find_index(table, value, column_name=reference_column_name)
            if index is None: continue
            table_column_values.append(table[column_name][index])

        #print(table_column_values)

        if not sequences.all_equal(table_column_values): return False

    return True

# -----------------------------------------------------------------

def merge_tables(*tables, **kwargs):

    """
    This function ...
    :param tables:
    :param kwargs:
    :return:
    """

    from ..tools.tables import find_index

    # Get flags
    differences = kwargs.pop("differences", False)
    rel_differences = kwargs.pop("rel_differences", False)
    percentual = kwargs.pop("percentual", False)

    # Columns to use
    columns = kwargs.pop("columns", None)
    not_columns = kwargs.pop("not_columns", None)

    # Get table labels
    labels = kwargs.pop("labels", None)
    if labels is not None and len(labels) != len(tables): raise ValueError("Number of labels must be equal to number of tables")

    # Only shared columns
    only_shared = kwargs.pop("only_shared", False)

    # Determine column name
    reference_column_name = kwargs.pop("column_name", None)
    if reference_column_name is None:

        first_column_names = [table.colnames[0] for table in tables]
        if not sequences.all_equal(first_column_names): raise ValueError("Tables have different first columns")
        reference_column_name = first_column_names[0]

    reference_column_dtypes = []
    reference_column_units = []
    for table in tables:
        reference_column_dtypes.append(table.get_column_dtype(reference_column_name))
        reference_column_units.append(table.get_column_unit(reference_column_name))
    # Check
    if not sequences.all_equal(reference_column_dtypes): raise ValueError("Different reference column dtypes")
    if not sequences.all_equal(reference_column_units): raise ValueError("Different reference column units")
    reference_column_dtype = reference_column_dtypes[0]
    reference_column_unit = reference_column_units[0]

    all_column_types = DefaultOrderedDict(list)
    all_column_units = defaultdict(list)
    all_column_tableids = defaultdict(list)

    for table_index, table in enumerate(tables):
        #for colname in table.colu
        for name, dtype, unit, description in table.column_info:
            if name == reference_column_name: continue
            all_column_types[name].append(dtype)
            all_column_units[name].append(unit)
            all_column_tableids[name].append(table_index)

    all_values = []
    for table in tables: all_values.extend(table[reference_column_name])
    # print(all_values)
    reference_values = sequences.unique_values(all_values, ignore_none=True)

    # Create a table
    merged = SmartTable()

    unique_column_names = dict()
    equal_column_names = []
    original_column_names = dict()
    new_column_names = dict()

    # Add the columns
    merged.add_column_info(reference_column_name, reference_column_dtype, reference_column_unit, None)
    for column_name in all_column_types:

        # Use column?
        if columns is not None and column_name not in columns: continue
        if not_columns is not None and column_name in not_columns: continue

        # Get types and units
        dtypes = all_column_types[column_name]
        units = all_column_units[column_name]
        tableids = all_column_tableids[column_name]

        if len(dtypes) == 1:

            if only_shared: continue
            assert len(units) == 1
            assert len(tableids) == 1
            merged.add_column_info(column_name, dtypes[0], units[0], None)
            unique_column_names[column_name] = tableids[0]

        else:

            # Check if the columns are equal
            if has_same_values_for_column(tables, column_name, reference_column_name, reference_values):

                dtype = tables[tableids[0]].get_column_dtype(column_name)
                unit = tables[tableids[0]].get_column_unit(column_name)
                merged.add_column_info(column_name, dtype, unit, None)
                equal_column_names.append(column_name)

            else:

                for dtype, unit, tableid in zip(dtypes, units, tableids):
                    if labels is not None: new_column_name = column_name + " " + labels[tableid]
                    else: new_column_name = column_name + " " + str(tableid)
                    merged.add_column_info(new_column_name, dtype, unit, None)
                    original_column_names[new_column_name] = (column_name, tableid)

                # Add differences?
                if differences:
                    #print(tableids)
                    if len(tableids) > 2: raise ValueError("Cannot add differences for more than 2 tables")
                    if not sequences.all_equal(dtypes): raise ValueError("Not the same types")
                    if not sequences.all_equal(units): raise ValueError("Not the same units")
                    dtype = dtypes[0]
                    unit = units[0]
                    difference_column_name = column_name + " difference"
                    merged.add_column_info(difference_column_name, dtype, unit, "difference")
                    new_column_names[difference_column_name] = tableids

                # Add relative differences?
                if rel_differences:
                    #print(tableids)
                    if len(tableids) > 2: raise ValueError("Cannot add relative differences for more than 2 tables")
                    if not sequences.all_equal(dtypes): raise ValueError("Not the same types")
                    if not sequences.all_equal(units): raise ValueError("Not the same units")
                    dtype = dtypes[0]
                    unit = units[0]
                    if percentual: rel_difference_column_name = column_name + " percentual difference"
                    else: rel_difference_column_name = column_name + " relative difference"
                    merged.add_column_info(rel_difference_column_name, dtype, unit, "relative difference")
                    new_column_names[rel_difference_column_name] = tableids

    # All columns are added
    merged.setup()
    column_names = merged.column_names

    # Loop over all reference values
    for value in reference_values:

        # Find index of this value for each table
        indices = []
        for table in tables:
            index = find_index(table, value, column_name=reference_column_name)
            indices.append(index)

        #print(value, indices)

        values = [value]

        # Loop over the column names
        for column_name in column_names:
            if column_name == reference_column_name: continue

            #tableids = all_column_tableids[column_name]

            if column_name in equal_column_names:
                #print(column_name, indices[0])
                #value = tables[0][column_name][indices[0]]
                values_tables = [tables[tableid][column_name][indices[tableid]] for tableid in range(len(tables)) if column_name in tables[tableid].colnames and indices[tableid] is not None]
                #print(column_name, values_tables)
                value = sequences.get_first_not_none_value(values_tables)
                #print(value)

            elif column_name in original_column_names:

                original_column_name, tableid = original_column_names[column_name]
                if indices[tableid] is not None:
                    #print(indices[tableid])
                    value = tables[tableid][original_column_name][indices[tableid]]
                else: value = None

            elif column_name in unique_column_names:

                tableid = unique_column_names[column_name]
                if indices[tableid] is not None:
                    #print(indices[tableid])
                    value = tables[tableid][column_name][indices[tableid]]
                else: value = None

            elif column_name in new_column_names:

                tableids = new_column_names[column_name]
                id_a = tableids[0]
                id_b = tableids[1]
                index_a = indices[id_a]
                index_b = indices[id_b]
                #print(index_a, index_b)

                if index_a is None or index_b is None: value = None
                else:

                    if column_name.endswith("relative difference"):

                        original_column_name = column_name.split(" relative difference")[0]
                        value_a = tables[id_a][original_column_name][index_a]
                        value_b = tables[id_b][original_column_name][index_b]
                        value = abs(value_a - value_b) / value_a

                    elif column_name.endswith("percentual difference"):

                        original_column_name = column_name.split(" percentual difference")[0]
                        value_a = tables[id_a][original_column_name][index_a]
                        value_b = tables[id_b][original_column_name][index_b]
                        value = abs(value_a - value_b) / value_a * 100.

                    elif column_name.endswith("difference"):

                        original_column_name = column_name.split(" difference")[0]
                        value_a = tables[id_a][original_column_name][index_a]
                        value_b = tables[id_b][original_column_name][index_b]
                        value = abs(value_a - value_b)

                    else: raise ValueError("Column name not recognized")

            else: raise RuntimeError("Something went wrong: " + column_name)

            #print(value)

            # Add the value
            values.append(value)

        # Add row
        merged.add_row(values)

    # Return the table
    return merged

# -----------------------------------------------------------------

class SmartTable(Table):

    """
    This class ...
    """

    # default extension
    default_extension = "dat"

    # -----------------------------------------------------------------

    def __init__(self, *args, **kwargs):

        """
        The constructor ...
        :param args:
        :param kwargs:
        """

        # Always used masked tables
        kwargs["masked"] = True

        # Call the constructor of the base class
        super(SmartTable, self).__init__(*args, **kwargs)

        # Column info
        self.column_info = []

        # Path
        self.path = None

        # Initialize 'density' meta object
        if "density" not in self.meta: self.meta["density"] = []
        if "brightness" not in self.meta: self.meta["brightness"] = []

        # The column descriptions
        self._descriptions = dict()

    # -----------------------------------------------------------------

    @classmethod
    def from_dictionary(cls, dictionary, key_label="Property", value_label="Value", tostr_kwargs=None,
                        key_description="property name", value_description="property value"):

        """
        This function ...
        :param dictionary:
        :param key_label:
        :param value_label:
        :param tostr_kwargs:
        :param key_description:
        :param value_description:
        :return:
        """

        # Import tostr function
        from ..tools.stringify import tostr

        if tostr_kwargs is None: tostr_kwargs = dict()

        # Create the table
        table = cls()

        # Add the column info
        table.add_column_info(key_label, str, None, key_description)
        table.add_column_info(value_label, str, None, value_description)
        table.setup()

        for label in dictionary:

            value = dictionary[label]
            value_string = tostr(value, **tostr_kwargs)

            values = [label, value_string]
            table.add_row(values)

        # Return the table
        return table

    # -----------------------------------------------------------------

    @classmethod
    def from_dictionaries(cls, *dictionaries, **kwargs):

        """
        This function ...
        :param dictionaries:
        :param kwargs:
        :return:
        """

        from ..tools.stringify import stringify

        # Get list of lists of property names
        property_names = [dictionary.keys() for dictionary in dictionaries]

        # Determine the column names, types and descriptions
        column_names = sequences.union(*property_names)

        # Sort column names?
        first = kwargs.pop("first", None)
        last = kwargs.pop("last", None)
        if first is not None or last is not None: column_names = sequences.sort_with_first_last(column_names, first=first, last=last)

        # Ignore all None?
        ignore_none = kwargs.pop("ignore_none", False)
        remove_columns = []

        # Get the column types, units and descriptions
        prop_types = dict()
        prop_units = dict()
        prop_descriptions = dict()
        for name in column_names:

            # Get the types, units and descriptions
            #types = [composite.type_for_property(name) for composite in composites]
            #units = [composite.unit_for_property(name) for composite in composites]
            #descriptions = [composite.description_for_property(name) for composite in composites]

            types = []
            units = []
            descriptions = []

            for dictionary in dictionaries:

                # Get value
                if name in dictionary:

                    value = dictionary[name]

                    # Check whether there is a unit
                    if hasattr(value, "unit"): unit = value.unit
                    else: unit = None

                    # Get the type
                    dtype, string = stringify(value)

                # Not in this dictionary
                else: unit = dtype = None

                # Add the type and
                types.append(dtype)
                units.append(unit)

            # Determine column type, unit and description
            if sequences.all_equal_to(types, 'None') or sequences.all_none(types):
                if ignore_none: remove_columns.append(name)
                column_type = 'None'
            else: column_type = sequences.get_all_equal_value(types, ignore_none=True, ignore='None')

            # Determine column unit
            column_unit = sequences.get_first_not_none_value(units)

            # Determine column description
            #column_description = sequences.get_first_not_none_value(descriptions)
            column_description = None

            # Set type, unit and description
            prop_types[name] = column_type
            prop_units[name] = column_unit
            prop_descriptions[name] = column_description

        # Remove columns
        if len(remove_columns) > 0: column_names = sequences.removed(column_names, remove_columns)

        # Create and return
        return cls.from_properties(column_names, prop_types, prop_units, prop_descriptions, dictionaries, **kwargs)

    # -----------------------------------------------------------------

    @classmethod
    def from_composite(cls, composite, key_label="Property", value_label="Value", tostr_kwargs=None,
                       key_description="property name", value_description="property value"):

        """
        This function ...
        :param composite:
        :param key_label:
        :param value_label:
        :param tostr_kwargs:
        :param key_description:
        :param value_description:
        :return:
        """

        # Import tostr function
        from ..tools.stringify import tostr

        if tostr_kwargs is None: tostr_kwargs = dict()

        # Create the table
        table = cls()

        #column_types = [str, str]
        #column_units = [None, None]
        #keys_values = composite.as_tuples()
        #column_names = [key_label, value_label]

        # Add the column info
        table.add_column_info(key_label, str, None, key_description)
        table.add_column_info(value_label, str, None, value_description)
        table.setup()

        #print(table.column_info)

        for key in composite:

            value = composite[key]
            value_string = tostr(value, **tostr_kwargs)

            values = [key, value_string]
            table.add_row(values)

        # Return the table
        return table

    # -----------------------------------------------------------------

    @classmethod
    def from_composites(cls, *composites, **kwargs):

        """
        This function ...
        :param composites:
        :param kwargs:
        :return:
        """

        # Check number
        if len(composites) == 0: raise ValueError("No input is provided")

        # Get list of lists of property names
        property_names = [composite.property_names for composite in composites]

        # Determine the column names, types and descriptions
        column_names = sequences.union(*property_names)

        # Sort column names?
        first = kwargs.pop("first", None)
        last = kwargs.pop("last", None)
        if first is not None or last is not None: column_names = sequences.sort_with_first_last(column_names, first=first, last=last)

        # Get the column types, units and descriptions
        prop_types = dict()
        prop_units = dict()
        prop_descriptions = dict()
        for name in column_names:

            # Get the types, units and descriptions
            types = [composite.type_for_property(name) for composite in composites]
            units = [composite.unit_for_property(name) for composite in composites]
            descriptions = [composite.description_for_property(name) for composite in composites]

            # Determine column type, unit and description
            if sequences.all_equal_to(types, 'None') or sequences.all_none(types): column_type = 'None'
            else: column_type = sequences.get_all_equal_value(types, ignore_none=True, ignore='None')

            # Determine column unit
            column_unit = sequences.get_first_not_none_value(units)

            # Determine column description
            column_description = sequences.get_first_not_none_value(descriptions)

            # Set type, unit and description
            prop_types[name] = column_type
            prop_units[name] = column_unit
            prop_descriptions[name] = column_description

        # Create and return
        kwargs["attr"] = True
        return cls.from_properties(column_names, prop_types, prop_units, prop_descriptions, composites, **kwargs)

    # -----------------------------------------------------------------

    @classmethod
    def from_properties(cls, property_names, property_types, property_units, property_descriptions, objects, **kwargs):

        """
        This function ...
        :param property_names:
        :param objects:
        :param property_types:
        :param property_units:
        :param property_descriptions:
        :param kwargs:
        :return:
        """

        # Import tostr function
        from ..tools.stringify import tostr

        # Get names
        labels = kwargs.pop("labels", None)
        label = kwargs.pop("label", "-")

        # Get tostr kwargs
        tostr_kwargs = kwargs.pop("tostr_kwargs", {})

        # Get flag
        attr = kwargs.pop("attributes", False)

        # Add the label column name
        if labels is not None: column_names = [label] + property_names #sequences.prepend(column_names, label)
        else:
            column_names = property_names
            labels = [None] * len(objects) # labels was None

        # Create the table
        table = cls()

        # Create lists to contain the column types and units
        column_types = []
        column_units = []

        # COLUMNS FOR WHICH THE VALUE HAS TO BE CONVERTED TO STRING
        to_string = []

        # Make the columns
        for name in column_names:

            if name == label:

                real_type = str
                column_unit = None
                column_description = label

            else:

                # Get type, unit and description
                column_type = property_types[name]
                column_unit = property_units[name]
                column_description = property_descriptions[name]

                # Add column type and unit to lists
                column_types.append(column_type)
                column_units.append(column_unit)

                if column_type.endswith("real"): real_type = float
                elif column_type.endswith("integer"): real_type = int
                elif column_type.endswith("string"): real_type = str
                elif column_type.endswith("boolean"): real_type = bool
                elif column_type.endswith("quantity"): real_type = float

                # UNIT HAVE TO BE CONVERTED TO STRINGS
                elif column_type.endswith("unit"):
                    to_string.append(name)
                    real_type = str

                # FILTERS HAVE TO BE CONVERTED TO STRINGS
                elif column_type.endswith("filter"):
                    to_string.append(name)
                    real_type = str

                # SPECIAL CASE: WAS NONE FOR EACH COMPOSITE
                elif column_type == "None": real_type = str

                # LISTS OF THINGS -> STRINGS
                elif column_type.endswith("_list"):
                    to_string.append(name)
                    real_type = str

                # NOT RECOGNIZED
                else: raise ValueError("Column type not recognized: " + str(column_type) + " (" + str(type(column_type)) + ")")

            # Add the column info
            table.add_column_info(name, real_type, column_unit, column_description)

        # Set None string
        if "none_string" not in tostr_kwargs: tostr_kwargs["none_string"] = "--"

        # Add the rows
        for composite_label, obj in zip(labels, objects):

            values = []

            # Fill the row
            #for name, dtype, unit in zip(column_names, column_types, column_units):
            for name in column_names:

                if name == label: value = composite_label
                else:

                    # Properties are attributes of the objects
                    if attr:

                        # Get the value
                        if hasattr(obj, name):
                            value = getattr(obj, name)
                            if name in to_string: value = tostr(value, **tostr_kwargs)
                        else: value = None

                    # Properties are items of the objects
                    else:

                        if name in obj:
                            value = obj[name]
                            if name in to_string: value = tostr(value, **tostr_kwargs)
                        else: value = None

                # Add the value
                values.append(value)

            # Add the row: unit conversion is done here
            table.add_row(values)

        # Return the table
        return table

    # -----------------------------------------------------------------

    def remove_other_columns(self, names):

        """
        This function ...
        :param names:
        :return:
        """

        remove_names = sequences.get_other(self.column_names, names)
        self.remove_columns(remove_names)

    # -----------------------------------------------------------------

    def remove_all_columns(self):

        """
        This function ...
        :return:
        """

        self.remove_columns(self.column_names)

    # -----------------------------------------------------------------

    def remove_all_rows(self):

        """
        This function ...
        :return:
        """

        self.remove_rows(range(self.nrows))

    # -----------------------------------------------------------------

    def get_column_index(self, column_name):

        """
        This function ...
        :param column_name:
        :return:
        """

        for index in range(len(self.column_info)):
            if self.column_info[index][0] == column_name: return index
        return None

    # -----------------------------------------------------------------

    def get_column_dtype(self, column_name):

        """
        Thisf unction ...
        :param column_name:
        :return:
        """

        index = self.get_column_index(column_name)
        if index is None: raise ValueError("No column '" + column_name + "'")
        return self.column_info[index][1]

    # -----------------------------------------------------------------

    def get_column_array_dtype(self, column_name):

        """
        This function ...
        :param column_name:
        :return:
        """

        return self[column_name].dtype

    # -----------------------------------------------------------------

    def get_column_array_dtype_string(self, column_name):

        """
        This function ...
        :param column_name:
        :return:
        """

        return str(self.get_column_array_dtype(column_name))

    # -----------------------------------------------------------------

    def is_string_column(self, column_name):

        """
        This function ...
        :param column_name:
        :return:
        """

        return self.get_column_array_dtype_string(column_name).startswith("|S")

    # -----------------------------------------------------------------

    def get_string_column_size(self, column_name):

        """
        This function ...
        :param column_name:
        :return:
        """

        return int(self.get_column_array_dtype_string(column_name).split("S")[1])

    # -----------------------------------------------------------------

    def get_column_unit(self, column_name):

        """
        This function ...
        :param column_name:
        :return:
        """

        index = self.get_column_index(column_name)
        if index is None: raise ValueError("No column '" + column_name + "'")
        return self.column_info[index][2]

    # -----------------------------------------------------------------

    def get_column_description(self, column_name):

        """
        This function ...
        :param column_name:
        :return:
        """

        index = self.get_column_index(column_name)
        if index is None: raise ValueError("No column '" + column_name + "'")
        return self.column_info[index][3]

    # -----------------------------------------------------------------

    def add_column_info(self, name, dtype, unit, description):

        """
        This function ...
        :param name:
        :param dtype:
        :param unit:
        :param description:
        :return:
        """

        if types.is_string_type(unit): unit = u(unit)
        self.column_info.append((name, dtype, unit, description))

    # -----------------------------------------------------------------

    def has_column_unit(self, column_name):

        """
        This function ...
        :param column_name:
        :return:
        """

        return self[column_name].unit is not None

    # -----------------------------------------------------------------

    def column_unit(self, column_name):

        """
        This function ...
        :param column_name:
        :return:
        """

        if not self.has_column_unit(column_name): return None

        # Construct unit
        if column_name in self.meta["density"]: density = True
        else: density = False
        if column_name in self.meta["brightness"]: brightness = True
        else: brightness = False
        return u(self[column_name].unit, density=density, brightness=brightness)

    # -----------------------------------------------------------------

    def column_unit_string(self, column_name):

        """
        This function ...
        :param column_name:
        :return:
        """

        unit = self.column_unit(column_name)
        if unit is None: return ""
        else: return str(unit)

    # -----------------------------------------------------------------

    def setup(self):

        """
        This function ...
        :return:
        """

        #print("Performing setup of the table ...")

        # Setup has already been called
        if len(self.colnames) != 0: return

        # Create the table names and types lists
        for entry in self.column_info:

            name = entry[0]
            dtype = entry[1]
            unit = entry[2]
            description = entry[3]

            data = []

            # Add column
            col = MaskedColumn(data=data, name=name, dtype=dtype, unit=unit)
            self.add_column(col)

            # Set the description
            self._descriptions[name] = description

            # Set whether this column is a spectral density
            if isinstance(unit, PhotometricUnit) and unit.density:
                if "density" not in self.meta: self.meta["density"] = []
                self.meta["density"].append(name)

            # Set whether this column is a surface brightness
            if isinstance(unit, PhotometricUnit) and unit.brightness:
                if "brightness" not in self.meta: self.meta["brightness"] = []
                self.meta["brightness"].append(name)

    # -----------------------------------------------------------------

    def __getitem__(self, item):

        """
        This function ...
        :param item: 
        :return: 
        """

        # Run the setup if not yet performed
        if len(self.colnames) == 0: self.setup()

        # Call the implementation of the base class
        return super(SmartTable, self).__getitem__(item)

    # -----------------------------------------------------------------

    @classmethod
    def from_remote_file(cls, path, remote):

        """
        This function ...
        :param path:
        :param remote:
        :return:
        """

        fill_values = [('--', '0')]

        # Get the contents
        contents = remote.get_text(path)

        # Read the table from file
        table = super(SmartTable, cls).read(contents, fill_values=fill_values, format="ascii.ecsv")

        # Set masks
        set_table_masks(table)

        ## Don't set the (remote) path

        # Initialize
        initialize_table(table)

        # Return the table
        return table

    # -----------------------------------------------------------------

    @classmethod
    def from_file(cls, path, format=None):

        """
        This function ...
        :param path:
        :param format:
        :return:
        """

        # Guess the format
        if format is None:
            first_line = fs.get_first_line(path)
            if "ECSV" in first_line: format = "ecsv"
            elif "PTS data format" in first_line: format = "pts"

        #fill_values = [('--', '0')]
        fill_values = [('--', '0')]

        # Check the path
        if not fs.is_file(path): raise IOError("The file '" + path + "' does not exist")

        # PTS format
        if format == "pts":

            # Read the lines
            lines = fs.read_lines(path)

            #header.append("PTS data format")
            # for name in masks: header.append(name + " mask: " + tostr(masks[name])) # WILL BE READ FROM THE QUOTE CHARACTERS in the data lines

            # Set density and brightness lists
            #if "density" in self.meta and len(self.meta["density"]) > 0: header.append("density: " + tostr(self.meta["density"]))
            #if "brightness" in self.meta and len(self.meta["brightness"]) > 0: header.append("brightness: " + tostr(self.meta["brightness"]))

            # Set unit string line for the header
            #unit_string = ""
            #for name in self.column_names:
            #    unit = self.column_unit(name)
            #    if unit is None: unit_string += ' ""'
            #    else: unit_string += " " + tostr(unit)
            #header.append(unit_string.strip())

            # Initialize the data lines and header lines
            data_lines = []
            header = []

            # Loop over the lines of the file
            for line in lines:

                # Header line
                if line.startswith("#"): header.append(line[2:])
                else:
                    #line = line.replace('""', "--")
                    data_lines.append(line)

            # Put last header line (colum names) as first data line (and remove it from the header)
            sequences.prepend(data_lines, "# " + header[-1])
            header = header[:-1]

            #print("DATA")
            #for line in data_lines: print(line)
            #print("")
            #print("HEADER")
            #for line in header: print(line)
            #print("")

            #filehandle = StringIO.StringIO()
            #for line in data_lines: filehandle.write(line + "\n")

            # Call the constructor from Astropy, to read in plain ascii format
            table = super(SmartTable, cls).read(data_lines, format="ascii.commented_header")

            # FIX BOOLEAN COLUMNS
            to_boolean = []
            for column_name in table.colnames:
                values = list(table[column_name])
                #value_strings = [str(value) for value in values] # actually not necessary
                #print(column_name, values)
                if not sequences.all_strings(values, ignore_instance=np.ma.core.MaskedConstant): continue
                if sequences.all_in(values, ["True", "False"]): to_boolean.append(column_name)

            # Search for density and brightness, set meta info
            for line in header:
                if line.startswith("density:"):

                    density_string = line.split("density: ")[1]
                    string = "[" + ",".join('"' + s + '"' for s in density_string.split(",")) + "]"
                    table.meta["density"] = eval(string)

                elif line.startswith("brightness:"):

                    brightness_string = line.split("brightness: ")[1]
                    string = "[" + ",".join('"' + s + '"' for s in brightness_string.split(",")) + "]"
                    table.meta["brightness"] = eval(string)

            # Set units
            unit_string = header[-1]
            unit_strings = unit_string.split()
            assert len(unit_strings) == len(table.colnames)
            #print(len(unit_strings), len(table.colnames))
            #print(unit_strings)
            for unit_string, colname in zip(unit_strings, table.colnames):
                if unit_string == '""': continue
                table[colname].unit = unit_string

            # DO THIS AT THE END BECAUSE OTHERWISE UNITS ASSIGNED TO THE WRONG COLUMNS
            # Loop over the columns to convert to booleans
            for column_name in to_boolean:
                booleans = []
                for index in range(len(table)):
                    if table[column_name].mask[index]:
                        boolean = None  # masked?
                    else:
                        value = table[column_name][index]
                        boolean = eval(value)
                    booleans.append(boolean)
                # remove original column
                table.remove_column(column_name)
                table[column_name] = booleans

        # ECSV format (with masks and units in the meta info)
        elif format == "ecsv":

            # Read
            table = super(SmartTable, cls).read(path, fill_values=fill_values, format="ascii.ecsv")

            # Set masks
            set_table_masks(table)

        # Write the table in the desired format (by Astropy)
        elif format == "csv": table = super(SmartTable, cls).read(path, fill_values=fill_values, format="ascii.csv")

        # HTML
        elif format == "html": table = super(SmartTable, cls).read(path, fill_values=fill_values, format="ascii.html")

        # Latex
        elif format == "latex": table = super(SmartTable, cls).read(path, fill_values=fill_values, format="ascii.latex")

        # All other
        else: table = super(SmartTable, cls).read(path, fill_values=fill_values, format=format)

        # Set the path
        table.path = path

        # Initialize
        initialize_table(table)

        # Return the table
        return table

    # -----------------------------------------------------------------

    def _resize_string_columns(self, values):

        """
        This function ...
        :param values:
        :return:
        """

        # Initialize dictionary for the new sizes of the columns
        #new_sizes = dict()

        # Loop over the columns
        for index, colname in enumerate(self.column_names):

            # Skip non-string columns
            if not self.is_string_column(colname): continue

            # Resize if necessary
            self.resize_string_column_for_string(colname, values[index])

        # Resize columns
        #for colname in new_sizes: self.resize_string_column(colname, new_sizes[colname])

    # -----------------------------------------------------------------

    def resize_string_column_for_string(self, colname, string):

        """
        This function ...
        :param colname:
        :param string:
        :return:
        """

        # Get current column string length
        current_string_length = self.get_string_column_size(colname)

        # Get new string length
        if string is None: new_string_length = 0
        else: new_string_length = len(string)

        # Doesn't need resize?
        if new_string_length <= current_string_length: return

        # Resize
        self.resize_string_column(colname, new_string_length)

    # -----------------------------------------------------------------

    def resize_string_column(self, colname, size):

        """
        This function ...
        :param colname:
        :param size:
        :return:
        """

        # Create new version of the column
        resized = self[colname].astype("S" + str(size))

        # Replace the column
        self.replace_column(colname, resized)

    # -----------------------------------------------------------------

    def _resize_string_column(self, colname, value):

        """
        This function ...
        :param colname:
        :param value:
        :return:
        """

        if value is None: return

        dtype_str = str(self[colname].dtype)

        if not dtype_str.startswith("|S"): raise ValueError("Column " + colname + " is not a column of strings")

        current_string_length = int(dtype_str.split("S")[1])

        new_string_length = len(value)

        if new_string_length > current_string_length:

            new_size = new_string_length

            # Replace the column by a resized one
            current_resized = self[colname].astype("S" + str(new_size))
            self.replace_column(colname, current_resized)

    # -----------------------------------------------------------------

    def _strip_units(self, values, conversion_info=None):

        """
        This function ...
        :param values:
        :param conversion_info:
        :return:
        """

        scalar_values = []

        #print(values)
        #print(self.column_info)

        for i, value in enumerate(values):

            # Get the column name
            colname = self.column_info[i][0]

            # If this value has a unit, we have to make sure it is converted into the proper column unit
            if hasattr(value, "unit"):

                #print(self.column_info)

                #print(value, colname)

                column_unit = self.column_unit(colname)
                #print(colname, self.column_type(colname), column_unit)
                #column_unit = self.column_info[i][2]
                assert column_unit is not None

                # Quantity with photometric unit
                if isinstance(value.unit, PhotometricUnit):

                    # Get the conversion info for this column
                    if conversion_info is not None and colname in conversion_info: conv_info = conversion_info[colname]
                    else: conv_info = dict()

                    # Determine the conversion factor
                    factor = value.unit.conversion_factor(column_unit, **conv_info)

                    # Multiply with the conversion factor
                    scalar_value = value.value * factor

                # Quantity with regular Astropy Unit
                else: scalar_value = value.to(column_unit).value

                # Add the value
                scalar_values.append(scalar_value)

            # A scalar value (or string, int, ...)
            else: scalar_values.append(value)

        # Return the values without unit
        return scalar_values

    # -----------------------------------------------------------------

    def _convert_lists(self, values):

        """
        This function ...
        :param values:
        :return:
        """

        converted_values = []

        for i, value in enumerate(values):

            if isinstance(value, list):

                column_type = self.column_info[i][1]

                if len(value) == 0: converted_value = None
                elif column_type == str: converted_value = ",".join(map(str, value))
                else: raise ValueError("Cannot have a list element in the row at the column that is not of string type")

            else: converted_value = value

            converted_values.append(converted_value)

        # Return the converted values
        return converted_values

    # -----------------------------------------------------------------

    def get_quantity(self, colname, index):

        """
        This function ...
        :param colname:
        :param index:
        :return:
        """

        value = self[colname][index]

        if self[colname].mask[index]: return None
        elif self[colname].unit is not None:
            quantity = value * self[colname].unit
        else: quantity = value

        # Return the quantity
        return quantity

    # -----------------------------------------------------------------

    def get_value(self, colname, index, add_unit=True):

        """
        This function ...
        :param colname:
        :param index:
        :param add_unit:
        :return:
        """

        value = self[colname][index]

        if self[colname].mask[index]: value = None
        elif self.has_column_unit(colname) and add_unit: value = value * self.column_unit(colname)

        # Return the value
        return value

    # -----------------------------------------------------------------

    def set_value(self, colname, index, value, conversion_info=None, return_previous=False):

        """
        This function ...
        :param colname:
        :param index:
        :param value:
        :param return_previous:
        :param conversion_info:
        :return:
        """

        # Get the current value
        if return_previous: previous = self.get_value(colname, index)
        else: previous = None

        # Value is None?
        if value is None: self[colname].mask[index] = True

        # Column with unit
        elif self.has_column_unit(colname):

            # Set the value in the correct unit
            if conversion_info is None: conversion_info = dict()
            self[colname][index] = value.to(self.column_unit(colname), **conversion_info).value

        # Column without unit: check that value has no unit
        elif hasattr(value, "unit"): raise ValueError("Value has unit but unit of column is undefined")

        # String column
        elif self.is_string_column(colname):
            self.resize_string_column_for_string(colname, value)
            self[colname][index] = value

        # Other column type
        else: self[colname][index] = value

        # Return the previous value
        return previous

    # -----------------------------------------------------------------

    def is_masked_value(self, colname, index):

        """
        This function ...
        :param colname:
        :param index:
        :return:
        """

        return self[colname].mask[index]

    # -----------------------------------------------------------------

    def get_row(self, index, add_units=True, as_list=False):

        """
        This function ...
        :param index:
        :param add_units:
        :param as_list:
        :return:
        """

        row = OrderedDict()

        for name in self.colnames:

            # Get the value
            value = self.get_value(name, index, add_unit=add_units)

            # Add the value
            row[name] = value

        # Return the row
        if as_list: return row.values()
        else: return row

    # -----------------------------------------------------------------

    def add_row(self, values, conversion_info=None):

        """
        This function ...
        :param values:
        :param conversion_info:
        :return:
        """

        # Setup if necessary
        if len(self.colnames) == 0: self.setup()

        #print(len(self.colnames))
        #print(len(values))

        # CHECK TYPES BEFORE RESIZE STRING COLUMNS?

        # Resize string columns for the new values
        self._resize_string_columns(values)

        # Strip units
        values = self._strip_units(values, conversion_info=conversion_info)

        # Convert lists to string
        values = self._convert_lists(values)

        # Create mask
        mask = [value is None for value in values]

        # Set masked values to have a default value (None will not work for Astropy)
        new_values = []
        for i in range(len(values)):

            if values[i] is not None: new_values.append(values[i])
            else:
                colname = self.colnames[i]
                if self.is_string_type(colname): new_values.append("")
                elif self.is_real_type(colname): new_values.append(0.)
                elif self.is_integer_type(colname): new_values.append(0)
                elif self.is_boolean_type(colname): new_values.append(False)
                else: raise ValueError("Unknown column type for '" + colname + "'")

        # Add the row
        super(SmartTable, self).add_row(new_values, mask=mask)

    # -----------------------------------------------------------------

    def add_row_from_dict(self, dictionary, conversion_info=None):

        """
        This function ...
        :param dictionary:
        :param conversion_info:
        :return:
        """

        # Initialize list for the values
        values = []

        # Loop over the column names
        for column_name in self.column_names:

            if column_name not in dictionary: value = None
            else: value = dictionary[column_name]

            # Add the value
            values.append(value)

        #print(values)

        # Add row
        self.add_row(values, conversion_info=conversion_info)

    # -----------------------------------------------------------------

    def column_type(self, column_name):

        """
        This function ...
        :param column_name: 
        :return: 
        """

        coltype = self[column_name].dtype.name

        if coltype.startswith("string"): return "string"
        elif coltype.startswith("float"): return "real"
        elif coltype.startswith("int"): return "integer"
        elif coltype.startswith("bool"): return "boolean"
        else: raise ValueError("Unknown column type: " + coltype)

    # -----------------------------------------------------------------

    def is_string_type(self, column_name):

        """
        This function ...
        :param column_name: 
        :return: 
        """

        return self.column_type(column_name) == "string"

    # -----------------------------------------------------------------

    def is_real_type(self, column_name):

        """
        This function ...
        :param column_name: 
        :return: 
        """

        return self.column_type(column_name) == "real"

    # -----------------------------------------------------------------

    def is_integer_type(self, column_name):

        """
        This function ...
        :param column_name: 
        :return: 
        """

        return self.column_type(column_name) == "integer"

    # -----------------------------------------------------------------

    def is_boolean_type(self, column_name):

        """
        This function ...
        :param column_name: 
        :return: 
        """

        return self.column_type(column_name) == "boolean"

    # -----------------------------------------------------------------

    def all_equal(self, column_name):

        """
        This function ...
        :param column_name:
        :return:
        """

        if len(self[column_name]) == 0: return True

        # Doesn't work with strings I think ...
        #return (self[column_name] == self[column_name][0]).all() # all equal to the first element

        first = self[column_name][0]
        #print(first)
        for i in range(len(self[column_name])):
            print(self[column_name][i])
            if self[column_name][i] != first: return False
        return True

    # -----------------------------------------------------------------

    def save(self):

        """
        This function ...
        :return:
        """

        if self.path is None: raise RuntimeError("Path has not been set yet")

        # Save to the current path
        self.saveto(self.path)

    # -----------------------------------------------------------------

    def saveto(self, path, format="pts"):

        """
        This function ...
        :param path:
        :param format:
        :return:
        """

        # Import tostr function
        from ..tools.stringify import tostr

        # Setup if necessary
        if len(self.colnames) == 0: self.setup()

        # If the file already exists, remove
        if fs.is_file(path): fs.remove_file(path)

        # PTS format
        if format == "pts":

            # Create string buffer
            import StringIO
            output = StringIO.StringIO()

            # Write to buffer, get the lines
            self.write(output, format="ascii.commented_header")
            data_lines = output.getvalue().split("\n")

            # Get masks
            #masks = self.get_masks()

            # Create header
            header = []
            header.append("PTS data format")
            #for name in masks: header.append(name + " mask: " + tostr(masks[name])) # WILL BE READ FROM THE QUOTE CHARACTERS in the data lines

            # Set density and brightness lists
            if "density" in self.meta and len(self.meta["density"]) > 0: header.append("density: " + tostr(self.meta["density"]))
            if "brightness" in self.meta and len(self.meta["brightness"]) > 0: header.append("brightness: " + tostr(self.meta["brightness"]))

            # Set unit string line for the header
            unit_string = ""
            for name in self.column_names:
                unit = self.column_unit(name)
                if unit is None: unit_string += ' ""'
                else: unit_string += " " + tostr(unit)
            header.append(unit_string.strip())

            # Create lines
            lines = []
            for line in header: lines.append("# " + line)
            #lines.append("# " + data_lines[0]) # add line with the column names
            #for line in data_lines[1:]:
            for line in data_lines:
                if not line: continue # empty line at the end
                lines.append(line)

            # Write the lines
            fs.write_lines(path, lines)

        # ECSV format (with masks and units in the meta info)
        elif format == "ecsv":

            # Get masks
            masks = self.get_masks_int()

            # Set masks in meta
            for name in masks: self.meta[name + " mask"] = masks[name]

            # Replace masked values (not masked anymore)
            self.replace_masked_values()

            # Save
            self.write(path, format="ascii.ecsv")

            # Set the masks back (because they were set to False by replace_masked_values, necessary to avoid writing out
            # '""' (empty string) for each masked value, which is unreadable by Astropy afterwards)
            self.set_masks(masks)

        # Write the table in the desired format (by Astropy)
        elif format == "csv": self.write(path, format="ascii.csv")

        # HTML
        elif format == "html": self.write(path, format="ascii.html")

        # Latex
        elif format == "latex": self.write(path, format="ascii.latex")

        # All other
        else: self.write(path, format=format)

        # Set the path
        self.path = path

    # -----------------------------------------------------------------

    def saveto_csv(self, path):

        """
        This function ...
        :param path:
        :return:
        """

        # Check or add extension
        if fs.has_extension(path):
            if fs.get_extension(path) != "csv": warnings.warn("The extension is not 'csv'")
        else: path = path + ".csv"

        # Save
        self.saveto(path, format="csv")

    # -----------------------------------------------------------------

    def saveto_ecsv(self, path):

        """
        This function ...
        :param path:
        :return:
        """

        # Check or add extension
        if fs.has_extension(path):
            if fs.get_extension(path) != "ecsv": warnings.warn("The extension is not 'ecsv'")
        else: path = path + ".ecsv"

        # Save
        self.saveto(path, format="ecsv")

    # -----------------------------------------------------------------

    def saveto_html(self, path):

        """
        This function ...
        :param path:
        :return:
        """

        # Check or add extension
        if fs.has_extension(path):
            if fs.get_extension(path) != "html": warnings.warn("The extension if not 'html'")
        else: path = path + ".html"

        # Save
        self.saveto(path, format="html")

    # -----------------------------------------------------------------

    def saveto_latex(self, path):

        """
        This function ...
        :param path:
        :return:
        """

        # Check or add extension
        if fs.has_extension(path):
            if fs.get_extension(path) != "text": warnings.warn("The extension is not 'tex'")
        else: path = path + ".tex"

        # Save
        self.saveto(path, format="latex")

    # -----------------------------------------------------------------

    def saveto_votable(self, path):

        """
        This function ...
        :param path:
        :return:
        """

        # Check or add extension
        if fs.has_extension(path):
            if fs.get_extension(path) != "votable": warnings.warn("The extension is not 'xml'")
        else: path = path + ".xml"

        # Save
        self.saveto(path, format="votable")

    # -----------------------------------------------------------------

    def saveto_ascii(self, path):

        """
        This function ...
        :param path:
        :return:
        """

        # Check or add extension
        if fs.has_extension(path):
            if fs.get_extension(path) != "ascii": warnings.warn("The extension is not 'ascii'")
        else: path = path + ".ascii"

        # Save
        self.saveto(path, format="ascii")

    # -----------------------------------------------------------------

    def saveto_pts(self, path):

        """
        This function ...
        :param path:
        :return:
        """

        # Check or add extension
        if fs.has_extension(path):
            if fs.get_extension(path) != "dat": warnings.warn("The extension is not 'dat'")
        else: path = path + ".dat"

        # Save
        self.saveto(path, format="pts")

    # -----------------------------------------------------------------

    def get_masks(self):

        """
        This function ...
        :return: 
        """

        masks = dict()
        for name in self.colnames:
            masks[name] = [boolean for boolean in self[name].mask]
        return masks

    # -----------------------------------------------------------------

    def get_masks_int(self):

        """
        This function ...
        :return:
        """

        masks = dict()
        for name in self.colnames:
            masks[name] = [int(boolean) for boolean in self[name].mask]
        return masks

    # -----------------------------------------------------------------

    def set_masks(self, masks):

        """
        This function ...
        :param masks:
        :return: 
        """

        # Loop over the columns for which there is a mask in the 'masks' dictionary
        for colname in masks:

            # Loop over the rows, set mask elements
            for index in range(len(self)): self[colname].mask[index] = masks[colname][index]

    # -----------------------------------------------------------------

    def replace_masked_values(self):

        """
        This function ...
        :return: 
        """

        # Loop over the columns
        for colname in self.colnames:

            # Loop over the rows
            for index in range(len(self)):

                # If not masked, skip
                if not self[colname].mask[index]: continue

                # Set value
                if self.is_string_type(colname): value = ""
                elif self.is_real_type(colname): value = 0.
                elif self.is_integer_type(colname): value = 0
                elif self.is_boolean_type(colname): value = False
                else: raise ValueError("Unknown column type for '" + colname + "'")

                # Set value
                self[colname][index] = value

    # -----------------------------------------------------------------

    def set_masked_constants(self):

        """
        This function ...
        :return: 
        """

        # Loop over the columns
        for colname in self.colnames:

            # Loop over the rows
            for index in range(len(self)):

                # If not masked, skip
                if not self[colname].mask[index]: continue

                # Else, set masked value
                #if self.column_type(colname) == "string": self[colname][index] = "--"
                #elif self.column_type(colname) == "integer": self[colname][index] = 0
                #elif self.column_type(colname) == "real": self[colname][index] = 0
                #elif self.column_type(colname) == "boolean": self[colname][index] = False

                self[colname][index] = np.ma.masked
                self[colname].mask[index] = True

    # -----------------------------------------------------------------

    def to_html(self):

        """
        This function ...
        :return:
        """

        # Make string output
        output = StringIO.StringIO()

        # Write as HTML
        self.write(output, format='html')
        contents = output.getvalue()

        # Close object and discard memory buffer --
        # .getvalue() will now raise an exception.
        output.close()

        # Return the HTML string
        return contents

    # -----------------------------------------------------------------

    @property
    def column_names(self):

        """
        Thisn function ...
        :return:
        """

        return self.colnames

    # -----------------------------------------------------------------

    @property
    def units(self):

        """
        This function ...
        :return:
        """

        units = []
        for name in self.column_names: units.append(self.column_unit(name))
        return units

    # -----------------------------------------------------------------

    @property
    def unit_strings(self):

        """
        This function ...
        :return:
        """

        strings = []
        for name in self.column_names: strings.append(self.column_unit_string(name))
        return strings

    # -----------------------------------------------------------------

    @property
    def descriptions(self):

        """
        This function ...
        :return:
        """

        strings = []
        for name in self.column_names:
            if name in self._descriptions: description = self._descriptions[name]
            else: description = None
            strings.append(description)
        return strings

    # -----------------------------------------------------------------

    @property
    def ncolumns(self):

        """
        This function ...
        :return:
        """

        return len(self.column_names)

    # -----------------------------------------------------------------

    @property
    def nrows(self):

        """
        This function ...
        :return:
        """

        return len(self)

    # -----------------------------------------------------------------

    def as_tuples(self, add_units=True):

        """
        This function ...
        :param add_units:
        :return:
        """

        tuples = []
        for index in range(len(self)):
            values = self.get_row(index, add_units=add_units).values()
            tuples.append(tuple(values))
        return tuples

    # -----------------------------------------------------------------

    def as_lists(self, add_units=True):

        """
        This function ...
        :param add_units:
        :return:
        """

        lists = []
        for index in range(len(self)):
            values = self.get_row(index, add_units=add_units).values()
            lists.append(values)
        return lists

    # -----------------------------------------------------------------

    def print_latex(self):

        """
        This function ...
        :return: 
        """

        #self.show_in_browser()

        colnames_escaped = [name.replace("_", "\_") for name in self.colnames]

        header = " & ".join(colnames_escaped) + " \\\\"
        print(header)

        units = []
        has_units = False
        for name in self.colnames:
            unit = self.column_unit(name)
            if unit is None:
                units.append("")
            else:
                has_units = True
                units.append(str(unit))

        if has_units:
            units_string = " & ".join(units) + " \\\\"
            print(units_string)

        for index in range(len(self)):

            row = []
            for name in self.colnames: row.append(str(self[name][index]).replace("_", "\_"))
            row_string = " & ".join(row) + " \\\\"

            print(row_string)

# -----------------------------------------------------------------

def set_table_masks(table):

    """
    This function ...
    :param table:
    :return:
    """

    # Look for masks
    for colname in table.colnames:
        key = colname + " mask"
        if key not in table.meta: continue
        if len(table) != len(table.meta[key]): raise IOError("Length of the table does not correspond to the length of the masks")
        for index in range(len(table)): table[colname].mask[index] = table.meta[key][index]
        del table.meta[key]

# -----------------------------------------------------------------

def initialize_table(table):

    """
    This function ...
    :return:
    """

    # Clear the column info so that we can rebuild it
    table.column_info = []

    # Set the column info
    # Loop over the columns
    for name in table.colnames:

        # Get the type
        dtype = table[name].dtype
        if np.issubdtype(dtype, np.string_): simple_dtype = str
        elif np.issubdtype(dtype, np.float): simple_dtype = float
        elif np.issubdtype(dtype, np.int): simple_dtype = int
        elif np.issubdtype(dtype, np.bool): simple_dtype = bool
        else: raise ValueError("Did not recognize the dtype of column '" + name + "'")

        # Get unit of the column
        unit = table.column_unit(name)

        # Set this unit object as the actual column unit (so it can be a PhotometricUnit)
        table[name].unit = unit

        # Add column info
        table.add_column_info(name, simple_dtype, unit, None)

        # Initialize "density" meta
        if "density" not in table.meta: table.meta["density"] = []

        # Initialize "brightness" meta
        if "brightness" not in table.meta: table.meta["brightness"] = []

# -----------------------------------------------------------------
