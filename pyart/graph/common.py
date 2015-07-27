"""
pyart.graph.common
==================

Common graphing routines.

.. autosummary::
    :toctree: generated/

    dms_to_d
    radar_coords_to_cart
    corner_to_point
    ax_radius
    sweep_coords_to_cart
    _interpolate_range_edges
    _interpolate_elevation_edges
    _interpolate_azimuth_edges

"""

import numpy as np

PI = 3.141592653589793

from ..io.common import dms_to_d, radar_coords_to_cart


def corner_to_point(corner, point):
    """
    Return the x, y distances in meters from a corner to a point.

    Assumes a spherical earth model.

    Parameters
    ----------
    corner : (float, float)
        Latitude and longitude in degrees of the corner.
    point : (float, float)
        Latitude and longitude in degrees of the point.

    Returns
    -------
    x, y : floats
        Distances from the corner to the point in meters.

    """
    Re = 6371.0 * 1000.0
    Rc = ax_radius(point[0], units='degrees')
    #print Rc/Re
    y = ((point[0] - corner[0]) / 360.0) * PI * 2.0 * Re
    x = ((point[1] - corner[1]) / 360.0) * PI * 2.0 * Rc
    return x, y


def ax_radius(lat, units='radians'):
    """
    Return the radius of a constant latitude circle for a given latitude.

    Parameters
    ----------
    lat : float
        Latitude at which to calculate constant latitude circle (parallel)
        radius.
    units : 'radians' or 'degrees'
        Units of lat, either 'radians' or 'degrees'.

    Returns
    -------
    R : float
        Radius in meters of a constant latitude circle (parallel).

    """
    Re = 6371.0 * 1000.0
    if units == 'degrees':
        const = PI / 180.0
    else:
        const = 1.0
    R = Re * np.sin(PI / 2.0 - abs(lat * const))
    return R


def sweep_coords_to_cart(ranges, azimuths, elevations, edges=False):
    """
    Calculate Cartesian coordinate for the gates in a single radar sweep.

    Calculates the Cartesian coordinates for the gate centers or edges for
    all gates in a single sweep assuming a standard atmosphere (4/3 Earth's
    radius model). See :py:func:`pyart.io.common.radar_coords_to_cart` for
    details.

    Parameters
    ----------
    ranges : array, 1D.
        Distances to the center of the radar gates (bins) in meters.
    azimuths : array, 1D.
        Azimuth angles of the sweep in degrees.
    elevations : array, 1D.
        Elevation angles of the sweep in degrees.
    edges : bool, optional
        True to calculate the coordinates of the gate edges by interpolating
        between gates and extrapolating at the boundaries.  False to
        calculate the gate centers.

    Returns
    -------
    x, y, z : array, 2D
        Cartesian coordinates in meters from the center of the radar to the
        gate centers or edges.

    """
    if edges:
        if len(ranges) != 1:
            ranges = _interpolate_range_edges(ranges)
        if len(elevations) != 1:
            elevations = _interpolate_elevation_edges(elevations)
        if len(azimuths) != 1:
            azimuths = _interpolate_azimuth_edges(azimuths)
    rg, azg = np.meshgrid(ranges, azimuths)
    rg, eleg = np.meshgrid(ranges, elevations)
    return radar_coords_to_cart(rg / 1000., azg, eleg)


def _interpolate_range_edges(ranges):
    """ Interpolate the edges of the range gates from their centers. """
    edges = np.empty((ranges.shape[0] + 1, ), dtype=ranges.dtype)
    edges[1:-1] = (ranges[:-1] + ranges[1:]) / 2.
    edges[0] = ranges[0] - (ranges[1] - ranges[0]) / 2.
    edges[-1] = ranges[-1] - (ranges[-2] - ranges[-1]) / 2.
    edges[edges < 0] = 0    # do not allow range to become negative
    return edges


def _interpolate_elevation_edges(elevations):
    """ Interpolate the edges of the elevation angles from their centers. """
    edges = np.empty((elevations.shape[0]+1, ), dtype=elevations.dtype)
    edges[1:-1] = (elevations[:-1] + elevations[1:]) / 2.
    edges[0] = elevations[0] - (elevations[1] - elevations[0]) / 2.
    edges[-1] = elevations[-1] - (elevations[-2] - elevations[-1]) / 2.
    edges[edges > 180] = 180.   # prevent angles from going below horizon
    edges[edges < 0] = 0.
    return edges


def _interpolate_azimuth_edges(azimuths):
    """ Interpolate the edges of the azimuth angles from their centers. """
    edges = np.empty((azimuths.shape[0]+1, ), dtype=azimuths.dtype)
    # perform interpolation and extrapolation in complex plane to
    # account for periodic nature of azimuth angle.
    az = np.exp(1.j*np.deg2rad(azimuths))
    edges[1:-1] = np.angle((az[1:] + az[:-1]) / 2., deg=True)
    edges[0] = np.angle(az[0] - (az[1] - az[0]) / 2., deg=True)
    edges[-1] = np.angle(az[-1] - (az[-2] - az[-1]) / 2., deg=True)
    edges[edges < 0] += 360     # range from [-180, 180] to [0, 360]
    return edges

########################
# Common radar methods #
########################

def parse_ax(ax):
    """ Parse and return ax parameter. """
    if ax is None:
        ax = plt.gca()
    return ax

def parse_ax_fig(ax, fig):
    """ Parse and return ax and fig parameters. """
    if ax is None:
        ax = plt.gca()
    if fig is None:
        fig = plt.gcf()
    return ax, fig

def generate_colorbar_label(standard_name, units):
    """ Generate and return a label for a colorbar. """
    return standard_name.replace('_', ' ') + ' (' + units + ')'

def generate_field_name(radar, field):
    """ Return a nice field name for a particular field. """
    if 'standard_name' in radar.fields[field]:
        field_name = radar.fields[field]['standard_name']
    elif 'long_name' in radar.fields[field]:
        field_name = radar.fields[field]['long_name']
    else:
        field_name = str(field)
    field_name = field_name.replace('_', ' ')
    field_name = field_name[0].upper() + field_name[1:]
    return field_name

def generate_radar_name(radar):
    """ Return radar name. """
    if 'instrument_name' in radar.metadata:
        return radar.metadata['instrument_name']
    else:
        return ''

def generate_time_begin(radar):
    """ Return time begin in datetime instance. """
    # datetime object describing first sweep time
    times = radar.time['data'][0]
    units = radar.time['units']
    calendar = radar.time['calendar']
    return netCDF4.num2date(times, units, calendar)


def generate_filename(radar, field, sweep, ext='png'):
    """
    Generate a filename for a plot.

    Generated filename has form:
        radar_name_field_sweep_time.ext

    Parameters
    ----------
    radar : Radar
        Radar structure.
    field : str
        Field plotted.
    sweep : int
        Sweep plotted.
    ext : str
        Filename extension.

    Returns
    -------
    filename : str
        Filename suitable for saving a plot.

    """
    name_s = generate_radar_name(radar).replace(' ', '_')
    field_s = field.replace(' ', '_')
    time_s = generate_time_begin(radar).strftime('%Y%m%d%H%M%S')
    sweep_s = str(sweep).zfill(2)
    return '%s_%s_%s_%s.%s' % (name_s, field_s, sweep_s, time_s, ext)

def generate_title(radar, field, sweep):
    """
    Generate a title for a plot.

    Parameters
    ----------
    radar : Radar
        Radar structure.
    field : str
        Field plotted.
    sweep : int
        Sweep plotted.

    Returns
    -------
    title : str
        Plot title.

    """
    time_str = generate_time_begin(radar).isoformat() + 'Z'
    fixed_angle = radar.fixed_angle['data'][sweep]
    l1 = "%s %.1f Deg. %s " % (generate_radar_name(radar), fixed_angle, time_str)
    field_name = generate_field_name(radar, field)
    return l1 + '\n' + field_name

def generate_vpt_title(radar, field):
    """
    Generate a title for a VPT plot.

    Parameters
    ----------
    radar : Radar
        Radar structure.
    field : str
        Field plotted.

    Returns
    -------
    title : str
        Plot title.

    """
    time_str = generate_time_begin(radar).isoformat() + 'Z'
    l1 = "%s %s " % (generate_radar_name(radar), time_str)
    field_name = generate_field_name(radar, field)
    return l1 + '\n' + field_name

def generate_ray_title(radar, field, ray):
    """
    Generate a title for a ray plot.

    Parameters
    ----------
    radar : Radar
        Radar structure.
    field : str
        Field plotted.
    ray : int
        Ray plotted.

    Returns
    -------
    title : str
        Plot title.

    """
    time_str = generate_time_begin(radar).isoformat() + 'Z'
    l1 = "%s %s" % (generate_radar_name(radar), time_str)
    azim = radar.azimuth['data'][ray]
    elev = radar.elevation['data'][ray]
    l2 = "Ray: %i  Elevation: %.1f Azimuth: %.1f" % (ray, azim, elev)
    field_name = generate_field_name(radar, field)
    return l1 + '\n' + l2 + '\n' + field_name

def set_limits(self, xlim=None, ylim=None, ax=None):
    """
    Set the display limits.

    Parameters
    ----------
    xlim : tuple, optional
        2-Tuple containing y-axis limits in km. None uses default limits.
    ylim : tuple, optional
        2-Tuple containing x-axis limits in km. None uses default limits.
    ax : Axis
        Axis to adjust.  None will adjust the current axis.

    """
    if ax is None:
        ax = plt.gca()
    if ylim is not None:
        ax.set_ylim(ylim)
    if xlim is not None:
        ax.set_xlim(xlim)