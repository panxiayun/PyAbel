# -*- coding: utf-8 -*-

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import numpy as np
from abel.tools.polar import reproject_image_into_polar
from scipy.ndimage import map_coordinates
from scipy.ndimage.interpolation import shift
from scipy.optimize import curve_fit


def angular_integration(IM, origin=None, Jacobian=True, dr=1, dt=None):
    """ Angular integration of the image.

        Returning the one-dimentional intensity profile as a function of the
        radial coordinate.

     Parameters
     ----------
     IM : rows x cols 2D np.array
       The data image.

     origin : tuple
       Image center coordinate relative to *bottom-left* corner
       defaults to (rows//2+rows%2,cols//2+cols%2).

     Jacobian : boolean
       Include r*sinθ in the angular sum (integration).

     dr : float
       Radial coordinate grid spacing, in pixels (default 1).

     dt : float
       Theta coordinate grid spacing in degrees, defaults to rows//2.

     Returns
     -------
     speeds : 1D np.array
       Integrated intensity array (vs radius).

      r : 1D np.array
       radial coordinates

     """

    polarIM, r_grid, theta_grid = reproject_image_into_polar(
        IM, origin, Jacobian=Jacobian, dr=dr, dt=dt)
    theta = theta_grid[0, :]   # theta coordinates
    r = r_grid[:, 0]           # radial coordinates

    if Jacobian:  # x r sinθ
        sintheta = np.abs(np.sin(theta))
        polarIM = polarIM*sintheta[np.newaxis, :]
        polarIM = polarIM*r[:, np.newaxis]

    speeds = np.sum(polarIM, axis=1)
    n = speeds.shape[0]

    return r[:n], speeds   # limit radial coordinates range to match speed


def calculate_angular_distributions(IM, radial_ranges=None):
    """ Intensity variation in the angular coordinate, theta.

    This function is the theta-coordinate complement to 'calculate_speeds(IM)'

    (optionally and more useful) returning intensity vs angle for defined
    radial ranges.

    Parameters
    ----------
    IM : 2D np.array
        Image data

    radial_ranges : list of tuples
        [(r0, r1), (r2, r3), ...]
        Evaluate the intensity vs angle
        for the radial ranges r0_r1, r2_r3, etc.

    Returns
    -------
    intensity_vs_theta: 2D np.array
       Intensity vs angle distribution for each selected radial range.

    theta: 1D np.array
       Angle coordinates, referenced to vertical direction.

    """

    polarIM, r_grid, theta_grid = reproject_image_into_polar(IM)

    theta = theta_grid[0, :]  # theta coordinates
    r = r_grid[:, 0]          # radial coordinates

    if radial_ranges is None:
        radial_ranges = [(0, r[-1]), ]

    intensity_vs_theta_at_R = []
    for rr in radial_ranges:
        subr = np.logical_and(r >= rr[0], r <= rr[1])

        # sum intensity across radius of spectral feature
        intensity_vs_theta_at_R.append(np.sum(polarIM[subr], axis=0))

    return np.array(intensity_vs_theta_at_R), theta


def anisotropy_parameter(theta, intensity, theta_ranges=None):
    """ Evaluate anisotropy parameter beta, for I vs theta data.

         I = xs_total/4pi [ 1 + beta P2(cos theta) ]     Eq. (1)

     where P2(x)=(3x^2-1)/2 is a 2nd order Legendre polynomial.

    Cooper and Zare "Angular distribution of photoelectrons"
    J Chem Phys 48, 942-943 (1968) doi:10.1063/1.1668742


    Parameters:
    -----------
    theta: 1D np.array
       Angle coordinates, referenced to the vertical direction.

    intensity: 1D np.array
       Intensity variation (with angle)

    theta_ranges: list of tuples
       Angular ranges over which to fit  [(theta1, theta2), (theta3, theta4)].
       Allows data to be excluded from fit

    Returns:
    --------
    (beta, error_beta) : tuple of floats
    (amplitude, error_amplitude) : tuple of floats
       Fit parameters: (beta, error_beta), (amplitude, error_amplitude)

    """
    def P2(x):   # 2nd order Legendre polynomial
        return (3*x*x-1)/2

    def PAD(theta, beta, amplitude):
        return amplitude*(1 + beta*P2(np.cos(theta)))   # Eq. (1) as above

    # select data to be included in the fit by θ
    if theta_ranges is not None:
        subtheta = np.ones(len(theta), dtype=bool)
        for rt in theta_ranges:
            subtheta = np.logical_and(
                subtheta, np.logical_and(theta >= rt[0], theta <= rt[1]))
        theta = theta[subtheta]
        intensity = intensity[subtheta]

    # fit angular intensity distribution
    popt, pcov = curve_fit(PAD, theta, intensity)

    beta, amplitude = popt
    error_beta, error_amplitude = np.sqrt(np.diag(pcov))

    return (beta, error_beta), (amplitude, error_amplitude)


