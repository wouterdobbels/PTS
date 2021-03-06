#!/usr/bin/env python
# -*- coding: utf8 -*-
# *****************************************************************
# **       PTS -- Python Toolkit for working with SKIRT          **
# **       © Astronomical Observatory, Ghent University          **
# *****************************************************************

## \package pts.modeling.build.builder Contains the ModelBuilder class.

# -----------------------------------------------------------------

# Ensure Python 3 compatibility
from __future__ import absolute_import, division, print_function

# Import standard modules
from collections import OrderedDict

# Import the relevant PTS classes and modules
from ...core.tools import filesystem as fs
from ...core.tools.utils import lazyproperty
from .tables import ModelsTable, RepresentationsTable, ModelMapsTable
from ...core.basics.map import Map
from ...core.basics.configuration import open_mapping
from ..basics.models import DeprojectionModel3D, load_3d_model
from ...core.tools.serialization import load_dict
from ...magic.core.frame import Frame
from ...magic.basics.coordinatesystem import CoordinateSystem
from .representation import Representation
from ...core.basics.log import log
from .construct import add_stellar_component, add_dust_component
from ...core.tools.utils import create_lazified_class
from ...core.tools import tables

# -----------------------------------------------------------------

model_map_basename = "map"

# -----------------------------------------------------------------

parameters_filename = "parameters.cfg"
deprojection_filename = "deprojection.mod"
model_map_filename = model_map_basename + ".fits"
model_filename = "model.mod"
properties_filename = "properties.dat"

# -----------------------------------------------------------------

models_name = "models"
representations_name = "representations"

# -----------------------------------------------------------------

models_table_filename = "models.dat"
maps_table_filename = "maps.dat"
representations_table_filename = "representations.dat"

# -----------------------------------------------------------------

class ModelSuite(object):

    """
    This function ...
    """

    def __init__(self, path):

        """
        This function ...
        :param path:
        """

        # Set the build path
        self.path = path

        # Determine the path to the models directory
        self.models_path = fs.create_directory_in(self.build_path, models_name)

        # Determine the path to the models table
        self.models_table_path = fs.join(self.models_path, models_table_filename)

        # Initialize the models table if necessary
        if not fs.is_file(self.models_table_path):
            table = ModelsTable()
            table.saveto(self.models_table_path)

        # Determine the path to the maps table
        self.maps_table_path = fs.join(self.models_path, maps_table_filename)

        # Initialize the maps table if necessary
        if not fs.is_file(self.maps_table_path):
            table = ModelMapsTable()
            table.saveto(self.maps_table_path)

        # Determine the path to the representations directory
        self.representations_path = fs.create_directory_in(self.build_path, representations_name)

        # Determine the path to the representations table
        self.representations_table_path = fs.join(self.representations_path, representations_table_filename)

        # Initialize the representations table if necessary
        if not fs.is_file(self.representations_table_path):
            table = RepresentationsTable()
            table.saveto(self.representations_table_path)

    # -----------------------------------------------------------------

    @classmethod
    def from_modeling_path(cls, path):

        """
        This function ...
        :param path:
        :return:
        """

        return cls(fs.join(path, "build"))

    # -----------------------------------------------------------------

    @property
    def build_path(self):

        """
        This function ...
        :return:
        """

        return self.path

    # -----------------------------------------------------------------

    @property
    def modeling_path(self):

        """
        This function ...
        :return:
        """

        return fs.directory_of(self.path)

    # -----------------------------------------------------------------

    @lazyproperty
    def galaxy_name(self):

        """
        This function ...
        :return:
        """

        return fs.name(self.modeling_path)

    # -----------------------------------------------------------------

    @lazyproperty
    def galaxy_properties_path(self):

        """
        This function ...
        :return:
        """

        from ..core.environment import properties_name, data_name
        return fs.join(self.modeling_path, data_name, properties_name)

    # -----------------------------------------------------------------

    @lazyproperty
    def galaxy_properties(self):

        """
        This function ...
        :return:
        """

        # Load the properties
        from ..basics.properties import GalaxyProperties
        return GalaxyProperties.from_file(self.galaxy_properties_path)

    # -----------------------------------------------------------------

    @property
    def galaxy_distance(self):

        """
        This function ...
        :return:
        """

        return self.galaxy_properties.distance

    # -----------------------------------------------------------------

    @property
    def galaxy_center(self):

        """
        This function ...
        :return:
        """

        return self.galaxy_properties.center

    # -----------------------------------------------------------------

    @property
    def galaxy_info_path(self):

        """
        This function ...
        :return:
        """

        #  Set the path to the galaxy info file
        modeling_data_path = fs.join(self.modeling_path, "data")
        return fs.join(modeling_data_path, "info.dat")

    # -----------------------------------------------------------------

    @lazyproperty
    def galaxy_info(self):

        """
        This function ...
        :return:
        """

        # Load the info table
        table = tables.from_file(self.galaxy_info_path)

        # To ordered dict
        info = OrderedDict()
        for name in table.colnames: info[name] = table[name][0]

        # Return the info
        return info

    # -----------------------------------------------------------------

    @lazyproperty
    def hubble_type(self):

        """
        This function ...
        :return:
        """

        return self.galaxy_info["Hubble Type"]

    # -----------------------------------------------------------------

    @lazyproperty
    def hubble_stage(self):

        """
        Thisf unction ...
        :return:
        """

        return self.galaxy_info["Hubble Stage"]

    # -----------------------------------------------------------------

    def get_model_definition(self, model_name):

        """
        This function ...
        :param model_name:
        :return:
        """

        from .definition import ModelDefinition

        # Determine model path
        path = self.get_model_path(model_name)
        if not fs.is_directory(path): raise ValueError("Model does not exist")

        # Load the table
        table = self.models_table

        # Determine the stellar component paths
        stellar_paths = table.stellar_component_paths_for_model(model_name)

        # Determine the dust component paths
        dust_paths = table.dust_component_paths_for_model(model_name)

        # Create the model definition and return
        return ModelDefinition(model_name, path, stellar_paths=stellar_paths, dust_paths=dust_paths)

    # -----------------------------------------------------------------

    def get_model(self, model_name, representation_name=None):

        """
        This function ...
        :param model_name:
        :param representation_name:
        :return:
        """

        from ..core.model import RTModel

        # Get the definition
        definition = self.get_model_definition(model_name)

        # Get the representation
        if representation_name is not None: representation = self.get_model_representation(representation_name)
        else: representation = None

        # Get representation information
        if representation is not None:
            reference_wcs = representation.reference_map_wcs
        else: reference_wcs = None

        # Create the RTModel
        return RTModel(definition, simulation_name=model_name, center=self.galaxy_center,
                       galaxy_name=self.galaxy_name, hubble_stage=self.hubble_stage, earth_wcs=reference_wcs)

    # -----------------------------------------------------------------

    @property
    def models_table(self):

        """
        This function ...
        :return:
        """

        # Open the table
        return ModelsTable.from_file(self.models_table_path)

    # -----------------------------------------------------------------

    @property
    def maps_table(self):

        """
        This function ...
        :return:
        """

        return ModelMapsTable.from_file(self.maps_table_path)

    # -----------------------------------------------------------------

    def get_old_map_name_for_model(self, model_name):

        """
        This function ...
        :param model_name:
        :return:
        """

        return self.maps_table.old_stars_map_name_for_model(model_name)

    # -----------------------------------------------------------------

    def get_young_map_name_for_model(self, model_name):

        """
        Thisn function ...
        :param model_name:
        :return:
        """

        return self.maps_table.young_stars_map_name_for_model(model_name)

    # -----------------------------------------------------------------

    def get_ionizing_map_name_for_model(self, model_name):

        """
        This function ...
        :param model_name:
        :return:
        """

        return self.maps_table.ionizing_stars_map_name_for_model(model_name)

    # -----------------------------------------------------------------

    def get_dust_map_name_for_model(self, model_name):

        """
        This function ...
        :param model_name:
        :return:
        """

        return self.maps_table.dust_map_name_for_model(model_name)

    # -----------------------------------------------------------------

    @property
    def model_names(self):

        """
        This function ...
        :return:
        """

        return self.models_table.names

    # -----------------------------------------------------------------

    @property
    def nmodels(self):

        """
        This function ...
        :return:
        """

        return len(self.model_names)

    # -----------------------------------------------------------------

    @property
    def has_models(self):

        """
        This function ...
        :return:
        """

        return self.nmodels > 0

    # -----------------------------------------------------------------

    @property
    def no_models(self):

        """
        This function ...
        :return:
        """

        return self.nmodels == 0

    # -----------------------------------------------------------------

    @property
    def has_single_model(self):

        """
        This function ...
        :return:
        """

        return self.nmodels == 1

    # -----------------------------------------------------------------

    @property
    def single_model_name(self):

        """
        This function ...
        :return:
        """

        return self.model_names[0]

    # -----------------------------------------------------------------

    def get_model_path(self, model_name):

        """
        This function ...
        :param model_name:
        :return:
        """

        return fs.join(self.models_path, model_name)

    # -----------------------------------------------------------------

    def get_model_stellar_path(self, model_name):

        """
        This function ...
        :param model_name:
        :return:
        """

        return fs.join(self.get_model_path(model_name), "stellar")

    # -----------------------------------------------------------------

    def get_model_dust_path(self, model_name):

        """
        This function ...
        :param model_name:
        :return:
        """

        return fs.join(self.get_model_path(model_name), "dust")

    # -----------------------------------------------------------------

    def get_stellar_component_paths(self, model_name):

        """
        This function ...
        :param model_name:
        :return:
        """

        return self.models_table.stellar_component_paths_for_model(model_name).values()

    # -----------------------------------------------------------------

    def get_stellar_component_names(self, model_name):

        """
        This function ...
        :return:
        """

        # NO
        #return fs.directories_in_path(self.get_model_stellar_path(model_name), returns="name")

        # NEW
        table = self.models_table
        return table.stellar_component_names_for_model(model_name)

    # -----------------------------------------------------------------

    def get_dust_component_paths(self, model_name):

        """
        This function ...
        :param model_name:
        :return:
        """

        return self.models_table.dust_component_paths_for_model(model_name).values()

    # -----------------------------------------------------------------

    def get_dust_component_names(self, model_name):

        """
        This function ...
        :param model_name:
        :return:
        """

        # NO
        #return fs.directories_in_path(self.get_model_dust_path(model_name), returns="name")

        # NEW
        table = self.models_table
        return table.dust_component_names_for_model(model_name)

    # -----------------------------------------------------------------

    def is_representation(self, representation_name):

        """
        Thisf unction ...
        :param representation_name:
        :return:
        """

        path = self.get_representation_path(representation_name)
        return fs.is_directory(path)

    # -----------------------------------------------------------------

    def get_model_name_for_representation(self, representation_name):

        """
        This function ...
        :param representation_name:
        :return:
        """

        if not self.is_representation(representation_name): raise ValueError("Representation does not exist")

        # Get model name
        return self.representations_table.model_for_representation(representation_name)

    # -----------------------------------------------------------------

    def get_representation(self, representation_name):

        """
        This function ...
        :param representation_name:
        :return:
        """

        path = self.get_representation_path(representation_name)
        if not self.is_representation(representation_name): raise ValueError("Representation does not exist")
        else:
            model_name = self.get_model_name_for_representation(representation_name)
            return Representation(representation_name, model_name, path)

    # -----------------------------------------------------------------

    def get_model_representation(self, representation_name):

        """
        This function ...
        :param representation_name:
        :return:
        """

        return self.get_representation(representation_name)

    # -----------------------------------------------------------------

    def get_representation_path(self, representation_name):

        """
        This function ...
        :param representation_name:
        :return:
        """

        return fs.join(self.representations_path, representation_name)

    # -----------------------------------------------------------------

    @property
    def representations_table(self):

        """
        This function ...
        :return:
        """

        return RepresentationsTable.from_file(self.representations_table_path)

    # -----------------------------------------------------------------

    @property
    def representation_names(self):

        """
        This function ...
        :return:
        """

        return self.representations_table.names

    # -----------------------------------------------------------------

    @property
    def nrepresentations(self):

        """
        This function ...
        :return:
        """

        return len(self.representation_names)

    # -----------------------------------------------------------------

    @property
    def has_representations(self):

        """
        This functino ...
        :return:
        """

        return self.nrepresentations > 0

    # -----------------------------------------------------------------

    @property
    def no_representations(self):

        """
        This function ...
        :return:
        """

        return self.nrepresentations == 0

    # -----------------------------------------------------------------

    @property
    def has_single_representation(self):

        """
        This function ...
        :return:
        """

        return self.nrepresentations == 1

    # -----------------------------------------------------------------

    @property
    def single_representation_name(self):

        """
        This function ...
        :return:
        """

        return self.representation_names[0]

    # -----------------------------------------------------------------

    def representations_for_model(self, model_name):

        """
        This function ...
        :param model_name:
        :return:
        """

        return self.representations_table.representations_for_model(model_name)

    # -----------------------------------------------------------------

    def create_deprojection_for_wcs(self, galaxy_properties, disk_position_angle, wcs, filename, scaleheight):

        """
        This function ...
        :param galaxy_properties: has to be passed since this class is GENERAL (BUT THIS FUNCTION CAN ONLY BE CALLED FOR A GALAXY MODELING ENVIRONMENT)
        :param disk_position_angle:
        :param wcs:
        :param filename:
        :param scaleheight:
        :return:
        """

        # Create the deprojection
        return create_deprojection_for_wcs(galaxy_properties, disk_position_angle, wcs, filename, scaleheight)

    # -----------------------------------------------------------------

    def create_deprojection_for_map(self, galaxy_properties, disk_position_angle, map, filename, scaleheight, inclination=None):

        """
        This function ...
        :param galaxy_properties:
        :param disk_position_angle:
        :param map:
        :param filename:
        :param scaleheight:
        :param inclination:
        :return:
        """

        # Create the deprojection
        return create_deprojection_for_map(galaxy_properties, disk_position_angle, map, filename, scaleheight, inclination=inclination)

    # -----------------------------------------------------------------

    def load_component(self, path, add_map=False):

        """
        This function ...
        :param path:
        :param add_map:
        :return:
        """

        return load_component(path, add_map=add_map)

    # -----------------------------------------------------------------

    def load_component_map(self, path):

        """
        Thisf unction ...
        :param path:
        :return:
        """

        return load_component_map(path)

    # -----------------------------------------------------------------

    def load_component_map_wcs(self, path):

        """
        This function ...
        :param path:
        :return:
        """

        return load_component_map_wcs(path)

    # -----------------------------------------------------------------

    def get_stellar_component_path(self, model_name, component_name):

        """
        This function ...
        :param model_name:
        :param component_name:
        :return:
        """

        # NO
        #return fs.join(self.get_model_stellar_path(model_name), component_name)

        # NEW
        return self.models_table.stellar_component_path_for_name(model_name, component_name)

    # -----------------------------------------------------------------

    def get_dust_component_path(self, model_name, component_name):

        """
        This function ...
        :param modeling_path:
        :param model_name:
        :param component_name:
        :return:
        """

        # NO
        #return fs.join(self.get_model_dust_path(model_name), component_name)

        # NEW
        return self.models_table.dust_component_path_for_name(model_name, component_name)

    # -----------------------------------------------------------------

    def load_stellar_component(self, model_name, component_name, add_map=False):

        """
        This function ...
        :param model_name:
        :param component_name:
        :param add_map:
        :return:
        """

        # Determine the path
        path = self.get_stellar_component_path(model_name, component_name)

        # Load the component
        return self.load_component(path, add_map=add_map)

    # -----------------------------------------------------------------

    def load_stellar_components(self, model_name, add_map=False):

        """
        This function ...
        :param model_name:
        :param add_map:
        :return:
        """

        # Loop over the paths
        for path in self.get_stellar_component_paths(model_name):

            # Give the component
            yield self.load_component(path, add_map=add_map)

    # -----------------------------------------------------------------

    def load_stellar_component_deprojection(self, model_name, component_name, load_map=False):

        """
        This function ...
        :param model_name:
        :param component_name:
        :param load_map:
        :return:
        """

        from ..component.galaxy import get_disk_position_angle

        # Load galaxy properties
        from ..component.galaxy import get_galaxy_properties
        properties = get_galaxy_properties(self.modeling_path)

        # Load component
        component = self.load_stellar_component(model_name, component_name, add_map=load_map)

        # Get the map
        if "map" in component: the_map = component.map
        else: the_map = None

        ## Set deprojection
        if "deprojection" in component:

            # Get title
            title = component.parameters.title

            # Return
            deprojection = component.deprojection
            if the_map is not None: deprojection.map = the_map
            return title, deprojection

        # Check if this is a new component, add geometry, SED and normalization all at once
        if "geometry" in component.parameters:

            # Get title
            title = component.parameters.title

            # Check whether this is a read FITS geometry
            geometry_type = component.parameters.geometry
            if geometry_type != "ReadFitsGeometry": return component.parameters.title, None

            # Get properties for each of the three classes
            geometry_properties = component.properties["geometry"]

            # Get the path of the input map
            filepath = geometry_properties["filename"]

            # Get the scale height
            scale_height = geometry_properties["axialScale"]

            # Get properties
            wcs = CoordinateSystem.from_file(filepath)

            # Get the galaxy distance, the inclination and position angle
            distance = properties.distance
            inclination = properties.inclination
            position_angle = get_disk_position_angle(self.modeling_path)
            # Get center coordinate of galaxy
            galaxy_center = properties.center

            # Create
            deprojection = DeprojectionModel3D.from_wcs(wcs, galaxy_center, distance, position_angle, inclination,
                                                        filepath, scale_height)

            # Set the map
            if the_map is not None: deprojection.map = the_map

            # Return
            return title, deprojection

        # No deprojection
        return component.parameters.title, None

    # -----------------------------------------------------------------

    def get_stellar_component_map_path(self, model_name, component_name):

        """
        This function ...
        :param model_name:
        :param component_name:
        :return:
        """

        # Determine the path
        path = self.get_stellar_component_path(model_name, component_name)

        # Return the map path
        return get_component_map_path(path)

    # -----------------------------------------------------------------

    def load_stellar_component_map(self, model_name, component_name):

        """
        This function ...
        :param model_name:
        :param component_name:
        :return:
        """

        # Determine the path
        path = self.get_stellar_component_path(model_name, component_name)

        # Load the map
        return self.load_component_map(path)

    # -----------------------------------------------------------------

    def load_stellar_component_wcs(self, model_name, component_name):

        """
        This function ...
        :param model_name:
        :param component_name:
        :return:
        """

        # Determine the path
        path = self.get_stellar_component_path(model_name, component_name)

        # Load the coordinate system
        return self.load_component_map_wcs(path)

    # -----------------------------------------------------------------

    def load_dust_component(self, model_name, component_name, add_map=False):

        """
        This function ...
        :param model_name:
        :param component_name:
        :param add_map:
        :return:
        """

        # Determine the path
        path = self.get_dust_component_path(model_name, component_name)

        # Load the component
        return self.load_component(path, add_map=add_map)

    # -----------------------------------------------------------------

    def load_dust_components(self, model_name, add_map=False):

        """
        This function ...
        :param model_name:
        :param add_map:
        :return:
        """

        # Loop over the paths
        for path in self.get_dust_component_paths(model_name):

            # Give the component
            yield self.load_component(path, add_map=add_map)

    # -----------------------------------------------------------------

    def load_dust_component_deprojection(self, model_name, component_name, load_map=False):

        """
        This function ...
        :param modeling_path:
        :param model_name:
        :param component_name:
        :param load_map:
        """

        from ..component.galaxy import get_disk_position_angle

        # Load galaxy properties
        from ..component.galaxy import get_galaxy_properties
        properties = get_galaxy_properties(self.modeling_path)

        # Load the component
        component = self.load_dust_component(model_name, component_name, add_map=load_map)

        # Get the map
        if "map" in component: the_map = component.map
        else: the_map = None

        # Set deprojection
        if "deprojection" in component:

            # Get title
            title = component.parameters.title

            # Return
            deprojection = component.deprojection
            if the_map is not None: deprojection.map = the_map
            return title, deprojection

        # Check if this is a new dust component, add geometry, mix and normalization all at once
        if "geometry" in component.parameters:

            # Get title
            title = component.parameters.title

            # Check whether this is a read FITS geometry
            geometry_type = component.parameters.geometry
            if geometry_type != "ReadFitsGeometry": return title, None

            # Get properties for each of the three classes
            geometry_properties = component.properties["geometry"]

            # Get the path of the input map
            filepath = geometry_properties["filename"]

            # Get the scale height
            scale_height = geometry_properties["axialScale"]

            # Get properties
            wcs = CoordinateSystem.from_file(filepath)

            # Get the galaxy distance, the inclination and position angle
            distance = properties.distance
            inclination = properties.inclination
            position_angle = get_disk_position_angle(self.modeling_path)
            # Get center coordinate of galaxy
            galaxy_center = properties.center

            # Create
            deprojection = DeprojectionModel3D.from_wcs(wcs, galaxy_center, distance, position_angle, inclination,
                                                        filepath, scale_height)

            # Set the map
            if the_map is not None: deprojection.map = the_map

            # Return
            return title, deprojection

        # No deprojection for this component
        return component.parameters.title, None

    # -----------------------------------------------------------------

    def get_dust_component_map_path(self, model_name, component_name):

        """
        This function ...
        :param model_name:
        :param component_name:
        :return:
        """

        # Determine the path
        path = self.get_dust_component_path(model_name, component_name)

        # Return the map path
        return get_component_map_path(path)

    # -----------------------------------------------------------------

    def load_dust_component_map(self, model_name, component_name):

        """
        This function ...
        :param model_name:
        :param component_name:
        :return:
        """

        # Determine the path
        path = self.get_dust_component_path(model_name, component_name)

        # Load the map
        return self.load_component_map(path)

    # -----------------------------------------------------------------

    def load_dust_component_wcs(self, model_name, component_name):

        """
        This function ...
        :param model_name:
        :param component_name:
        :return:
        """

        # Determine the path
        path = self.get_dust_component_path(model_name, component_name)

        # Load the WCS
        return self.load_component_map_wcs(path)

    # -----------------------------------------------------------------

    def add_model_components(self, model_name, ski, input_map_paths):

        """
        This function ...
        :param model_name:
        :param ski:
        :param input_map_paths:
        :return:
        """

        # Inform the user
        log.info("Adding the components of model '" + model_name + "' to the ski file ...")

        # 1. Set stellar components
        self.add_stellar_components(model_name, ski, input_map_paths)

        # 2. Set dust components
        self.add_dust_components(model_name, ski, input_map_paths)

    # -----------------------------------------------------------------

    def add_stellar_components(self, model_name, ski, input_map_paths):

        """
        This function ...
        :param model_name:
        :param ski
        :param input_map_paths:
        :return:
        """

        from .models.stars import titles as stellar_titles

        # Inform the user
        log.info("Adding the stellar components of model '" + model_name + "' to the ski file ...")

        # Loop over the stellar components
        #for name in self.get_stellar_component_names(model_name): # SLOWER BECAUSE MODELS TABLE WILL BE READ MULTIPLE TIMES
        for component in self.load_stellar_components(model_name, add_map=False):

            # Debugging
            log.debug("Adding the '" + component.name + "' stellar component ...")

            # Load the component
            #component = self.load_stellar_component(model_name, name, add_map=False) # SLOWER BECAUSE ...

            # Try to get the title
            name = component.name
            title = stellar_titles[name] if name in stellar_titles else None

            # Debugging
            if title is not None: log.debug("Adding the component under the title '" + title + "' ...")

            # Add the stellar component
            map_filename = add_stellar_component(ski, name, component, title=title)

            # If map filename is defined, set path in dictionary
            if map_filename is not None: input_map_paths[map_filename] = component.map_path

    # -----------------------------------------------------------------

    def add_dust_components(self, model_name, ski, input_map_paths):

        """
        This function ...
        :param model_name:
        :param ski:
        :param input_map_paths:
        :return:
        """

        from .models.dust import titles as dust_titles

        # Inform the user
        log.info("Adding the dust components of model '" + model_name + "' to the ski file ...")

        # Loop over the dust components
        #for name in self.get_dust_component_names(model_name): # SLOWER BECAUSE MODELS TABLE WILL BE READ MULTIPLE TIMES
        for component in self.load_dust_components(model_name, add_map=False):

            # Debugging
            log.debug("Adding the '" + component.name + "' dust component ...")

            # Load the component
            #component = self.load_dust_component(model_name, name, add_map=False) # SLOWER BECAUSE ...

            # Try to get the title
            name = component.name
            title = dust_titles[name] if name in dust_titles else None

            # Debugging
            if title is not None: log.debug("Adding the component under the title '" + title + "' ...")

            # Add the dust component
            map_filename = add_dust_component(ski, name, component, title=title)

            # If map filename is defined, set path in dictionary
            if map_filename is not None: input_map_paths[map_filename] = component.map_path

# -----------------------------------------------------------------

StaticModelSuite = create_lazified_class(ModelSuite, "StaticModelSuite")

# -----------------------------------------------------------------

def create_deprojection_for_wcs(galaxy_properties, disk_position_angle, wcs, filename, scaleheight, inclination=None):

    """
    This function ...
    :param galaxy_properties:
    :param disk_position_angle:
    :param wcs:
    :param filename:
    :param scaleheight:
    :param inclination:
    :return:
    """

    # Get the galaxy distance, the inclination and position angle
    distance = galaxy_properties.distance
    if inclination is None: inclination = galaxy_properties.inclination
    position_angle = disk_position_angle

    # Get center coordinate of galaxy
    galaxy_center = galaxy_properties.center

    # Create deprojection
    # wcs, galaxy_center, distance, pa, inclination, filepath, scale_height
    deprojection = DeprojectionModel3D.from_wcs(wcs, galaxy_center, distance, position_angle, inclination, filename, scaleheight)

    # Return the deprojection
    return deprojection

# -----------------------------------------------------------------

def create_deprojection_for_map(galaxy_properties, disk_position_angle, map, filename, scaleheight, inclination=None):

    """
    This function ...
    :param galaxy_properties:
    :param disk_position_angle:
    :param map:
    :param filename:
    :param scaleheight:
    :param inclination:
    :return:
    """

    # Get the WCS
    reference_wcs = map.wcs

    # Create the deprojection
    return create_deprojection_for_wcs(galaxy_properties, disk_position_angle, reference_wcs, filename, scaleheight, inclination=inclination)

# -----------------------------------------------------------------

def load_component_cwd(add_map=False):

    """
    This function ...
    :param add_map:
    :return:
    """

    return load_component(fs.cwd(), add_map=add_map)

# -----------------------------------------------------------------

def load_component(path, add_map=False):

    """
    This function ...
    :param path:
    :param add_map:
    :return:
    """

    # Create a map
    component = Map()

    # Set the name
    component.name = fs.name(path)

    # Load the parameters
    parameters_path = fs.join(path, parameters_filename)
    if fs.is_file(parameters_path):
        parameters = open_mapping(parameters_path)
        component.parameters = parameters
        component.parameters_path = parameters_path

    # Load the deprojection
    deprojection_path = fs.join(path, deprojection_filename)
    if fs.is_file(deprojection_path):
        deprojection = DeprojectionModel3D.from_file(deprojection_path)
        component.deprojection = deprojection

    # Load the map
    map_path = fs.join(path, model_map_filename)
    if fs.is_file(map_path):
        component.map_path = map_path
        if add_map:
            map = Frame.from_file(map_path)
            component.map = map

    # Load the model
    model_path = fs.join(path, model_filename)
    if fs.is_file(model_path):
        model = load_3d_model(model_path)
        component.model = model

    # Load the properties
    properties_path = fs.join(path, properties_filename)
    if fs.is_file(properties_path):
        properties = load_dict(properties_path)
        component.properties = properties

    # Return the component
    return component

# -----------------------------------------------------------------

def get_component_map_path(path):

    """
    This function ...
    :param path:
    :return:
    """

    # Determine map path
    map_path = fs.join(path, model_map_filename)

    # Check
    if not fs.is_file(map_path): raise IOError("The component map '" + map_path + "' does not exist")

    # Return the map path
    return map_path

# -----------------------------------------------------------------

def load_component_map(path):

    """
    This function ...
    :param path:
    :return:
    """

    # Get the path
    map_path = get_component_map_path(path)

    # Load the map and return
    return Frame.from_file(map_path)

# -----------------------------------------------------------------

def load_component_map_wcs(path):

    """
    This function ...
    :param path:
    :return:
    """

    # Get the path
    map_path = get_component_map_path(path)

    # Load the map and return
    return CoordinateSystem.from_file(map_path)

# -----------------------------------------------------------------

def load_stellar_deprojections(modeling_path, model_name):

    """
    This function ...
    :param modeling_path:
    :param model_name:
    :return:
    """

    # Load the model suite
    suite = ModelSuite.from_modeling_path(modeling_path)

    # Return the deprojections
    return get_stellar_deprojections(suite, model_name)

# -----------------------------------------------------------------

def get_stellar_deprojections(suite, model_name, deprojections=None, add_title=False):

    """
    This function ...
    :param suite:
    :param model_name:
    :param deprojections:
    :param add_title:
    :return:
    """

    # Initialize dictinoary
    return_deprojections = True
    if deprojections is None: deprojections = dict()
    else: return_deprojections = False

    # Loop over the stellar components
    for name in suite.get_stellar_component_names(model_name):

        # Load the deprojection of the component, if applicable
        title, deprojection = suite.load_stellar_component_deprojection(model_name, name)
        if deprojection is not None:
            if add_title: deprojections[(name, title)] = deprojection
            else: deprojections[name] = deprojection

    # Return the deprojections
    if return_deprojections: return deprojections

# -----------------------------------------------------------------

def load_dust_deprojections(modeling_path, model_name):

    """
    This function ...
    :param modeling_path:
    :param model_name:
    :return:
    """

    # Load the model suite
    suite = ModelSuite.from_modeling_path(modeling_path)

    # Return the deprojections
    return get_dust_deprojections(suite, model_name)

# -----------------------------------------------------------------

def get_dust_deprojections(suite, model_name, deprojections=None, add_title=False):

    """
    This function ...
    :param suite:
    :param model_name:
    :param deprojections:
    :param add_title:
    :return:
    """

    # Initialize dictionary
    return_deprojections = True
    if deprojections is not None: deprojections = dict()
    else: return_deprojections = False

    # Loop over the dust components
    for name in suite.get_dust_component_names(model_name):

        # Load the deprojection of the component, if applicable
        title, deprojection = suite.load_dust_component_deprojection(model_name, name)
        if deprojection is not None:
            if add_title: deprojections[(name, title)] = deprojection
            else: deprojections[name] = deprojection

    # Return the deprojections
    if return_deprojections: return deprojections

# -----------------------------------------------------------------
