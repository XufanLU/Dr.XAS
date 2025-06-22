## define the functions to be called.
from openai import OpenAI
import os
from dotenv import load_dotenv
from typing import List, Dict


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
from physics.physic_functions import load_prj

from agents import function_tool
from pydantic import BaseModel
from typing import List


load_dotenv()


class Param(BaseModel):
    amp: float
    e0: float
    alpha: float
    sigma2: float
    sigma2_2: float
    sigma2_4: float


# Define the function to fit XAFS data using FEFF paths

# class FEFF_Path(BaseModel):
#     path_name: str
#     file_path: list[str]


class FittedParameter(BaseModel):
    nvar: int | None
    kmin: float
    kmax: float
    rmin: float
    rmax: float
    s02: float
    s02_err: float | None
    deltae: float
    errore: float | None
    reduced_chi2: float
    rfactor: float


class PathParameter(BaseModel):
    path_label: str
    deltar: float
    deltar_err: float | None
    R: float  # reff + deltar
    sigma2: float
    sigma2_err: float | None


# Define an entry for each dynamic path
class FEFFPathEntry(BaseModel):
    name: str
    path: str


# Wrap entries in a list
class FEFF_Path(BaseModel):
    entries: List[FEFFPathEntry]

    def items(self):
        # Provide dict-like access
        return [(entry.name, entry.path) for entry in self.entries]


class Report(BaseModel):
    fitted_parameter: FittedParameter | None = None
    path_parameter: List[PathParameter] | None = None


@function_tool
def fit_ffef(name: str, params: Param, paths: FEFF_Path) -> Report:
    """
    Fit XAFS data using the provided parameters to FEFF paths
    """
    params_group = param_group(
        amp=param(params.amp, vary=True),
        e0=param(params.e0, vary=True),
        alpha=param(params.alpha, vary=True),
        sigma2=param(params.sigma2, vary=True),
        sigma2_2=param(params.sigma2_2, vary=True),
        sigma2_4=param(params.sigma2_4, vary=True),
    )

    # --- Define the paths ---
    paths_dict = {}
    for path_key, path_str in paths.items():
        path = feffpath(
            path_str,
            degen="degen",
            s02="amp",
            e0="e0",
            deltar="alpha * reff",
            sigma2="sigma2_4",
        )
        paths_dict[path_key] = path

    # --- Define fourier transform ---
    trans = feffit_transform(
        kmin=3, kmax=13, rmin=1, rmax=5.0, kweight=[1, 2, 3], dk=1, window="Hanning"
    )  # TODO : this can also be given as a parameter. hyper parameter. => we can use this for now
    data = (
        load_prj()
    )  # this function loads the data from the project file, which is used for the fit
    # --- Create a dataset for the fit ---
    dset = feffit_dataset(data=data[name], transform=trans, pathlist=paths_dict)

    result = feffit(params_group, [dset])

    # transform the result into correct pydantic format for LLM to understand
    fitted_parameters = extract_fitted_parameters(result)
    path_parameters = extract_path_parameters(result)

    return Report(fitted_parameter=fitted_parameters, path_parameter=path_parameters)


def extract_fitted_parameters(result) -> FittedParameter:
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

    return FittedParameter(
        nvar=nvar,
        kmin=kmin,
        kmax=kmax,
        rmin=rmin,
        rmax=rmax,
        s02=s02,
        s02_err=s02_err,
        deltae=deltae,
        errore=errore,
        reduced_chi2=reduced_chi2,
        rfactor=rfactor,
    )


def extract_path_parameters(result) -> List[PathParameter]:
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
            PathParameter(
                path_label=label,
                deltar=deltar,
                deltar_err=deltar_err,
                R=reff + (deltar if deltar is not None else 0.0),
                sigma2=sigma2,
                sigma2_err=sigma2_err,
            )
        )
    return path_summaries
