#!/usr/bin/env python

import os
import pkg_resources
import argparse

import matplotlib.pyplot as plt
import matplotlib as mpl

import astropy.units as u
from astropy.table import Table
from astropy.modeling.fitting import LevMarLSQFitter

from pahfit.base import PAHFITBase


def initialize_parser():
    """
    Command line parser for run_pahfit

    Returns
    -------
    parser : argparse object
    """
    plottypes = [
        "png",
        "jpg",
        "jpeg",
        "pdf",
        "ps",
        "eps",
        "rgba",
        "svg",
        "tiff",
        "tif",
        "pgf",
        "svgz",
        "raw",
    ]
    savetypes = ["fits", "votable", "ipac", "ascii.ecsv"]
    parser = argparse.ArgumentParser()
    parser.add_argument("spectrumfile", help="name of file with observed spectrum")
    parser.add_argument("packfile", help="name of PAHFIT pack file")
    parser.add_argument(
        "--savefig",
        action="store",
        default="pdf",
        choices=plottypes,
        help="Save figure to a file of specified type",
    )
    parser.add_argument(
        "--showplot", action="store_true", help="display plot to the screen"
    )
    parser.add_argument(
        "--saveoutput",
        action="store",
        default="ipac",
        choices=savetypes,
        help="Save fit results to a file of specified type",
    )
    parser.add_argument(
        "--estimate_start",
        action="store_true",
        help="Estimate of starting point based on the input spectrum",
    )

    return parser


def main():

    # setup and parse the command line
    parser = initialize_parser()
    args = parser.parse_args()

    # read in the observed spectrum
    # assumed to be astropy table compatibile and include units
    specfile = args.spectrumfile
    outputname = specfile.split(".")[0]
    if not os.path.isfile(specfile):
        pack_path = pkg_resources.resource_filename("pahfit", "data/")
        test_specfile = "{}/{}".format(pack_path, specfile)
        if os.path.isfile(test_specfile):
            specfile = test_specfile
        else:
            raise ValueError("Input spectrumfile {} not found".format(specfile))

    # get the table format (from extension of filename)
    tformat = specfile.split(".")[-1]
    if tformat == "ecsv":
        tformat = "ascii.ecsv"
    obs_spectrum = Table.read(specfile, format=tformat)
    obs_x = obs_spectrum["wavelength"].to(u.micron, equivalencies=u.spectral())
    obs_y = obs_spectrum["flux"].to(u.Jy, equivalencies=u.spectral_density(obs_x))
    obs_unc = obs_spectrum["sigma"].to(u.Jy, equivalencies=u.spectral_density(obs_x))

    # strip units as the observed spectrum is in the internal units
    obs_x = obs_x.value
    obs_y = obs_y.value
    weights = 1.0 / obs_unc.value

    # read in the pack file
    packfile = args.packfile
    if not os.path.isfile(packfile):
        pack_path = pkg_resources.resource_filename("pahfit", "packs/")
        test_packfile = "{}/{}".format(pack_path, packfile)
        if os.path.isfile(test_packfile):
            packfile = test_packfile
        else:
            raise ValueError("Input packfile {} not found".format(packfile))

    pmodel = PAHFITBase(
        obs_x, obs_y, estimate_start=args.estimate_start, filename=packfile
    )

    # pick the fitter
    fit = LevMarLSQFitter()

    # fit
    obs_fit = fit(
        pmodel.model,
        obs_x,
        obs_y,
        weights=weights,
        maxiter=200,
        epsilon=1e-10,
        acc=1e-10,
    )
    print(fit.fit_info["message"])

    # save results to fits file
    pmodel.save(obs_fit, outputname, args.saveoutput)

    # plot result
    fontsize = 18
    font = {"size": fontsize}
    mpl.rc("font", **font)
    mpl.rc("lines", linewidth=2)
    mpl.rc("axes", linewidth=2)
    mpl.rc("xtick.major", width=2)
    mpl.rc("ytick.major", width=2)

    fig, ax = plt.subplots(figsize=(15, 10))

    pmodel.plot(ax, obs_x, obs_y, obs_fit)

    ax.set_yscale("linear")
    ax.set_xscale("log")

    # use the whitespace better
    fig.tight_layout()

    # show
    if args.showplot:
        plt.show()
    # save (always)
    fig.savefig("{}.{}".format(outputname, args.savefig))


if __name__ == "__main__":
    main()
