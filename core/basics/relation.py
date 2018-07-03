#!/usr/bin/env python
# -*- coding: utf8 -*-
# *****************************************************************
# **       PTS -- Python Toolkit for working with SKIRT          **
# **       © Astronomical Observatory, Ghent University          **
# *****************************************************************

## \package pts.core.basics.relation Contains the Relation class.

# -----------------------------------------------------------------

# Ensure Python 3 compatibility
from __future__ import absolute_import, division, print_function

# Import standard modules
import numpy as np
import copy

# Import the relevant PTS classes and modules
from .table import SmartTable
from ..tools import arrays

# -----------------------------------------------------------------

class Relation(SmartTable):

    """
    This class ...
    """

    def __init__(self, *args, **kwargs):

        """
        This function ...
        :param args:
        :param kwargs:
        """

        if kwargs.get("from_astropy", None) is None:
            if "x_unit" in kwargs: from_astropy = False
            else: from_astropy = True
        else: from_astropy = kwargs.pop("from_astropy")

        # Get properties
        if not from_astropy:
            x_unit = kwargs.pop("x_unit", None)
            y_unit = kwargs.pop("y_unit", None)
            x_name = kwargs.pop("x_name", "x")
            y_name = kwargs.pop("y_name", "y")
            x_description = kwargs.pop("x_description", "x values")
            y_description = kwargs.pop("y_description", "y values")
        else: x_unit = y_unit = x_name = y_name = x_description = y_description = None

        # Call the constructor of the base class
        super(Relation, self).__init__(*args, **kwargs)

        # Set properties
        if not from_astropy:

            # Set the column info
            self.add_column_info(x_name, float, x_unit, x_description)
            self.add_column_info(y_name, float, y_unit, y_description)

            # Set x name and y name
            self.x_name = x_name
            self.y_name = y_name

    # -----------------------------------------------------------------

    def copy(self):

        """
        This function ...
        :return:
        """

        new = copy.deepcopy(self)
        if hasattr(self, "x_name"): new.x_name = self.x_name
        if hasattr(self, "y_name"): new.y_name = self.y_name
        return new

    # -----------------------------------------------------------------

    @classmethod
    def from_columns(cls, *columns, **kwargs):

        """
        This function ...
        :param columns:
        :param kwargs:
        :return:
        """

        kwargs["from_astropy"] = False

        # x and y name
        if kwargs.get("names", None) is not None:
            names = kwargs.get("names")
            x_name = names[0]
            y_name = names[1]
            kwargs["x_name"] = x_name
            kwargs["y_name"] = y_name

        # x and y unit
        if kwargs.get("units", None) is not None:
            units = kwargs.get("units")
            x_unit = units[0]
            y_unit = units[1]
            kwargs["x_unit"] = x_unit
            kwargs["y_unit"] = y_unit

        # x and y descriptions
        #if kwargs.get("descriptions", None) is not None:
        descriptions = kwargs.get("descriptions", ("no description", "no description"))
        x_description = descriptions[0]
        y_description = descriptions[1]
        kwargs["x_description"] = x_description
        kwargs["y_description"] = y_description

        # USe the base class implementation
        curve = super(Relation, cls).from_columns(*columns, **kwargs)

        # Set x name and y name
        curve.x_name = curve.column_names[0]
        curve.y_name = curve.column_names[1]

        # Return the curve
        return curve

    # -----------------------------------------------------------------

    @classmethod
    def from_file(cls, path):

        """
        This function ...
        :return:
        """

        # Load the curve
        relation = super(Relation, cls).from_file(path)

        # Set x name and y name
        relation.x_name = relation.column_info[0][0]
        relation.y_name = relation.column_info[1][0]

        # Return the relation
        return relation

    # -----------------------------------------------------------------

    @classmethod
    def from_data_file(cls, path, x_name="x", x_description="x values", x_unit=None, y_name="y",
                       y_description="y values", y_unit=None, x_column=0, y_column=1, skiprows=0, conversion_info=None):

        """
        This function ...
        :param path:
        :param x_name:
        :param x_description:
        :param x_unit:
        :param y_name:
        :param y_description:
        :param y_unit:
        :param x_column:
        :param y_column:
        :param skiprows:
        :param conversion_info:
        :return:
        """

        # Define columns
        columns = (x_column, y_column)

        kwargs = dict()

        kwargs["x_name"] = x_name
        kwargs["x_description"] = x_description
        kwargs["x_unit"] = x_unit

        kwargs["y_name"] = y_name
        kwargs["y_description"] = y_description
        kwargs["y_unit"] = y_unit

        # Create the curve
        curve = cls(**kwargs)
        x_values, y_values = np.loadtxt(path, unpack=True, usecols=columns, skiprows=skiprows)
        for x_value, y_value in zip(x_values, y_values): curve.add_point(x_value, y_value, conversion_info=conversion_info)

        # Return the curve
        return curve

    # -----------------------------------------------------------------

    @property
    def x_unit(self):

        """
        This function ...
        :return:
        """

        return self[self.x_name].unit

    # -----------------------------------------------------------------

    @property
    def y_unit(self):

        """
        This function ...
        :return:
        """

        return self[self.y_name].unit

    # -----------------------------------------------------------------

    @property
    def x_data(self):

        """
        This function ...
        :return:
        """

        return self[self.x_name]

    # -----------------------------------------------------------------

    @property
    def y_data(self):

        """
        This function ...
        :return:
        """

        return self[self.y_name]

    # -----------------------------------------------------------------

    def add_point(self, x_value, y_value, conversion_info=None, sort=False):

        """
        This function ...
        :param x_value:
        :param y_value:
        :param conversion_info:
        :param sort: DEFAULT IS FALSE HERE
        :return:
        """

        # Set values
        values = [x_value, y_value]

        # Add a row
        self.add_row(values, conversion_info=conversion_info)

        # Sort the table by the x values
        if sort: self.sort(self.x_name)

    # -----------------------------------------------------------------

    @property
    def has_errors(self):

        """
        This function ...
        :return:
        """

        return "Error-" in self.colnames and "Error+" in self.colnames

    # -----------------------------------------------------------------

    def get_x(self, unit=None, asarray=False, add_unit=True, conversion_info=None, density=False, brightness=False):

        """
        This function ...
        :param unit:
        :param asarray:
        :param add_unit:
        :param conversion_info:
        :param density:
        :param brightness:
        :return:
        """

        # Create and return
        if asarray: return arrays.plain_array(self[self.x_name], unit=unit, array_unit=self.column_unit(self.x_name),
                                      conversion_info=conversion_info, density=density, brightness=brightness)
        else: return arrays.array_as_list(self[self.x_name], unit=unit, add_unit=add_unit,
                                        array_unit=self.column_unit(self.x_name), conversion_info=conversion_info,
                                        density=density, brightness=brightness)

    # -----------------------------------------------------------------

    def get_y(self, unit=None, asarray=False, add_unit=True, conversion_info=None, density=False, brightness=False):

        """
        This function ...
        :param unit:
        :param asarray:
        :param add_unit:
        :param conversion_info:
        :param density:
        :param brightness:
        :return:
        """

        # Create and return
        if asarray: return arrays.plain_array(self[self.y_name], unit=unit, array_unit=self.column_unit(self.y_name),
                                      conversion_info=conversion_info, density=density, brightness=brightness)
        else: return arrays.array_as_list(self[self.y_name], unit=unit, add_unit=add_unit,
                                        array_unit=self.column_unit(self.y_name), conversion_info=conversion_info,
                                        density=density, brightness=brightness)

    # -----------------------------------------------------------------

    @property
    def npoints(self):

        """
        Thisf unction
        :return:
        """

        return len(self)

    # -----------------------------------------------------------------

    def get_indices(self, x_min=None, x_max=None, include_min=True, include_max=True):

        """
        This function ...
        :param x_min:
        :param x_max:
        :param include_min:
        :param include_max:
        :return:
        """

        # No limits given
        if x_min is None and x_max is None: return list(range(self.npoints))

        # Get the values
        x_values = self.get_x()

        indices = []

        # Loop over the values
        for index, value in enumerate(x_values):

            # Checks
            if x_min is not None:
                if include_min:
                    if value < x_min: continue
                else:
                    if value <= x_min: continue
            if x_max is not None:
                if include_max:
                    if value > x_max: continue
                else:
                    if value >= x_max: continue

            # Add the index
            indices.append(index)

        # Return the indices
        return indices

    # -----------------------------------------------------------------

    def splice(self, x_min=None, x_max=None, include_min=True, include_max=True):

        """
        This function ...
        :param x_min:
        :param x_max:
        :param include_min:
        :param include_max:
        :return:
        """

        # Get the indices
        indices = self.get_indices(x_min, x_max, include_min=include_min, include_max=include_max) # don't name arguments because of re-definition of function in WavelengthCurve class

        # Set the x and y unit
        x_unit = self.x_unit
        y_unit = self.y_unit

        # Get the values
        x_values = [self.get_value(self.x_name, index, unit=x_unit, add_unit=False) for index in indices]
        y_values = [self.get_value(self.y_name, index, unit=y_unit, add_unit=False) for index in indices]

        # Set the names and units
        names = (self.x_name, self.y_name)
        units = (x_unit, y_unit)

        # Create new curve
        return self.__class__.from_columns(x_values, y_values, names=names, units=units)

    # -----------------------------------------------------------------

    def flatten_above(self, value, flatten_value=0., include=True):

        """
        This function ...
        :param value:
        :param flatten_value:
        :param include:
        :return:
        """

        from ..units.parsing import parse_quantity

        # Check value with unit
        if self.x_unit is not None:
            if hasattr(value, "unit"): pass
            elif isinstance(value, basestring): value = parse_quantity(value)
            else: raise ValueError("Unit of the value is not defined")
        elif hasattr(value, "unit") or isinstance(value, basestring): raise ValueError("Unit of the value is defined, but column unit is not")

        # Get the indices of the values to be flattened
        #indices = self.get_indices(x_min=value, include_min=include)
        indices = self.get_indices(value, None, include_min=include) # works also with derived class implementation

        # Set flatten value with unit
        if self.y_unit is not None:
            if hasattr(flatten_value, "unit"): pass
            elif flatten_value == 0.: flatten_value = flatten_value * self.y_unit
            else: raise ValueError("Unit of the flatten value is not defined")
        elif hasattr(flatten_value, "unit") or isinstance(flatten_value, basestring): raise ValueError("Unit of the flatten value is defined, but column unit is not")
        #print(flatten_value)

        # Flatten values
        for index in indices: self.set_value(self.y_name, index, flatten_value)

    # -----------------------------------------------------------------

    def flatten_below(self, value, flatten_value=0., include=True):

        """
        This function ...
        :param value:
        :param flatten_value:
        :param include:
        :return:
        """

        from ..units.parsing import parse_quantity

        # Check value with unit
        if self.x_unit is not None:
            if hasattr(value, "unit"): pass
            elif isinstance(value, basestring): value = parse_quantity(value)
            else: raise ValueError("Unit of the value is not defined")
        elif hasattr(value, "unit") or isinstance(value, basestring): raise ValueError("Unit of the value is defined, but column unit is not")

        # Get the indices of the values to be flattened
        #indices = self.get_indices(x_max=value, include_max=include)
        indices = self.get_indices(None, value, include_max=include) # works also with derived class implementation

        # Set flatten value with unit
        if self.y_unit is not None:
            if hasattr(flatten_value, "unit"): pass
            elif isinstance(flatten_value, basestring): flatten_value = parse_quantity(flatten_value)
            elif flatten_value == 0.: flatten_value = flatten_value * self.y_unit
            else: raise ValueError("Unit of the flatten value is not defined")
        elif hasattr(flatten_value, "unit") or isinstance(flatten_value, basestring): raise ValueError("Unit of the flatten value is defined, but column unit is not")
        #print(flatten_value)

        # Flatten values
        for index in indices: self.set_value(self.y_name, index, flatten_value)

    # -----------------------------------------------------------------

    def flattened_above(self, value, flatten_value=0., include=True):

        """
        This function ...
        :param value:
        :param flatten_value:
        :param include:
        :return:
        """

        # Make copy
        new = self.copy()
        new.flatten_above(value, flatten_value=flatten_value, include=include)
        return new

    # -----------------------------------------------------------------

    def flattened_below(self, value, flatten_value=0., include=True):

        """
        This function ...
        :param value:
        :param flatten_value:
        :param include:
        :return:
        """

        # Make copy
        new = self.copy()
        new.flatten_below(value, flatten_value=flatten_value, include=include)
        return new

# -----------------------------------------------------------------