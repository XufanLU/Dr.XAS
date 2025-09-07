from pathlib import Path
import glob
from pymatgen.io.cif import CifParser
from pymatgen.io.feff.sets import FEFFDictSet

import os
import subprocess
from pymatgen.io.cif import CifParser
from pymatgen.io.feff.sets import FEFFDictSet

import larch
from larch import Interpreter
from larch.xafs.feffrunner import feffrunner
from larch.xafs import (
    pre_edge,
    autobk,
    sort_xafs,
    xftf,
    xftr,
    ff2chi,
    feffpath,
    feffit_transform,
    feffit_dataset,
    feffit,
    feffit_report,
    cauchy_wavelet,
    pre_edge,
    autobk,
    xftf,
)
from larch.xafs import pre_edge, autobk, xftf
from larch.fitting import param, guess, param_group
from larch.io import read_ascii

from agents import function_tool
from typing import List
import matplotlib.pyplot as plt
import numpy as np


def get_absorber_from_cif(cif_file: str) -> str:
    absorber = "Ni"  # placeholder for the absorber element
    return absorber


def make_and_run_feff(cif_file_name, absorber, radius=5.0, edge="K"):
    """
    Run FEFF on a single CIF file.
    """
    origin = Path.cwd() / "material_cif"
    cif_file = origin / f"{cif_file_name}.cif"
    output_dir = Path.cwd() / "physics/FEFF_paths" / cif_file_name
    _make_and_run_feff(
        str(cif_file), str(output_dir), absorber=absorber, radius=radius, edge=edge
    )
    return Path.cwd() / "physics/FEFF_paths" / cif_file_name


def _make_and_run_feff(
    cif_file, out_dir, absorber="", radius=5.0, edge="K", feff_exe="feff8l"
):

    try:
        os.makedirs(out_dir, exist_ok=True)

        # 1) Parse CIF → structure
        struct = CifParser(cif_file).get_structures()[0]
        print(f"Read structure with {len(struct)} atoms from {cif_file}")

        # 2) Generate basic feff.inp with ff2chi=1
        feff_set = FEFFDictSet(
            absorbing_atom=absorber,
            structure=struct,
            radius=radius,
            edge=edge,
            config_dict={},
            user_tag_settings={"CONTROL": {"ff2chi": 1}},
        )
        feff_set.write_input(out_dir)

        # 3) Read, patch, write back
        inp_path = os.path.join(out_dir, "feff.inp")
        new_lines = []
        saw_control = saw_print = False

        for line in open(inp_path):
            # After writing or seeing a CONTROL line, inject our CONTROL+PRINT
            if line.strip().startswith("CONTROL") and not saw_control:
                new_lines.append(
                    "*         pot    xsph  fms   paths genfmt ff2chi\n"
                    "CONTROL   1      1     1     1     1      1\n"
                )
                new_lines.append("PRINT     1      0     0     0     0      3\n")
                saw_control = saw_print = True
                # skip any original CONTROL/PRINT lines
                continue

            # If CONTROL never appeared before POTENTIALS, inject just before POTENTIALS
            if not saw_control and line.strip().startswith("POTENTIALS"):
                new_lines.append(
                    "*         pot    xsph  fms   paths genfmt ff2chi\n"
                    "CONTROL   1      1     1     1     1      1\n"
                    "PRINT     1      0     0     0     0      3\n"
                )
                saw_control = saw_print = True

            new_lines.append(line)

        with open(inp_path, "w") as f:
            f.writelines(new_lines)

        # 4) Run the real FEFF8L (must be the Fortran binary!)
        print(f"Running {feff_exe} in {out_dir} …")
        subprocess.run([feff_exe], cwd=out_dir, check=True)
        print("Done; check for feff0001.dat … in", out_dir)
    except Exception as e:
        print(f"_make_and_run_feff: {e}")
        raise e


def load_paths(feff_dir, amp_ratio=None, r_max=None, verbose=False):
    """
    Scan a FEFF run directory, filter by amp_ratio and r_max, and return
    a dict mapping 'path<index>' to the corresponding feffNNNN.dat filepath.

    If verbose=True, prints a table with:
      Path  Bond   Amp (%)  R_eff (Å)   Deg  Nlegs

    Parameters
    ----------
    feff_dir : str
        Directory containing list.dat and feffNNNN.dat files.
    amp_ratio : float or None
        Minimum curved‑wave amplitude ratio (%) to include.
    r_max : float or None
        Maximum effective path length (Å) to include.
    verbose : bool
        If True, print a summary table.

    Returns
    -------
    dict
        { 'path1': '…/feff0001.dat', 'path2': … }
    """
    list_file = os.path.join(feff_dir, "list.dat")
    if not os.path.isfile(list_file):
        raise FileNotFoundError(f"No list.dat found in {feff_dir}")

    # Read list.dat and locate table start
    lines = open(list_file).read().splitlines()
    start = next((i + 1 for i, L in enumerate(lines) if "pathindex" in L.lower()), None)
    if start is None:
        start = next(
            (i + 1 for i, L in enumerate(lines) if L.strip().startswith("-----")), None
        )
    if start is None:
        raise ValueError("Couldn't find table in list.dat")

    # Parse columns: (index, amp, r_eff, deg, nlegs)
    entries = []
    for L in lines[start:]:
        parts = L.split()
        if not parts or not parts[0].isdigit():
            continue
        idx = int(parts[0])
        amp = float(parts[2])
        deg = float(parts[3])
        nlegs = int(parts[4])
        r_eff = float(parts[5])
        entries.append((idx, amp, r_eff, deg, nlegs))

    # Apply filters
    sel = [
        (i, amp, r_eff, deg, nlegs)
        for (i, amp, r_eff, deg, nlegs) in entries
        if (amp_ratio is None or amp >= amp_ratio) and (r_max is None or r_eff <= r_max)
    ]

    # Verbose header
    if verbose:
        header = f"{'Path':>4}  {'Bond':<7}  {'Amp (%)':>8}  {'R_eff (Å)':>9}  {'Deg':>4}  {'Nlegs':>5}"
        print(header)
        print("-" * len(header))

    paths = {}
    for idx, amp, r_eff, deg, nlegs in sel:
        # File path
        fname = os.path.join(feff_dir, f"feff{idx:04d}.dat")
        if not os.path.exists(fname):
            alt = fname.replace(".dat", ".data")
            if os.path.exists(alt):
                fname = alt
            else:
                continue

        # Determine bond type
        bond = ""
        with open(fname) as f:
            datlines = f.readlines()
        for j, line in enumerate(datlines):
            if "pot at#" in line.lower():
                atom_lines = [ln for ln in datlines[j + 1 : j + 4] if ln.strip()]
                if len(atom_lines) >= 2:
                    el0 = atom_lines[0].split()[5]
                    el1 = atom_lines[1].split()[5]
                    bond = f"{el0}-{el1}"
                break

        # Print row
        if verbose:
            print(
                f"{idx:4d}  {bond:<7}  {amp:8.3f}  {r_eff:9.3f}  {deg:4.1f}  {nlegs:5d}"
            )

        paths[f"path{idx}"] = fname

    return paths


def transform_paths(paths):
    # transform the paths into a format that can be used for fitting=> feffPath
    path_list = {}
    for path_key, path_str in paths.items():
        path = feffpath(
            path_str,
            s02="amp",
            e0="e0",
            deltar="alpha * reff",
            sigma2="sigma2_4",  # use Larch's built-in
        )

        path_list[path_key] = path
    return path_list


def load_prj(xas_path: str):
    """
    Load a project file, supporting both Athena .prj and plain text/ascii formats.
    """
    # filename = (
    #     Path.cwd() / "physics/Ni_edges_athena_project_file.prj"
    # )

    foldername = Path.cwd() / "online_xas_data" / Path(xas_path)
    # checke the folder exists
    if not foldername.exists():
        raise FileNotFoundError(f"Folder {foldername} does not exist.")
    # find the .prj file in the folder
    filenames = list(foldername.glob("*.dat")
    )
    if not filenames:
        raise FileNotFoundError(f"No .dat file found in folder {foldername}.")
    filename = filenames[0]  # take the first file found
    print(f"Loading project file: {filename}")
    if filename.suffix.lower() == ".prj":
        data = larch.io.read_athena(
            filename,
            match=None,
            do_preedge=True,
            do_bkg=True,
            do_fft=True,
            use_hashkey=False,
        )
    elif filename.suffix.lower() == ".dat":
        # Assume plain text, xmu, or ascii spectrum
        data = larch.io.read_ascii(
            filename,
            labels=("ang_c", "ang_o", "time", "i0", "itrans")
        )
        hc = 12398.42
        d = 1.63747
        theta = np.radians(data.ang_c)   # angle in radians
        energy = hc / (2 * d * np.sin(theta))

        data.energy = energy
        data.mu = -np.log(data.itrans / data.i0)

        # Step 3: process for EXAFS
        pre_edge(data)
        autobk(data)
        xftf(data)


    else:
        # Assume plain text, xmu, or ascii spectrum
        raise ValueError("Unsupported file format. Please provide a .prj or .dat file.")
    # TODO for "dat"

    return data


def _fit_ffef(name: str, params: dict, pathlist: list, xas_path: str):
    """
    Run a single fit on a FEFF path.
    """
    # This function is a placeholder for future implementation
    # It should take a path from the FEFF output and perform a fit

    # --- Define fourier transform ---

    fit_params = param_group(
        amp=param(params["amp"], vary=True),
        e0=param(params["e0"], vary=True),
        alpha=param(params["alpha"], vary=True),
        # t=param(300.0, vary=True),
        # theta=param(400.0, vary=True),
        sigma2=param(params["sigma2"], vary=True),
        sigma2_2=param(params["sigma2_2"], vary=True),
        sigma2_4=param(params["sigma2_4"], vary=True),
    )

    trans = feffit_transform(
        kmin=3, kmax=13, rmin=1, rmax=5.0, kweight=[1, 2, 3], dk=1, window="Hanning"
    )  # TODO : this can also be given as a parameter. hyper parameter. => we can use this for now
    data = load_prj(
        xas_path=xas_path
    )  # this function loads the data from the project file, which is used for the fit
    # Do pre-edge subtraction
    dset = feffit_dataset(data=data, transform=trans, pathlist=pathlist)

    result = feffit(fit_params, [dset])
    return result


def report(result):
    """
    Print a report of the fit results.
    """
    # feffit_report(result, with_paths=True)
    print(feffit_report(result, with_paths=True))


def extract_fitted_parameters(result) -> List:
    """
    Extract fitted parameters from the result of the fit.
    """
    params = result.params
    tr = result.datasets[0].transform

    s02, s02_err = 0, 0

    dataset = result.datasets[0]
    hashkey = dataset.hashkey
    paths = dataset.paths

    def safe_get(name: str):
        p = params.get(name)
        if p is None:
            return float("nan"), None
        return float(p.value), float(p.stderr) if p.stderr is not None else None

    for label, path in paths.items():
        path_hash = path.hashkey
        s02, s02_err = safe_get(
            f"s02_{hashkey}_{path_hash}"
        )  # It's the same for all paths, so we can break after the first one
        break

    # extract the parameters from the result
    nvar = result.nvarys
    kmin = tr.kmin if tr else float("nan")
    kmax = tr.kmax if tr else float("nan")
    rmin = tr.rmin if tr else float("nan")
    rmax = tr.rmax if tr else float("nan")

    deltae = params["e0"].value if "e0" in params else float("nan")
    errore = params["e0"].stderr if "e0" in params else float("nan")
    reduced_chi2 = (
        result.chi2_reduced if result.chi2_reduced is not None else float("nan")
    )
    rfactor = result.rfactor if result.rfactor is not None else float("nan")
    fitted_parameters = [
        nvar,
        kmin,
        kmax,
        rmin,
        rmax,
        deltae,
        errore,
        reduced_chi2,
        rfactor,
        s02,
        s02_err,
    ]
    print(fitted_parameters)

    return fitted_parameters


def extract_path_parameters(result) -> List:
    params = result.params
    dataset = result.datasets[0]
    hashkey = dataset.hashkey
    paths = dataset.paths

    path_summaries = []

    def safe_get(name: str):
        p = params.get(name)
        if p is None:
            return float("nan"), None
        return float(p.value), float(p.stderr) if p.stderr is not None else None

    for label, path in paths.items():
        path_hash = path.hashkey
        reff = float(path.reff)

        deltar, deltar_err = safe_get(f"deltar_{hashkey}_{path_hash}")
        sigma2, sigma2_err = safe_get(f"sigma2_{hashkey}_{path_hash}")
        path_summaries.append(
            [
                label,
                deltar,
                deltar_err,
                reff + (deltar if deltar is not None else 0.0),
                sigma2,
                sigma2_err,
            ]
        )
    print(path_summaries)
    return path_summaries


def viz(name, path_list, result,xas_path=None):
    """
    Visualize the result
    """

    data = load_prj(xas_path)

    datalist = [name]

    # cmap = plt.cm.nipy_spectral
    cmap = plt.cm.magma
    colors = [cmap(value) for value in np.linspace(0, 1, 16)]
    usepath = 16

    # step = 2.2 # Cu foil
    kweight = 2
    step = 1.2 * kweight / 2

    kmax = 10

    for i, sample in enumerate(datalist):
        plt.figure(figsize=(10, 5))

        mod = result.datasets[i].model
        dat = result.datasets[i].data
        data_chik = dat.chi * dat.k**kweight
        model_chik = mod.chi * mod.k**kweight

        plt.subplot(131)
        plt.plot(dat.k, data_chik, color="navy", label="data", alpha=0.6, lw=2)
        plt.plot(mod.k, model_chik, color="crimson", label="fit", alpha=0.6, lw=2)

        for i, path_i in enumerate(list(path_list.values())[:usepath]):
            path_i_data = ff2chi([path_i], params=result.paramgroup)
            path_chik = path_i_data.chi * path_i_data.k**kweight
            path_name = path_i.filename.split("_")[-1].split(".")[0]

            plt.plot(
                path_i_data.k,
                path_chik - step * (i + 1),
                label=path_name,
                color=colors[i],
                alpha=0.6,
                lw=1.5,
                ls="-.",
            )

        plt.xlabel("$k$ [$\\AA^{-1}$]", fontsize=12)
        plt.ylabel("$k^2 \\chi (k)$ [$\\AA^{-2}$]", fontsize=12)
        plt.xlim(0, 9.5)
        # plt.ylim(-4, 1.25)

        plt.subplot(132)
        xftf(
            dat, kmin=3, kmax=kmax, kweight=kweight, dk=1, window="hanning", rmax_out=12
        )
        xftf(
            mod, kmin=3, kmax=kmax, kweight=kweight, dk=1, window="hanning", rmax_out=12
        )

        plt.plot(dat.r, dat.chir_mag, color="navy", label="data", alpha=0.6, lw=2)
        plt.plot(mod.r, mod.chir_mag, color="crimson", label="fit", alpha=0.6, lw=2)

        for i, path_i in enumerate(list(path_list.values())[:usepath]):
            path_i_data = ff2chi([path_i], params=result.paramgroup)
            path_chik = path_i_data.chi * path_i_data.k**kweight
            xftf(
                path_i_data,
                kmin=3.5,
                kmax=9.5,
                kweight=kweight,
                dk=1,
                window="hanning",
                rmax_out=12,
            )
            path_name = path_i.filename.split("_")[-1].split(".")[0]

            plt.plot(
                path_i_data.r,
                path_i_data.chir_mag - step * (i + 1),
                label=path_name,
                color=colors[i],
                alpha=0.6,
                lw=1.5,
                ls="-.",
            )

        plt.title(sample)
        plt.xlabel("$R$ [$\\AA$]", fontsize=12)
        plt.ylabel("$|\\chi(R)|$ [$\\AA ^{-3}$]", fontsize=12)
        plt.xlim(0, 5)
        # plt.ylim(-4, 1.25)

        plt.subplot(133)

        plt.plot(dat.r, dat.chir_re, color="navy", label="data", alpha=0.6, lw=2)
        plt.plot(mod.r, mod.chir_re, color="crimson", label="fit", alpha=0.6, lw=2)

        for i, path_i in enumerate(list(path_list.values())[:usepath]):
            path_i_data = ff2chi([path_i], params=result.paramgroup)
            path_chik = path_i_data.chi * path_i_data.k**kweight
            xftf(
                path_i_data,
                kmin=3.5,
                kmax=9.5,
                kweight=kweight,
                dk=1,
                window="hanning",
                rmax_out=12,
            )
            path_name = path_i.filename.split("_")[-1].split(".")[0]

            plt.plot(
                path_i_data.r,
                path_i_data.chir_re - step * (i + 1),
                label=path_name,
                color=colors[i],
                alpha=0.6,
                lw=1.5,
                ls="-.",
            )

        plt.xlabel("$R$ [$\\AA$]", fontsize=12)
        plt.ylabel("Re[$\\chi(R)$] [$\\AA ^{-3}$]", fontsize=12)
        plt.xlim(0, 5)
        # plt.ylim(-4, 1.25)
        plt.legend(loc="upper right", frameon=False)
        plt.tight_layout()

        origin = Path.cwd()

        save_folder = "physics/viz/"
        save_path = origin / save_folder / f"{sample}_all.jpg"
        plt.savefig(save_path, dpi=300)


if __name__ == "__main__":
#    name = "Ni_foil"  # user input file
    # /Users/xufanlu/Projects/MT/Dr.XAFS/backend/material_cif/mp-1072089.cif
    material_id = "mp-1072089"
    material = "Co"  # from chat
    xas_id = "ff693629-a57c-4475-aaa8-5a4a815db425"  # from chat

  # absorber = "Ni"  # also user input? TODO . prj => recognize automatically.
    amp_ratio = 0.1
    r_max = 5.0
    verbose = True

    # user feedback is needed here, what are the parameters that the user wants to set? We can provide some initial guesses

    amp = 0.8  # initial guess for the amplitude
    e0 = 0.0  # initial guess for the energy shift
    alpha = 0  # initial guess for the Debye-Waller factor
    # t = 300.0  # initial guess for the temperature (if needed)
    # theta = 400.0v  # initial guess for the Debye temperature (if needed)
    sigma2 = 0.001  # initial guess for the mean square displacement
    sigma2_2 = 0.001  # initial guess for the second moment
    sigma2_4 = 0.001  # initial guess for the fourth moment

    params = {
        "amp": amp,
        "e0": e0,
        "alpha": alpha,
        "sigma2": sigma2,
        "sigma2_2": sigma2_2,
        "sigma2_4": sigma2_4,
    }  # dict of parameter initial values

    dat_paths = make_and_run_feff(material_id, material)
    dat_paths_str = load_paths(
        dat_paths, amp_ratio, r_max, verbose=True
    )  # of verbose == True, prints a table with the paths
    path_list = transform_paths(dat_paths_str)  # type?

    result = _fit_ffef(
        material_id, params, path_list, xas_path=xas_id
    )  # this is the function that runs the fit on the paths

    report(result) # this is the function that prints the report of the fit results
    # print("############################")
    # print("line 400")
    # extract_path_parameters(result)
    # print("############################")
    # print("line 403")
    # extract_fitted_parameters(
    #     result
    # )  # this is the function that extracts the fitted parameters from the result of the fit#

    viz(material_id, path_list, result,xas_path=xas_id)  # this is the function that visualizes the result
