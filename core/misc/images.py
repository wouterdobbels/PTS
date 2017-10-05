#!/usr/bin/env python
# -*- coding: utf8 -*-
# *****************************************************************
# **       PTS -- Python Toolkit for working with SKIRT          **
# **       © Astronomical Observatory, Ghent University          **
# *****************************************************************

## \package pts.core.misc.fluxes Contains the ObservedImageMaker class.

# -----------------------------------------------------------------

# Ensure Python 3 compatibility
from __future__ import absolute_import, division, print_function

# Import standard modules
import gc
from collections import defaultdict

# Import the relevant PTS classes and modules
from ..basics.log import log
from ..tools import filesystem as fs
from ..filter.filter import parse_filter
from ...magic.core.kernel import ConvolutionKernel
from ...magic.core.kernel import get_fwhm as get_kernel_fwhm
from ...magic.core.datacube import DataCube
from ...magic.basics.coordinatesystem import CoordinateSystem
from ...magic.core.remote import RemoteDataCube
from ...magic.core import fits
from ..simulation.wavelengthgrid import WavelengthGrid
from ..basics.configurable import Configurable
from ..simulation.simulation import createsimulations
from ..tools.utils import lazyproperty
from ..tools import types
from ..remote.remote import Remote
from ..prep.deploy import Deployer
from ..tools import strings
from ..tools.stringify import tostr
from ..tools import numbers

# -----------------------------------------------------------------

default_filter_names = ["FUV", "NUV", "u", "g", "r", "i", "z", "H", "J", "Ks", "I1", "I2", "I3", "I4", "W1", "W2",
                        "W3", "W4", "Pacs 70", "Pacs 100", "Pacs 160", "SPIRE 250", "SPIRE 350", "SPIRE 500"]

# -----------------------------------------------------------------

class ObservedImageMaker(Configurable):

    """
    This class ...
    """

    def __init__(self, *args, **kwargs):

        """
        The constructor ...
        :param interactive:
        :return:
        """

        # Call the constructor of the base class
        super(ObservedImageMaker, self).__init__(*args, **kwargs)

        # -- Attributes --

        # The simulation prefix
        self.simulation_prefix = None

        # The paths to the 'total' FITS files produced by SKIRT
        self.fits_paths = None

        # The wavelengths of the simulation
        self.wavelengths = None

        # The wavelength grid of the simulation
        self.wavelength_grid = None

        # Filter names
        self.filter_names = default_filter_names

        # The instrument names
        self.instrument_names = None

        # The dictionary containing the different SKIRT output datacubes
        self.datacubes = dict()

        # The dictionary containing the created observation images
        self.images = dict()

        # The coordinate systems of each instrument
        self.coordinate_systems = None

        # The FWHMs
        self.fwhms = None

        # The kernel paths
        self.kernel_paths = None

        # The PSF FWHMs
        self.psf_fwhms = None

        # The target unit
        self.unit = None

        # The host id
        self.host_id = None

        # Threshold for using remote datacubes
        self.remote_threshold = None

        # Flag
        self.remote_spectral_convolution = False

        # Thresholds (frame size) for remote rebinning and convolution
        self.remote_rebin_threshold = None
        self.remote_convolve_threshold = None

        # No spectral convolution for certain filters
        self.no_spectral_convolution_filters = []

        # The path to the output data cubes
        self.paths = defaultdict(dict)

        # The rebin coordinate systems
        self.rebin_coordinate_systems = None

    # -----------------------------------------------------------------

    @lazyproperty
    def output_path_hash(self):

        """
        This function ...
        :return:
        """

        return strings.hash_string(self.output_path)

    # -----------------------------------------------------------------

    @lazyproperty
    def remote_intermediate_results_path(self):

        """
        Thisnf unction ...
        :return:
        """

        dirname = "observedimagemaker_" + self.output_path_hash
        dirpath = fs.join(self.remote.pts_temp_path, dirname)

        # Create
        if self.config.write_intermediate and not self.remote.is_directory(dirpath): self.remote.create_directory(dirpath)

        # Return the path
        return dirpath

    # -----------------------------------------------------------------

    @lazyproperty
    def intermediate_results_path(self):

        """
        This function ...
        :return:
        """

        return self.output_path_directory("intermediate", create=self.config.write_intermediate)

    # -----------------------------------------------------------------

    @lazyproperty
    def remote_intermediate_initial_path(self):

        """
        This function ...
        :return:
        """

        # Set path
        initial_path = fs.join(self.remote_intermediate_results_path, "initial")

        # Create?
        if self.config.write_intermediate and not self.remote.is_directory(initial_path): self.remote.create_directory(initial_path)

        # Return the path
        return initial_path

    # -----------------------------------------------------------------

    @lazyproperty
    def intermediate_initial_path(self):

        """
        This function ...
        :return:
        """

        # Set path
        initial_path = fs.join(self.intermediate_results_path, "initial")

        # Create?
        if self.config.write_intermediate and not fs.is_directory(initial_path): fs.create_directory(initial_path)

        # Return the path
        return initial_path

    # -----------------------------------------------------------------

    @lazyproperty
    def remote_intermediate_rebin_path(self):

        """
        This function ...
        :return:
        """

        # Set path
        rebin_path = fs.join(self.remote_intermediate_results_path, "rebin")

        # Create?
        if self.config.write_intermediate and not self.remote.is_directory(rebin_path): self.remote.create_directory(rebin_path)

        # Return the path
        return rebin_path

    # -----------------------------------------------------------------

    @lazyproperty
    def intermediate_rebin_path(self):

        """
        This function ...
        :return:
        """

        # Set path
        rebin_path = fs.join(self.intermediate_results_path, "rebin")

        # Create?
        if self.config.write_intermediate and not fs.is_directory(rebin_path): fs.create_directory(rebin_path)

        # Return the path
        return rebin_path

    # -----------------------------------------------------------------

    @lazyproperty
    def remote_intermediate_convolve_path(self):

        """
        This function ...
        :return:
        """

        # Set path
        convolve_path = fs.join(self.remote_intermediate_results_path, "convolve")

        # Create?
        if self.config.write_intermediate and not self.remote.is_directory(convolve_path): self.remote.create_directory(convolve_path)

        # Return the path
        return convolve_path

    # -----------------------------------------------------------------

    @lazyproperty
    def intermediate_convolve_path(self):

        """
        Thisn function ...
        :return:
        """

        # Set path
        convolve_path = fs.join(self.intermediate_results_path, "convolve")

        # Create?
        if self.config.write_intermediate and not fs.is_directory(convolve_path): fs.create_directory(convolve_path)

        # Return the path
        return convolve_path

    # -----------------------------------------------------------------

    # @lazyproperty
    # def remote_kernels_path(self):
    #
    #     """
    #     Thisnf unction ...
    #     :return:
    #     """
    #
    #     dirname = "observedimagemaker_" + self.output_path_hash + "_kernels"
    #     dirpath = fs.join(self.remote.pts_temp_path, dirname)
    #
    #     # Create
    #     if self.config.write_kernels and not self.remote.is_directory(dirpath): self.remote.create_directory(dirpath)
    #
    #     # Return the path
    #     return dirpath

    # -----------------------------------------------------------------

    @lazyproperty
    def kernels_path(self):

        """
        This function ...
        :return:
        """

        return self.output_path_directory("kernels", create=self.config.write_kernels)

    # -----------------------------------------------------------------

    @property
    def has_coordinate_systems(self):

        """
        This function ...
        :return:
        """

        return self.coordinate_systems is not None

    # -----------------------------------------------------------------

    @property
    def has_kernel_paths(self):

        """
        This function ...
        :return:
        """

        return self.kernel_paths is not None

    # -----------------------------------------------------------------

    @property
    def has_psf_fwhms(self):

        """
        This function ...
        :return:
        """

        return self.psf_fwhms is not None

    # -----------------------------------------------------------------

    @property
    def convolution(self):

        """
        Thisf unction ...
        :return:
        """

        return self.has_kernel_paths or self.has_psf_fwhms

    # -----------------------------------------------------------------

    @property
    def rebinning(self):

        """
        Thisf unction ...
        :return:
        """

        return self.rebin_coordinate_systems is not None

    # -----------------------------------------------------------------

    @property
    def has_remote(self):

        """
        This function ...
        :return:
        """

        return self.host_id is not None

    # -----------------------------------------------------------------

    @lazyproperty
    def remote(self):

        """
        This function ...
        :return:
        """

        return Remote(host_id=self.host_id)

    # -----------------------------------------------------------------

    @lazyproperty
    def session(self):

        """
        This function ...
        :return:
        """

        #new_connection = False
        new_connection = True
        session = self.remote.start_python_session(attached=True, new_connection_for_attached=new_connection)
        return session

    # -----------------------------------------------------------------

    def run(self, **kwargs):

        """
        This function ...
        :param kwargs
        :return:
        """

        # 1. Call the setup function
        self.setup(**kwargs)

        # 2. Create the wavelength grid
        self.create_wavelength_grid()

        # 3. Load the datacubes
        self.load_datacubes()

        # 4. Set the coordinate systems of the datacubes
        if self.has_coordinate_systems: self.set_coordinate_systems()

        # 5. Make the observed images
        self.make_images()

        # 6. Do convolutions
        if self.convolution: self.convolve()

        # 7. Rebin
        if self.rebinning: self.rebin()

        # 8. Add sky
        self.add_sky()

        # 9. Add stars
        self.add_stars()

        # 10. Do unit conversions
        if self.unit is not None: self.convert_units()

        # 11. Write the results
        if self.output_path is not None: self.write()

        # 12. Clear intermediate results
        if not self.config.keep_intermediate: self.clear()

    # -----------------------------------------------------------------

    def setup(self, **kwargs):

        """
        This function ...
        :return:
        """

        # Call the setup function of the base class
        super(ObservedImageMaker, self).setup(**kwargs)

        # simulation, output_path=None, filter_names=None, instrument_names=None, wcs_path=None,
        # kernel_paths=None, unit=None, host_id=None
        if "simulation" in kwargs:
            simulation = kwargs.pop("simulation")
            self.initialize_from_simulation(simulation)
        elif "simulation_output_path" in kwargs:
            simulation = createsimulations(kwargs.pop("simulation_output_path"), single=True)
            self.initialize_from_simulation(simulation)
        else: self.initialize_from_cwd()

        # Get output directory
        output_path = kwargs.pop("output_path", None)
        self.config.output = output_path

        # Get filters for which not to perform spectral convolution
        self.no_spectral_convolution_filters = kwargs.pop("no_spectral_convolution_filters", [])

        # Get filter names for which to create observed images
        self.get_filter_names(**kwargs)

        # Get instrument (datacube names)
        self.get_instrument_names(**kwargs)

        # Get coordinate systems of the datacubes
        self.get_coordinate_systems(**kwargs)

        # Get unit for the images
        self.get_unit(**kwargs)

        # Get kernels
        self.get_kernels(**kwargs)

        # Get rebin coordinate systems
        self.get_rebin_coordinate_systems(**kwargs)

        # Get remote host ID
        self.get_host_id(**kwargs)

        # Update the remote
        if self.has_remote and self.config.deploy_pts: self.deploy_pts()

    # -----------------------------------------------------------------

    def initialize_from_simulation(self, simulation):

        """
        Thisf unction ...
        :param simulation:
        :return:
        """

        # Debugging
        log.debug("Initializing from simulation object ...")

        # Obtain the paths to the 'total' FITS files created by the simulation
        self.fits_paths = simulation.totalfitspaths()

        # Get the list of wavelengths for the simulation
        self.wavelengths = simulation.wavelengths()

        # Get the simulation prefix
        self.simulation_prefix = simulation.prefix()

    # -----------------------------------------------------------------

    def initialize_from_cwd(self):

        """
        This function ...
        :return:
        """

        # Debugging
        log.debug("Simulation or simulation output path not specified: searching for simulation output in the current working directory ...")

        # Get datacube paths
        #datacube_paths = fs.files_in_path(self.config.path, extension="fits")
        total_datacube_paths = fs.files_in_path(self.config.path, extension="fits", endswith="_total")

        # Get SED paths
        sed_paths = fs.files_in_path(self.config.path, extension="dat", endswith="_sed")

        # Determine prefix
        prefix = None
        for path in total_datacube_paths:
            filename = fs.strip_extension(fs.name(path))
            if prefix is None:
                prefix = filename.split("_")[0]
            elif prefix != filename.split("_")[0]:
                raise IOError("Not all datacubes have the same simulation prefix")
        if prefix is None: raise IOError("No datacubes were found")

        # Set the paths to the toatl FITS files created by the simulation
        self.fits_paths = total_datacube_paths

        from ..data.sed import load_sed

        # Load one of the SEDs
        if len(sed_paths) == 0: raise IOError("No SED files") # TODO: look for wavelength grid
        sed = load_sed(sed_paths[0])

        # Set the list of wavelengths for the simulation
        self.wavelengths = sed.wavelengths(asarray=True, unit="micron")

        # Set the simulation prefix
        self.simulation_prefix = prefix

    # -----------------------------------------------------------------

    def get_filter_names(self, **kwargs):

        """
        This function ...
        :param kwargs:
        :return:
        """

        # Filter names
        if kwargs.get("filter_names", None) is not None:

            # Check
            if "filters" in kwargs: raise ValueError("Cannot specify 'filters' and 'filter_names' simultaneously")

            # Set filter names
            self.filter_names = kwargs.pop("filter_names")

        # Filters
        elif kwargs.get("filters", None) is not None: self.filter_names = [str(fltr) for fltr in kwargs.pop("filters")]

        # From config
        elif self.config.filters is not None: self.filter_names = [str(fltr) for fltr in self.config.filters]

    # -----------------------------------------------------------------

    def get_instrument_names(self, **kwargs):

        """
        This function ...
        :param kwargs:
        :return:
        """

        # Debugging
        log.debug("Getting the instrument names ...")

        # Instrument names
        if kwargs.get("instrument_names", None) is not None:

            # Check
            if "instruments" in kwargs: raise ValueError("Cannot specify 'instruments' and 'instrument_names' simultaneously")

            # Get names of the instruments (datacubes) of which to create observed images
            self.instrument_names = kwargs.pop("instrument_names")

        # Instruments
        elif kwargs.get("instruments", None) is not None: self.instrument_names = kwargs.pop("instruments")

        # From config
        elif self.config.instruments is not None: self.instrument_names = self.config.instruments

    # -----------------------------------------------------------------

    def get_coordinate_systems(self, **kwargs):

        """
        This function ...
        :param kwargs:
        :return:
        """

        # Debugging
        log.debug("Getting the coordinate systems ...")

        # WCS
        if kwargs.get("wcs", None) is not None:

            # Check that wcs_instrument is defined
            wcs_instrument = kwargs.pop("wcs_instrument")

            # Get the wcs
            wcs = kwargs.pop("wcs")

            # Set the coordinate system
            self.coordinate_systems = dict()
            self.coordinate_systems[wcs_instrument] = wcs

        # WCS paths
        elif kwargs.get("wcs_paths", None) is not None:

            # Get the paths
            wcs_paths = kwargs.pop("wcs_paths")

            # Defined for each instrument
            if types.is_dictionary(wcs_paths):

                # Initialize
                self.coordinate_systems = dict()

                # Loop over the instruments
                for instrument_name in wcs_paths:

                    # Load wcs
                    wcs = CoordinateSystem.from_file(wcs_paths[instrument_name])

                    # Set wcs
                    self.coordinate_systems[instrument_name] = wcs

            # Invalid
            else: raise ValueError("Invalid option for 'wcs_path'")

        # Single WCS path is defined
        elif kwargs.get("wcs_path", None) is not None:

            # Check that wcs_instrument is defined
            wcs_instrument = kwargs.pop("wcs_instrument")

            # Get the wcs
            wcs_path = kwargs.pop("wcs_path")
            wcs = CoordinateSystem.from_file(wcs_path)

            # Set the coordinate system
            self.coordinate_systems = dict()
            self.coordinate_systems[wcs_instrument] = wcs

    # -----------------------------------------------------------------

    def get_unit(self, **kwargs):

        """
        This function ...
        :param kwargs:
        :return:
        """

        # Debugging
        log.debug("Getting the target unit ...")

        # Get the unit
        self.unit = kwargs.pop("unit", None)

    # -----------------------------------------------------------------

    def get_kernels(self, **kwargs):
        
        """
        This function ...
        :param kwargs: 
        :return: 
        """

        # Debugging
        log.debug("Getting the kernel paths ...")

        # Checks
        auto_psfs = kwargs.pop("auto_psfs", False)
        if kwargs.get("kernel_paths", None) is not None and kwargs.get("psf_paths", None) is not None: raise ValueError("Cannot specify 'kernel_paths' and 'psf_paths' simultaneously")
        if kwargs.get("psf_paths", None) is not None and auto_psfs: raise ValueError("Cannot specify 'psf_paths' when 'auto_psfs' is enabled")
        if auto_psfs and kwargs.get("kernel_paths", None) is not None: raise ValueError("Cannot specify 'kernel_paths' when 'auto_psfs' is enabled")

        # Get FWHMs reference dataset
        if kwargs.get("fwhms_dataset", None) is not None:

            # Load the dataset
            from ...magic.core.dataset import DataSet
            fwhms_dataset = kwargs.pop("fwhms_dataset")
            if types.is_string_type(fwhms_dataset): fwhms_dataset = DataSet.from_file(fwhms_dataset)

            image_names_for_filters = fwhms_dataset.get_names_for_filters(self.filter_names)
            for filter_name, image_name in zip(self.filter_names, image_names_for_filters):

                # Check whether there is such an image
                if image_name is None:
                    log.warning("There is no image in the dataset for the '" + filter_name + "' filter: FWHM cannot be obtained")
                    continue

                # Get the FWHM
                fwhm = fwhms_dataset.get_fwhm(image_name)

                # If defined, set the FWHM
                if fwhm is not None:
                    if self.fwhms is None: self.fwhms = dict()
                    self.fwhms[filter_name] = fwhm
                else: log.warning("The FWHM of the '" + filter_name + "' image in the dataset is not defined")

        # Kernel paths
        if kwargs.get("kernel_paths", None) is not None: self.kernel_paths = kwargs.pop("kernel_paths")

        # PSF paths
        elif kwargs.pop("psf_paths", None) is not None: self.kernel_paths = kwargs.pop("psf_paths")

        # Automatic PSF determination
        elif auto_psfs: self.set_psf_kernels()

    # -----------------------------------------------------------------

    def has_fwhm(self, filter_name):

        """
        This fnction ...
        :param filter_name:
        :return:
        """

        return self.fwhms is not None and filter_name in self.fwhms and self.fwhms[filter_name] is not None

    # -----------------------------------------------------------------

    def set_psf_kernels(self):

        """
        This function ...
        :return:
        """

        # Debugging
        log.debug("Determining the PSF kernel automatically for each image filter ...")

        # Imports
        from pts.magic.convolution.aniano import AnianoKernels
        from pts.magic.convolution.kernels import get_fwhm, has_variable_fwhm, has_average_variable_fwhm, get_average_variable_fwhm

        # Get Aniano kernels object
        aniano = AnianoKernels()

        # Initialize the kernel paths dictionary
        self.kernel_paths = dict()

        # Loop over the filter names
        for filter_name in self.filter_names:

            # Check whether we have Aniano PSF
            if aniano.has_psf_for_filter(filter_name):

                # Get the psf path
                psf_path = aniano.get_psf_path(filter_name, fwhm=self.get_fwhm(filter_name))

                # Set the PSF kernel path
                self.kernel_paths[filter_name] = psf_path

            # check whether we have a FWHM
            elif self.has_fwhm(filter_name):

                # Get the FWHM
                fwhm = self.fwhms[filter_name]

                # Set the FWHM
                if self.psf_fwhms is None: self.psf_fwhms = dict()
                self.psf_fwhms[filter_name] = fwhm

            # Variable FWHM?
            elif not has_variable_fwhm(filter_name):

                # Get the FWHM
                fwhm = get_fwhm(filter_name)

                # Set the FWHM
                if self.psf_fwhms is None: self.psf_fwhms = dict()
                self.psf_fwhms[filter_name] = fwhm

            # The FWHM is variable, but we have a good average value
            elif has_average_variable_fwhm(filter_name):

                # Get the average FWHM
                fwhm = get_average_variable_fwhm(filter_name)

                # Give warning
                log.warning("The FWHM for the '" + filter_name + "' is variable, but using the average value for this filter (Clark et al., 2017) ...")

                # Set the FWHM
                if self.psf_fwhms is None: self.psf_fwhms = dict()
                self.psf_fwhms[filter_name] = fwhm

            # No FWHM can be found
            else:
                #raise ValueError("")
                log.error("The FWHM for the '" + filter_name + "' could not be determined: convolution will not be performed")

    # -----------------------------------------------------------------

    def get_rebin_coordinate_systems(self, **kwargs):

        """
        This function ...
        :param kwargs:
        :return:
        """

        # Debugging
        log.debug("Getting rebin coordinate systems ...")

        # Rebin WCS paths
        if kwargs.get("rebin_wcs_paths", None) is not None:

            # Initialize dictionary
            self.rebin_coordinate_systems = dict()

            # Get the argument
            rebin_wcs_paths = kwargs.pop("rebin_wcs_paths")

            # WCS paths are defined per instrument
            if types.is_dictionary_of_dictionaries(rebin_wcs_paths):

                # Loop over the different instruments
                for instrument_name in rebin_wcs_paths:
                    wcs_dict = dict()
                    # Loop over the filter names
                    for filter_name in rebin_wcs_paths[instrument_name]:

                        # Load the wcs
                        wcs = CoordinateSystem.from_file(rebin_wcs_paths[instrument_name][filter_name])
                        wcs_dict[filter_name] = wcs

                    # Set the coordinate systems for this instrument
                    self.rebin_coordinate_systems[instrument_name] = wcs_dict

            # WCS paths are only defined per filter name
            elif types.is_dictionary(rebin_wcs_paths):

                # Check that rebin_instrument is specified
                rebin_instrument = kwargs.pop("rebin_instrument")

                # Initialize
                self.rebin_coordinate_systems = dict()
                self.rebin_coordinate_systems[rebin_instrument] = dict()

                # Load the coordinate systems
                for filter_name in self.filter_names:
                    wcs = CoordinateSystem.from_file(rebin_wcs_paths[filter_name])
                    self.rebin_coordinate_systems[rebin_instrument][filter_name] = wcs

        # Rebin WCS
        elif kwargs.get("rebin_wcs", None) is not None:

            # Check that rebin_instrument is specified
            rebin_instrument = kwargs.pop("rebin_instrument")

            # Initialize
            self.rebin_coordinate_systems = dict()
            self.rebin_coordinate_systems[rebin_instrument] = dict()

            # Load the coordinate systems
            rebin_wcs = kwargs.pop("rebin_wcs")
            for filter_name in self.filter_names:
                self.rebin_coordinate_systems[rebin_instrument][filter_name] = rebin_wcs

        # Rebin wcs path
        elif kwargs.get("rebin_wcs_path", None) is not None:

            # Check that rebin_instrument is specified
            rebin_instrument = kwargs.pop("rebin_instrument")

            # INitialize
            self.rebin_coordinate_systems = dict()
            self.rebin_coordinate_systems[rebin_instrument] = dict()

            # Load the wcs
            rebin_wcs_path = kwargs.pop("rebin_wcs_path")
            rebin_wcs = CoordinateSystem.from_file(rebin_wcs_path)

            # Set the coordinate systems
            for filter_name in self.filter_names:
                self.rebin_coordinate_systems[rebin_instrument][filter_name] = rebin_wcs

        # Rebin dataset
        elif kwargs.get("rebin_dataset", None) is not None:

            from ...magic.core.dataset import DataSet

            # Get the dataset
            dataset = kwargs.pop("rebin_dataset")
            if types.is_string_type(dataset): dataset = DataSet.from_file(dataset)

            # Check that rebin_instrument is specified
            rebin_instrument = kwargs.pop("rebin_instrument")

            # Initialize
            self.rebin_coordinate_systems = dict()
            self.rebin_coordinate_systems[rebin_instrument] = dict()

            # Loop over the filter names
            image_names_for_filters = dataset.get_names_for_filters(self.filter_names)
            for filter_name, image_name in zip(self.filter_names, image_names_for_filters):

                # Check whether there is such an image
                if image_name is None:
                    log.warning("There is no image in the dataset for the '" + filter_name + "' filter: skipping for rebinning ...")
                    continue

                # Get the coordinate system
                #wcs = dataset.get_coordinate_system_for_filter(filter_name, return_none=True)
                wcs = dataset.get_coordinate_system(image_name) # FASTER!
                # if wcs is None:
                #     log.warning("The coordinate system for the '" + filter_name + "' filter is not found in the dataset: skipping ...")
                #     continue

                # Set the coordinate system
                self.rebin_coordinate_systems[rebin_instrument][filter_name] = wcs

    # -----------------------------------------------------------------

    def get_host_id(self, **kwargs):

        """
        Thisf unction ...
        :param kwargs:
        :return:
        """

        # Debugging
        log.debug("Getting remote host ...")

        # Get the host ID
        self.host_id = kwargs.pop("host_id", None)

        # Remote spectral convolution flag
        self.remote_spectral_convolution = kwargs.pop("remote_spectral_convolution", False)

        # Remote threshold
        self.remote_threshold = kwargs.pop("remote_threshold", None)

        # Seperate rebin and convolve thresholds
        self.remote_rebin_threshold = kwargs.pop("remote_rebin_threshold", None)
        self.remote_convolve_threshold = kwargs.pop("remote_convolve_threshold", None)

    # -----------------------------------------------------------------

    def deploy_pts(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Deploying PTS remotely ...")

        # Create the deployer
        deployer = Deployer()

        # Don't do anything locally
        deployer.config.local = False

        # Only deploy PTS
        deployer.config.skirt = False
        deployer.config.pts = True

        # Set the host ids
        deployer.config.host_ids = [self.host_id]

        # Check versions between local and remote
        deployer.config.check = self.config.check_versions

        # Update PTS dependencies
        deployer.config.update_dependencies = self.config.update_dependencies

        # Do clean install
        #deployer.config.clean = self.config.deploy_clean

        # Pubkey pass
        #deployer.config.pubkey_password = self.config.pubkey_password

        # Run the deployer
        deployer.run()

    # -----------------------------------------------------------------

    def create_wavelength_grid(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Creating the wavelength grid ...")

        # Construct the wavelength grid from the array of wavelengths
        self.wavelength_grid = WavelengthGrid.from_wavelengths(self.wavelengths, "micron")

    # -----------------------------------------------------------------

    @lazyproperty
    def filters(self):

        """
        This function ...
        :return:
        """

        return {filter_name: parse_filter(filter_name) for filter_name in self.filter_names}

    # -----------------------------------------------------------------

    def filter_names_with_image_for_instrument(self, instr_name):

        """
        This function ...
        :param instr_name:
        :return:
        """

        return [filter_name for filter_name in self.filter_names if self.has_image(instr_name, filter_name)]

    # -----------------------------------------------------------------

    def filters_with_image_for_instrument(self, instr_name):

        """
        This function ...
        :param instr_name:
        :return:
        """

        return {filter_name: parse_filter(filter_name) for filter_name in self.filter_names_with_image_for_instrument(instr_name)}

    # -----------------------------------------------------------------

    def filter_names_without_image_for_instrument(self, instr_name):

        """
        This function ...
        :param instr_name:
        :return:
        """

        return [filter_name for filter_name in self.filter_names if not self.has_image(instr_name, filter_name)]

    # -----------------------------------------------------------------

    def filters_without_image_for_instrument(self, instr_name):

        """
        Thisf unction ...
        :param instr_name:
        :return:
        """

        return {filter_name: parse_filter(filter_name) for filter_name in self.filter_names_without_image_for_instrument(instr_name)}

    # -----------------------------------------------------------------

    @lazyproperty
    def total_datacube_paths(self):

        """
        Thisn function ...
        :return:
        """

        paths = []
        for path in self.fits_paths:
            if not is_total_datacube(path): continue
            paths.append(path)
        return paths

    # -----------------------------------------------------------------

    def needs_remote(self, path):

        """
        This function ...
        :return:
        """

        # No remote is set
        if self.host_id is None: return False

        # File size is exceeded
        if self.remote_threshold is not None and fs.file_size(path) > self.remote_threshold: return True

        # Remote spectral convolution
        if self.has_spectral_convolution_filters and self.remote_spectral_convolution: return True

        # Not remote
        return False

    # -----------------------------------------------------------------

    def load_datacubes(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Loading the SKIRT output datacubes ...")

        # Loop over the different simulated TOTAL datacubes
        for path in self.total_datacube_paths:

            # Get the name of the instrument
            instr_name = instrument_name(path, self.simulation_prefix)

            # If a list of instruments is defined an this instrument is not in this list, skip it
            if self.instrument_names is not None and instr_name not in self.instrument_names: continue

            # Check if already present
            if self.has_all_images(instr_name):
                if self.config.regenerate: self.remove_all_images(instr_name)
                else:
                    log.success("All images for the '" + instr_name + "' have already been created: skipping ...")
                    continue

            # Debugging
            log.debug("Loading total datacube of '" + instr_name + "' instrument from '" + path + "' ...")

            # Load datacube remotely
            if self.needs_remote(path): datacube = self.load_datacube_remote(path)

            # Load datacube locally
            else: datacube = self.load_datacube_local(path)

            # If datacube is None, something went wrong, skip the datacube
            if datacube is None: continue

            # Convert the datacube from neutral flux density to wavelength flux density
            datacube.to_wavelength_density("W / (m2 * arcsec2 * micron)", "micron")

            # Add the datacube to the dictionary
            self.datacubes[instr_name] = datacube

    # -----------------------------------------------------------------

    def load_datacube_local(self, path):

        """
        Thisj function ...
        :param self:
        :param path:
        :return:
        """

        # Debugging
        log.debug("Trying to load the datacube '" + path + "' locally ...")

        # Load
        try: datacube = DataCube.from_file(path, self.wavelength_grid)
        except fits.DamagedFITSFileError as e:
            log.error("The datacube '" + path + "' is damaged: images cannot be created. Skipping this datacube ...")
            datacube = None

        # Return the datacube
        return datacube

    # -----------------------------------------------------------------

    def load_datacube_remote(self, path):

        """
        This function ...
        :param self:
        :param path:
        :return:
        """

        # Debugging
        log.debug("Trying to load the datacube '" + path + "' remotely ...")

        # Load
        try: datacube = RemoteDataCube.from_file(path, self.wavelength_grid, self.session)
        except fits.DamagedFITSFileError as e:
            log.error("The datacube '" + path + "' is damaged: images cannot be created. Skipping this datacube ...")
            datacube = None

        # Return
        return datacube

    # -----------------------------------------------------------------

    def set_coordinate_systems(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Setting the WCS of the simulated images ...")

        # Loop over the different datacubes and set the WCS
        for instr_name in self.datacubes:

            # Check whether coordinate system is defined for this instrument
            if instr_name not in self.coordinate_systems: continue

            # Debugging
            log.debug("Setting the coordinate system of the '" + instr_name + "' instrument ...")

            # Set the coordinate system for this datacube
            self.datacubes[instr_name].wcs = self.coordinate_systems[instr_name]

    # -----------------------------------------------------------------

    @lazyproperty
    def spectral_convolution_filters(self):

        """
        This function ...
        :return:
        """

        # No spectral convolution for any filter
        if not self.config.spectral_convolution: return []

        # Initialize list
        filters = []

        # Loop over the filters
        for fltr in self.filters:

            if fltr in self.no_spectral_convolution_filters: pass
            else: filters.append(fltr)

        # Return the list of filters
        return filters

    # -----------------------------------------------------------------

    @lazyproperty
    def nspectral_convolution_filters(self):

        """
        This function ...
        :return:
        """

        return len(self.spectral_convolution_filters)

    # -----------------------------------------------------------------

    @property
    def has_spectral_convolution_filters(self):

        """
        This function ...
        :return:
        """

        return self.nspectral_convolution_filters > 0

    # -----------------------------------------------------------------

    def remote_intermediate_initial_path_for_image(self, instr_name, filter_name):

        """
        This function ...
        :param instr_name:
        :param filter_name:
        :return:
        """

        return fs.join(self.remote_intermediate_initial_path, instr_name + "__" + filter_name + ".fits")

    # -----------------------------------------------------------------

    def intermediate_initial_path_for_image(self, instr_name, filter_name):

        """
        This function ...
        :param instr_name:
        :param filter_name:
        :return:
        """

        return fs.join(self.intermediate_initial_path, instr_name + "__" + filter_name + ".fits")

    # -----------------------------------------------------------------

    def make_images(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Making the observed images (this may take a while) ...")

        from ...magic.core.remote import RemoteFrame
        from ...magic.core.frame import Frame

        # Loop over the datacubes
        for instr_name in self.datacubes:

            # Debugging
            log.debug("Making the observed images for the " + instr_name + " instrument ...")

            # Get the filters that don't have an image (end result) yet saved on disk
            filters_dict = self.filters_without_image_for_instrument(instr_name)

            # Get filters list and filter names list
            filter_names = filters_dict.keys()
            filters = filters_dict.values()

            # Initialize a dictionary, indexed by the filter names, to contain the images
            images = dict()

            # Get the datacube
            datacube = self.datacubes[instr_name]

            # Check for which filters an initial image is already present
            make_filter_names = []
            make_filters = []
            for filter_name, fltr in zip(filter_names, filters):

                # Remote datacube
                if isinstance(datacube, RemoteDataCube):
                    path = self.remote_intermediate_initial_path_for_image(instr_name, filter_name)
                    if self.remote.is_file(path):
                        # Success
                        log.success("Initial '" + filter_name + "' image from the '" + instr_name + "' instrument is found in the remote directory '" + self.remote_intermediate_initial_path + "': not making it again")
                        # Load as remote frame
                        frame = RemoteFrame.from_remote_file(path, self.session)
                        # Add to the dictionary of initial images
                        images[filter_name] = frame
                    else:
                        make_filter_names.append(filter_name)
                        make_filters.append(fltr)

                # Regular datacube
                elif isinstance(datacube, DataCube):
                    path = self.intermediate_initial_path_for_image(instr_name, filter_name)
                    if fs.is_file(path):
                        # Success
                        log.success("Initial '" + filter_name + "' image from the '" + instr_name + "' instrument is found in the directory '" + self.intermediate_initial_path + "': not making it again")
                        # Load as frame
                        frame = Frame.from_file(path)
                        # Add to the dictionary of initial images
                        images[filter_name] = frame
                    else:
                        make_filter_names.append(filter_name)
                        make_filters.append(fltr)

                # Invalid
                else: raise ValueError("Something went wrong")

            # Determine the number of processes
            if not self.has_spectral_convolution_filters: nprocesses = 1
            else:
                if isinstance(datacube, RemoteDataCube): nprocesses = self.config.nprocesses_remote
                elif isinstance(datacube, DataCube): nprocesses = self.config.nprocesses_local
                else: raise ValueError("Invalid datacube object for '" + instr_name + "' instrument")

            # Limit the number of processes to the number of filters
            nprocesses = min(len(make_filters), nprocesses)

            # Create the observed images from the current datacube (the frames get the correct unit, wcs, filter)
            frames = self.datacubes[instr_name].frames_for_filters(make_filters, convolve=self.spectral_convolution_filters, nprocesses=nprocesses, check_previous_sessions=True)

            # Add the observed images to the dictionary
            for filter_name, frame in zip(make_filter_names, frames): images[filter_name] = frame # these frames can be RemoteFrames if the datacube was a RemoteDataCube

            # Add the observed image dictionary for this datacube to the total dictionary (with the datacube name as a key)
            self.images[instr_name] = images

            # Save intermediate results
            if self.config.write_intermediate:

                # Loop over the images
                for filter_name in self.images[instr_name]:

                    # If the image didn't need to be made, it means it was already saved
                    if filter_name not in make_filter_names: continue

                    # Remote frame?
                    frame = self.images[instr_name][filter_name]
                    if isinstance(frame, RemoteFrame):

                        # Determine the path
                        path = self.remote_intermediate_initial_path_for_image(instr_name, filter_name)

                        # Save the frame remotely
                        frame.saveto_remote(path)

                    # Regular frame?
                    elif isinstance(frame, Frame):

                        # Determine the path
                        path = self.intermediate_initial_path_for_image(instr_name, filter_name)

                        # Save the frame
                        frame.saveto(path)

                    # Invalid
                    else: raise ValueError("Something went wrong")

    # -----------------------------------------------------------------

    def remote_intermediate_convolve_path_for_image(self, instr_name, filter_name):

        """
        This function ...
        :param instr_name:
        :param filter_name:
        :return:
        """

        return fs.join(self.remote_intermediate_convolve_path, instr_name + "__" + filter_name + ".fits")

    # -----------------------------------------------------------------

    def intermediate_convolve_path_for_image(self, instr_name, filter_name):

        """
        This function ...
        :param instr_name:
        :param filter_name:
        :return:
        """

        return fs.join(self.intermediate_convolve_path, instr_name + "__" + filter_name + ".fits")

    # -----------------------------------------------------------------

    def has_kernel_path(self, filter_name):

        """
        This function ...
        :param filter_name:
        :return:
        """

        if not self.has_kernel_paths: return False

        # Check if the name of the image filter is a key in the 'kernel_paths' dictionary. If not, don't convolve.
        return filter_name in self.kernel_paths and self.kernel_paths[filter_name] is not None

    # -----------------------------------------------------------------

    def has_psf_fwhm(self, filter_name):

        """
        This function ...
        :param filter_name:
        :return:
        """

        if not self.has_psf_fwhms: return False

        # Check
        return filter_name in self.psf_fwhms and self.psf_fwhms[filter_name] is not None

    # -----------------------------------------------------------------

    def get_fwhm_for_filter(self, filter_name):

        """
        Thisf unction ...
        :param filter_name:
        :return:
        """

        # Has FWHM defined
        if self.has_fwhm(filter_name): return self.fwhms[filter_name]

        # Has kernel
        if self.has_kernel_path(filter_name): fwhm = get_kernel_fwhm(self.kernel_paths[filter_name])

        # Has FWHM
        elif self.has_psf_fwhm(filter_name): fwhm = self.psf_fwhms[filter_name]

        # Error
        else: raise RuntimeError("Something went wrong")

        # Return the FWHM
        return fwhm

    # -----------------------------------------------------------------

    def kernel_path_for_image(self, instr_name, filter_name):

        """
        Thisf unction ...
        :param instr_name:
        :param filter_name:
        :return:
        """

        return fs.join(self.kernels_path, instr_name + "__" + filter_name + ".fits")

    # -----------------------------------------------------------------

    def get_fwhm(self, filter_name):

        """
        This function ...
        :param filter_name:
        :return:
        """

        if not self.has_fwhm(filter_name): return None
        else: return self.fwhms[filter_name]

    # -----------------------------------------------------------------

    def get_kernel_for_filter(self, filter_name, pixelscale):

        """
        This function ...
        :param filter_name:
        :param pixelscale:
        :return:
        """

        # Debugging
        log.debug("Loading the convolution kernel for the '" + filter_name + "' filter ...")

        # Get the kernel
        if self.has_kernel_path(filter_name): kernel = ConvolutionKernel.from_file(self.kernel_paths[filter_name], fwhm=self.get_fwhm(filter_name))

        # Get the PSF kernel
        elif self.has_psf_fwhm(filter_name): kernel = create_psf_kernel(self.psf_fwhms[filter_name], pixelscale)

        # Error
        else: raise RuntimeError("Something went wrong")

        # SET FWHM IF UNDEFINED
        if kernel.fwhm is None:
            if self.has_fwhm(filter_name): kernel.fwhm = self.fwhms[filter_name]
            else: log.warning("The FWHM of the convolution kernel for the '" + filter_name + "' image is undefined")

        # Return the kernel
        return kernel

    #  -----------------------------------------------------------------

    def convolve(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Convolving the images ...")

        from ...magic.core.remote import RemoteFrame
        from ...magic.core.frame import Frame

        # Loop over the images
        for instr_name in self.images:

            # Debugging
            log.debug("Convolving images from the '" + instr_name + "' instrument ...")

            # Loop over the filters
            for filter_name in self.images[instr_name]:

                # Check if the name of the image filter is a key in the 'kernel_paths' dictionary. If not, don't convolve.
                if not self.has_kernel_path(filter_name) and not self.has_psf_fwhm(filter_name):

                    # Debugging
                    log.debug("The filter '" + filter_name + "' is not in the kernel paths nor is PSF FWHM defined: no convolution")
                    continue

                # Check whether the end result is already there
                if self.has_image(instr_name, filter_name):
                    log.success("The result for the '" + filter_name + "' image from the '" + instr_name + "' instrument is already present: skipping convolution ...")
                    continue

                # Get the frame
                frame = self.images[instr_name][filter_name]

                # Check whether intermediate result is there
                # Remote frame?
                if isinstance(frame, RemoteFrame):
                    # Get path
                    path = self.remote_intermediate_convolve_path_for_image(instr_name, filter_name)
                    if self.remote.is_file(path):
                        # Success
                        log.success("Convolved '" + filter_name + "' image from the '" + instr_name + "' instrument is found in remote directory '" + self.remote_intermediate_convolve_path + "': not making it again")
                        # Load as remote frame
                        frame = RemoteFrame.from_remote_file(path, self.session)
                        # Replace the frame by the convolved frame
                        self.images[instr_name][filter_name] = frame
                        # Skip
                        continue
                    else: pass # go on

                # Regular frame?
                elif isinstance(frame, Frame):
                    # Get path
                    path = self.intermediate_convolve_path_for_image(instr_name, filter_name)
                    if fs.is_file(path):
                        # Success
                        log.success("Convolved '" + filter_name + "' image from the '" + instr_name + "' instrument is found in directory '" + self.intermediate_convolve_path + "': not making it again")
                        # Load as frame
                        frame = Frame.from_file(path)
                        # Replace the frame by the convolved frame
                        self.images[instr_name][filter_name] = frame
                        # Skip
                        continue
                    else: pass # go on

                # Invalid
                else: raise RuntimeError("Something went wrong")

                # Check whether the pixelscale is defined
                pixelscale = self.images[instr_name][filter_name].pixelscale
                if pixelscale is None: raise ValueError("Pixelscale of the '" + filter_name + "' image of the '" + instr_name + "' datacube is not defined, convolution not possible")

                # Get kernel for this filter
                #kernel = self.get_kernel_for_filter(filter_name, pixelscale)

                # CHECK THE RATIO BETWEEN FWHM AND PIXELSCALE
                target_fwhm = self.get_fwhm_for_filter(filter_name)
                if target_fwhm is None: raise ValueError("The FWHM cannot be determined for the '" + filter_name + "' image")
                if target_fwhm > self.config.max_fwhm_pixelscale_ratio * pixelscale.average:

                    # GIVE WARNING
                    log.warning("The target FWHM (" + tostr(target_fwhm) + ") is greater than " + tostr(self.config.max_fwhm_pixelscale_ratio) + " times the pixelscale of the image (" + tostr(pixelscale.average) + ")")
                    log.warning("Downsampling the image to a more reasonable pixelscale prior to convolution ...")

                    # Get the original FWHM to pixelscale ratio
                    original_fwhm_pixelscale_ratio = (target_fwhm / pixelscale.average).to("").value

                    # When rebinning has to be performed, check the
                    if self.needs_rebinning(instr_name, filter_name):

                        # Get the target coordinate system
                        target_wcs = self.rebin_coordinate_systems[instr_name][filter_name]

                        # Get the target pixelscale
                        target_pixelscale = target_wcs.average_pixelscale
                        target_downsample_factor = (target_pixelscale / pixelscale.average).to("").value

                        # Get the target FWHM to pixelscale ratio
                        target_fwhm_pixelscale_ratio = (target_fwhm / target_pixelscale).to("").value

                        # Get the geometric mean between original and target ratios
                        ratio = numbers.geometric_mean(original_fwhm_pixelscale_ratio, target_fwhm_pixelscale_ratio)

                        # Translate this ratio into a pixelscale
                        new_pixelscale = target_fwhm / ratio

                        # Determine the downsample factor
                        downsample_factor = (new_pixelscale / pixelscale.average).to("").value
                        downsample_factor = numbers.nearest_even_integer_below(downsample_factor, below=target_downsample_factor)

                    # No rebinning: we can freely choose the downsampling factor
                    else:

                        # Define the ideal FWHM to pixelscale ratio
                        ideal_fwhm_pixelscale_ratio = 25

                        # Translate this ratio into a pixelscale
                        ideal_pixelscale = target_fwhm / ideal_fwhm_pixelscale_ratio

                        # Determine the downsample factor
                        downsample_factor = (ideal_pixelscale / pixelscale.average).to("").value
                        downsample_factor = numbers.nearest_even_integer(downsample_factor)

                    # Debugging
                    log.debug("The downsampling factor is " + tostr(downsample_factor))

                    # DOWNSAMPLE
                    self.images[instr_name][filter_name].downsample(downsample_factor)

                    # Re-determine the pixelscale
                    pixelscale = self.images[instr_name][filter_name].pixelscale

                # Determine the path to save the kernel
                saved_kernel_path = self.kernel_path_for_image(instr_name, filter_name)

                # Exists? -> load the kernel from file
                if fs.is_file(saved_kernel_path):

                    # Success
                    log.success("Kernel file for the '" + filter_name + "' of the '" + instr_name + "' instrument is found in directory '" + self.intermediate_rebin_path + "'")

                    # Load the kernel
                    kernel = ConvolutionKernel.from_file(saved_kernel_path)

                # Create or get the kernel
                else:

                    # Get the kernel
                    kernel = self.get_kernel_for_filter(filter_name, pixelscale)

                    # Write the kernel
                    if self.config.write_kernels: kernel.saveto(saved_kernel_path)

                # Debugging
                log.debug("Convolving the '" + filter_name + "' image of the '" + instr_name + "' instrument ...")

                # Convert into remote frame if necessary
                if self.remote_convolve_threshold is not None and isinstance(frame, Frame) and frame.data_size > self.remote_convolve_threshold:

                    # Convert into remote
                    self.images[instr_name][filter_name] = RemoteFrame.from_local(frame, self.session)

                # Convolve the frame
                self.images[instr_name][filter_name].convolve(kernel)

                # If intermediate results have to be written
                if self.config.write_intermediate:

                    # Remote frame?
                    frame = self.images[instr_name][filter_name]
                    if isinstance(frame, RemoteFrame):

                        # Determine the path
                        path = self.remote_intermediate_convolve_path_for_image(instr_name, filter_name)

                        # Save the frame remotely
                        frame.saveto_remote(path)

                    # Regular frame?
                    elif isinstance(frame, Frame):

                        # Determine the path
                        path = self.intermediate_convolve_path_for_image(instr_name, filter_name)

                        # Save the frame locally
                        frame.saveto(path)

                    # Invalid
                    else: raise ValueError("Something went wrong")

    # -----------------------------------------------------------------

    def remote_intermediate_rebin_path_for_image(self, instr_name, filter_name):

        """
        Thisnf unction ...
        :param instr_name:
        :param filter_name:
        :return:
        """

        return fs.join(self.remote_intermediate_rebin_path, instr_name + "__" + filter_name + ".fits")

    # -----------------------------------------------------------------

    def intermediate_rebin_path_for_image(self, instr_name, filter_name):

        """
        This function ...
        :param instr_name:
        :param filter_name:
        :return:
        """

        return fs.join(self.intermediate_rebin_path, instr_name + "__" + filter_name + ".fits")

    # -----------------------------------------------------------------

    def needs_rebinning(self, instr_name, filter_name):

        """
        This function ...
        :param instr_name:
        :param filter_name:
        :return:
        """

        # Check if the name of the datacube appears in the rebin_wcs dictionary
        if instr_name not in self.rebin_coordinate_systems: return False

        # Check if the name of the image appears in the rebin_wcs[datacube_name] sub-dictionary
        if filter_name not in self.rebin_coordinate_systems[instr_name]: return False

        # Target coordinate system for rebinning is defined
        return True

    # -----------------------------------------------------------------

    def rebin(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Rebinning the images to the requested coordinate systems ...")

        from ...magic.core.remote import RemoteFrame
        from ...magic.core.frame import Frame

        # Loop over the datacubes
        for instr_name in self.images:

            # Check if the name of the datacube appears in the rebin_wcs dictionary
            if instr_name not in self.rebin_coordinate_systems:

                # Debugging
                log.debug("The instrument '" + instr_name + "' is not in the rebin coordinate systems: no rebinning")
                continue

            # Debugging
            log.debug("Rebinning images from the '" + instr_name + "' instrument ...")

            # Loop over the filters
            for filter_name in self.images[instr_name]:

                # Check if the name of the image appears in the rebin_wcs[datacube_name] sub-dictionary
                if filter_name not in self.rebin_coordinate_systems[instr_name]:

                    # Debugging
                    log.debug("The filter '" + filter_name + "' is not in the rebin coordinate systems for this instrument: no rebinning")
                    continue

                # Check whether the end result is already there
                if self.has_image(instr_name, filter_name):
                    log.success("The result for the '" + filter_name + "' image from the '" + instr_name + "' instrument is already present: skipping rebinning ...")
                    continue

                # Get the frame
                frame = self.images[instr_name][filter_name]

                # Check whether intermediate result is there
                # Remote frame?
                if isinstance(frame, RemoteFrame):
                    # Get path
                    path = self.remote_intermediate_rebin_path_for_image(instr_name, filter_name)
                    if self.remote.is_file(path):
                        # Success
                        log.success("Rebinned '" + filter_name + "' image from the '" + instr_name + "' instrument is found in remote directory '" + self.remote_intermediate_rebin_path + "': not making it again")
                        # Load as remote frame
                        frame = RemoteFrame.from_remote_file(path, self.session)
                        # Replace the frame by the rebinned frame
                        self.images[instr_name][filter_name] = frame
                        # Skip
                        continue
                    else: pass # go on
                # Regular frame
                elif isinstance(frame, Frame):
                    # Get path
                    path = self.intermediate_rebin_path_for_image(instr_name, filter_name)
                    if fs.is_file(path):
                        # Success
                        log.success("Rebinned '" + filter_name + "' image from the '" + instr_name + "' instrument is found in directory '" + self.intermediate_rebin_path + "': not making it again")
                        # Load as frame
                        frame = Frame.from_file(path)
                        # Replace the frame by the rebinned frame
                        self.images[instr_name][filter_name] = frame
                        # Skip
                        continue
                    else: pass # go on

                # Invalid
                else: raise RuntimeError("Something went wrong")

                # Get target WCS
                wcs = self.rebin_coordinate_systems[instr_name][filter_name]

                # CHECK THE PIXELSCALES
                if not self.config.upsample and wcs.average_pixelscale < self.images[instr_name][filter_name].average_pixelscale:

                    # Give warning that rebinning will not be performed
                    log.warning("Rebinning will not be peformed for the '" + filter_name + "' image of the '" + instr_name + "' instrument since the target pixelscale is smaller than the current pixelscale")

                    # Skip the rebin step for this image
                    continue

                # Debugging
                log.debug("Rebinning the '" + filter_name + "' image of the '" + instr_name + "' instrument ...")

                # Get the original unit
                original_unit = self.images[instr_name][filter_name].unit
                converted = False

                # Check if this is a surface brightness or intensity
                if not (original_unit.is_intensity or original_unit.is_surface_brightness):

                    # Determine the new (surface brightness or intensity) unit
                    #new_unit = original_unit / u("sr")
                    new_unit = original_unit.corresponding_angular_area_unit

                    # Debugging
                    log.debug("Converting the unit from '" + str(original_unit) + "' to '" + str(new_unit) + "' in order to be able to perform rebinning ...")

                    # Convert
                    self.images[instr_name][filter_name].convert_to(new_unit)
                    converted = True

                # Convert to remote frame if necessary
                if self.remote_rebin_threshold is not None and isinstance(frame, Frame) and frame.data_size > self.remote_rebin_threshold:

                    # Convert
                    self.images[instr_name][filter_name] = RemoteFrame.from_local(frame, self.session)

                # Rebin
                self.images[instr_name][filter_name].rebin(wcs)

                # Convert the unit back
                if converted: self.images[instr_name][filter_name].convert_to(original_unit)

                # If intermediate results have to be written
                if self.config.write_intermediate:

                    # Remote frame?
                    frame = self.images[instr_name][filter_name]
                    if isinstance(frame, RemoteFrame):

                        # Determine the path
                        path = self.remote_intermediate_rebin_path_for_image(instr_name, filter_name)

                        # Save the frame remotely
                        frame.saveto_remote(path)

                    # Regular frame?
                    elif isinstance(frame, Frame):

                        # Determine the path
                        path = self.intermediate_rebin_path_for_image(instr_name, filter_name)

                        # Save the frame
                        frame.saveto(path)

                    # Invalid
                    else: raise ValueError("Something went wrong")

    # -----------------------------------------------------------------

    def add_sky(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Adding artificial sky contribution to the images ...")

    # -----------------------------------------------------------------

    def add_stars(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Adding artificial stars to the images ...")

    # -----------------------------------------------------------------

    def convert_units(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Converting the units of the images to " + str(self.unit) + " ...")

        # Loop over the instruments
        for instr_name in self.images:

            # Loop over the images for this instrument
            for filter_name in self.images[instr_name]:

                # Debugging
                log.debug("Converting the unit of the " + filter_name + " image of the '" + instr_name + "' instrument ...")

                # Convert
                factor = self.images[instr_name][filter_name].convert_to(self.unit)

                # Debugging
                log.debug("The conversion factor is '" + str(factor) + "'")

    # -----------------------------------------------------------------

    def write(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Writing the images ...")

        # Write (grouped or not)
        if self.config.group: self.write_images_grouped()
        else: self.write_images()

    # -----------------------------------------------------------------

    def has_all_images(self, instr_name):

        """
        Thisf unction ...
        :param instr_name:
        :return:
        """

        # Loop over all filter names
        for filter_name in self.filter_names:
            if not self.has_image(instr_name, filter_name): return False

        # All checks passed
        return True

    # -----------------------------------------------------------------

    def has_image(self, instr_name, filter_name):

        """
        This function ...
        :param instr_name:
        :param filter_name:
        :return:
        """

        path = self.get_image_path(instr_name, filter_name)
        return fs.is_file(path) and fits.is_valid(path)

    # -----------------------------------------------------------------

    def remove_all_images(self, instr_name):

        """
        This function ...
        :param instr_name:
        :return:
        """

        # Loop over the filters
        for filter_name in self.filter_names:

            # Get path
            path = self.get_image_path(instr_name, filter_name)

            # Remove if existing
            fs.remove_file_if_present(path)

    # -----------------------------------------------------------------

    def remove_image(self, instr_name, filter_name):

        """
        This function ...
        :param instr_name:
        :param filter_name:
        :return:
        """

        # Determine the path
        path = self.get_image_path(instr_name, filter_name)

        # Remove if existing
        fs.remove_file_if_present(path)

    # -----------------------------------------------------------------

    def get_image_path(self, instr_name, filter_name):

        """
        This function ...
        :param instr_name:
        :param filter_name:
        :return:
        """

        # Group per instrument
        if self.config.group:

            # Determine path for instrument directory (and create)
            instrument_path = self.output_path_directory(instr_name, create=True)

            # Return the filepath
            return fs.join(instrument_path, filter_name + ".fits")

        # Don't group
        else: return self.output_path_file(instr_name + "__" + filter_name + ".fits")

    # -----------------------------------------------------------------

    def write_images_grouped(self):

        """
        This function ...
        :return:
        """

        # Loop over the different instruments (datacubes)
        for instr_name in self.images.keys(): # explicit keys to avoid error that dict changed

            # Loop over the images for this instrument
            for filter_name in self.images[instr_name].keys(): # explicit keys to avoid error that dict changed

                # Determine path to the output FITS file
                path = self.get_image_path(instr_name, filter_name)

                # Save the image
                self.images[instr_name][filter_name].saveto(path)

                # Remove from memory?
                del self.images[instr_name][filter_name]

                # Set the path
                self.paths[instr_name][filter_name] = path

            # Cleanup?
            gc.collect()

    # -----------------------------------------------------------------

    def write_images(self):

        """
        This function ...
        :return:
        """

        # Loop over the different images (self.images is a nested dictionary of dictionaries)
        for instr_name in self.images.keys(): # explicit keys to avoid error that dict changed

            # Loop over the images for this instrument
            for filter_name in self.images[instr_name].keys(): # explicit keys to avoid error that dict changed

                # Determine the path to the output FITS file
                path = self.get_image_path(instr_name, filter_name)

                # Save the image
                self.images[instr_name][filter_name].saveto(path)

                # Remove from memory?
                del self.images[instr_name][filter_name]

                # Set the path
                self.paths[instr_name][filter_name] = path

            # Cleanup?
            gc.collect()

    # -----------------------------------------------------------------

    def clear(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Clearing intermediate results ...")

        # TODO

# -----------------------------------------------------------------

def is_total_datacube(datacube_path):

    """
    This function ...
    :param datacube_path:
    :return:
    """

    name = fs.strip_extension(fs.name(datacube_path))
    if name.endswith("_total"): return True
    else: return False

# -----------------------------------------------------------------

def instrument_name(datacube_path, prefix):

    """
    This function ...
    :param datacube_path:
    :param prefix:
    :return:
    """

    return fs.name(datacube_path).split("_total.fits")[0].split(prefix + "_")[1]

# -----------------------------------------------------------------

def create_psf_kernel(fwhm, pixelscale, fltr=None, sigma_level=5.0):

    """
    This function ...
    :param fwhm:
    :param pixelscale:
    :param fltr:
    :param sigma_level:
    :return:
    """

    from astropy.convolution import Gaussian2DKernel
    from pts.magic.tools import statistics

    # Debugging
    log.debug("Creating a PSF kernel for a FWHM of " + tostr(fwhm) + " and a pixelscale of " + tostr(pixelscale.average) + ", cut-off at a sigma level of " + tostr(sigma_level) + " ...")

    # Get FWHM in pixels
    fwhm_pix = (fwhm / pixelscale.average).to("").value

    # Get the sigma in pixels
    sigma_pix = fwhm_pix * statistics.fwhm_to_sigma

    # DETERMINE THE ODD!! KERNEL SIZE
    kernel_size = int(round(2.0 * sigma_level))
    if numbers.is_even(kernel_size): kernel_size += 1

    # Debugging
    log.debug("The size for the kernel image is " + str(kernel_size) + " pixels")

    # Create a kernel
    kernel = Gaussian2DKernel(sigma_pix, x_size=kernel_size, y_size=kernel_size)
    kernel.normalize()  # to suppress warning

    # Create convolution kernel object
    kernel = ConvolutionKernel(kernel.array, to_filter=fltr, prepared=True, fwhm=fwhm, pixelscale=pixelscale)

    # Return the kernel
    return kernel

# -----------------------------------------------------------------
