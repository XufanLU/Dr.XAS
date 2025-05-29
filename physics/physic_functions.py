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
from larch.xafs import (pre_edge, autobk, sort_xafs, xftf, xftr, ff2chi, feffpath, feffit_transform, feffit_dataset, feffit, feffit_report, cauchy_wavelet)
from larch.fitting import param, guess, param_group
from larch.io import read_ascii


def _make_and_run_feff(cif_file, out_dir,
                      absorber="Ni", radius=5.0, edge="K",
                      feff_exe="feff8l"):
    os.makedirs(out_dir, exist_ok=True)

    # 1) Parse CIF → structure
    struct = CifParser(cif_file).get_structures()[0]

    # 2) Generate basic feff.inp with ff2chi=1
    feff_set = FEFFDictSet(
        absorbing_atom   = absorber,
        structure        = struct,
        radius           = radius,
        edge             = edge,
        config_dict      = {},
        user_tag_settings={"CONTROL": {"ff2chi": 1}}
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
            new_lines.append(
                "PRINT     1      0     0     0     0      3\n"
            )
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

    

def make_and_run_feff(file_name, absorber, radius=5.0, edge="K"):
    """
    Run FEFF on a single CIF file.
    """
    origin=Path.cwd()/ 'physics/cif_files'
    cif_file = origin / f"{file_name}.cif"
    output_dir = Path.cwd() / 'physics/FEFF_paths' / file_name
    _make_and_run_feff(str(cif_file), str(output_dir), absorber=absorber, radius=radius, edge=edge)
    return Path.cwd()/ 'physics/FEFF_paths'/ file_name


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
    start = next((i+1 for i, L in enumerate(lines) if "pathindex" in L.lower()), None)
    if start is None:
        start = next((i+1 for i, L in enumerate(lines) if L.strip().startswith("-----")), None)
    if start is None:
        raise ValueError("Couldn't find table in list.dat")

    # Parse columns: (index, amp, r_eff, deg, nlegs)
    entries = []
    for L in lines[start:]:
        parts = L.split()
        if not parts or not parts[0].isdigit():
            continue
        idx    = int(parts[0])
        amp    = float(parts[2])
        deg    = float(parts[3])
        nlegs  = int(parts[4])
        r_eff  = float(parts[5])
        entries.append((idx, amp, r_eff, deg, nlegs))

    # Apply filters
    sel = [
        (i, amp, r_eff, deg, nlegs)
        for (i, amp, r_eff, deg, nlegs) in entries
        if (amp_ratio is None or amp >= amp_ratio)
        and (r_max     is None or r_eff <= r_max)
    ]

    # Verbose header
    if verbose:
        header = f"{'Path':>4}  {'Bond':<7}  {'Amp (%)':>8}  {'R_eff (Å)':>9}  {'Deg':>4}  {'Nlegs':>5}"
        print(header)
        print('-' * len(header))

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
                atom_lines = [ln for ln in datlines[j+1:j+4] if ln.strip()]
                if len(atom_lines) >= 2:
                    el0 = atom_lines[0].split()[5]
                    el1 = atom_lines[1].split()[5]
                    bond = f"{el0}-{el1}"
                break

        # Print row
        if verbose:
            print(f"{idx:4d}  {bond:<7}  {amp:8.3f}  {r_eff:9.3f}  {deg:4.1f}  {nlegs:5d}")

        paths[f"path{idx}"] = fname


    return paths

def transform_paths(paths):
    # transform the paths into a format that can be used for fitting=> feffPath
    path_list = {}
    for path_key, path_str in paths.items():
        path = feffpath(path_str,
                        degen='degen',
                        s02='amp',
                        e0='e0',
                        deltar='alpha * reff',
                        sigma2='sigma2_4'  # use Larch's built-in
                    )
        # # Apply Einstein sigma²
        # s2 = sigma2_eins(t=300, theta=400, path=path)
        # print(s2)
        # path.sigma2 = s2
        path_list[path_key] = path
    return path_list


def load_prj():

    athena_prj=Path.cwd()/ 'physics/Ni_edges_athena_project_file.prj' # where do we get this file?  # TODO
    data = larch.io.read_athena(
                            athena_prj, 
                            match=None, 
                            do_preedge=True, # 
                            do_bkg=True, 
                            do_fft=True, 
                            use_hashkey=False
                            )
    return data



def fit(name,params,pathlist):
    """
    Run a single fit on a FEFF path.
    """
    # This function is a placeholder for future implementation
    # It should take a path from the FEFF output and perform a fit

    # --- Define fourier transform ---
    trans = feffit_transform(kmin=3, kmax=13, 
                         rmin=1, rmax=5.0,
                         kweight=[1, 2, 3], dk=1, window='Hanning')# TODO : this can also be given as a parameter
    data=load_prj()# this function loads the data from the project file, which is used for the fit
    # --- Create a dataset for the fit ---
    dset= feffit_dataset(data=data[name], 
                              transform=trans, 
                              pathlist=pathlist)


    result=feffit(params, [dset])
    return result

def report(result):
    """
    Print a report of the fit results.
    """
    print(feffit_report(result,  with_paths=True))



if __name__ == "__main__":
    name = 'Ni_foil'#user input file 

    absorber = 'Ni'# also user input? 
    amp_ratio=0.1
    r_max=5.0
    verbose=True

# user feedback is needed here, what are the parameters that the user wants to set? We can provide some initial guesses
    params =param_group(
    amp=param(0.8, vary=True),
    e0=param(0.0, vary=True),
    alpha=param(0, vary=True),
    # t=param(300.0, vary=True),
    # theta=param(400.0, vary=True),
    sigma2=param(0.001, vary=True),
    sigma2_2=param(0.001, vary=True),
    sigma2_4=param(0.001, vary=True))


    dat_paths=make_and_run_feff(name, absorber)
    dat_paths_str = load_paths(dat_paths,amp_ratio, r_max, verbose=True)# of verbose == True, prints a table with the paths
    path_list=transform_paths(dat_paths_str)

    result=fit(name,params, path_list) # this is the function that runs the fit on the paths
    report(result) # this is the function that prints the report of the fit results


