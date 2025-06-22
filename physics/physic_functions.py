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
)
from larch.fitting import param, guess, param_group
from larch.io import read_ascii

from agents import function_tool
from typing import List


def get_absorber_from_cif(cif_file: str) -> str:
    absorber = "Ni"  # placeholder for the absorber element
    return absorber


def make_and_run_feff(file_name, absorber, radius=5.0, edge="K"):
    """
    Run FEFF on a single CIF file.
    """
    origin = Path.cwd() / "physics/cif_files"
    cif_file = origin / f"{file_name}.cif"
    output_dir = Path.cwd() / "physics/FEFF_paths" / file_name
    _make_and_run_feff(
        str(cif_file), str(output_dir), absorber=absorber, radius=radius, edge=edge
    )
    return Path.cwd() / "physics/FEFF_paths" / file_name


def _make_and_run_feff(
    cif_file, out_dir, absorber="Ni", radius=5.0, edge="K", feff_exe="feff8l"
):
    os.makedirs(out_dir, exist_ok=True)

    # 1) Parse CIF → structure
    struct = CifParser(cif_file).get_structures()[0]

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
            degen="degen",
            s02="amp",
            e0="e0",
            deltar="alpha * reff",
            sigma2="sigma2_4",  # use Larch's built-in
        )

        path_list[path_key] = path
    return path_list


def load_prj():

    athena_prj = (
        Path.cwd() / "physics/Ni_edges_athena_project_file.prj"
    )  # where do we get this file?  # TODO could be txt / prj. ....
    data = larch.io.read_athena(
        athena_prj,
        match=None,
        do_preedge=True,  #
        do_bkg=True,
        do_fft=True,
        use_hashkey=False,
    )
    return data


def _fit_ffef(name: str, params: dict, pathlist: list):
    """
    Run a single fit on a FEFF path.
    """
    # This function is a placeholder for future implementation
    # It should take a path from the FEFF output and perform a fit

    # --- Define fourier transform ---

    params = param_group(
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
    data = (
        load_prj()
    )  # this function loads the data from the project file, which is used for the fit
    # --- Create a dataset for the fit ---
    dset = feffit_dataset(data=data[name], transform=trans, pathlist=pathlist)

    result = feffit(params, [dset])
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


if __name__ == "__main__":
    name = "Ni_foil"  # user input file

    absorber = "Ni"  # also user input? TODO . prj => recognize automatically.
    amp_ratio = 0.1
    r_max = 5.0
    verbose = True

    # user feedback is needed here, what are the parameters that the user wants to set? We can provide some initial guesses

    amp = 0.8  # initial guess for the amplitude
    e0 = 0.0  # initial guess for the energy shift
    alpha = 0  # initial guess for the Debye-Waller factor
    # t = 300.0  # initial guess for the temperature (if needed)
    # theta = 400.0  # initial guess for the Debye temperature (if needed)
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

    dat_paths = make_and_run_feff(name, absorber)
    dat_paths_str = load_paths(
        dat_paths, amp_ratio, r_max, verbose=True
    )  # of verbose == True, prints a table with the paths
    path_list = transform_paths(dat_paths_str)  # type?

    result = _fit_ffef(
        name, params, path_list
    )  # this is the function that runs the fit on the paths

    # report(result) # this is the function that prints the report of the fit results
    print("############################")
    print("line 400")
    extract_path_parameters(result)
    print("############################")
    print("line 403")
    extract_fitted_parameters(
        result
    )  # this is the function that extracts the fitted parameters from the result of the fit
