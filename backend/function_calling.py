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
import numpy as np
from matplotlib import pyplot as plt
from pathlib import Path
from aws import (
    upload_file,
    download_file,
    delete_file,
)


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
def fit_ffef(name: str, params: Param, paths: FEFF_Path,xas_path:str) -> Report:
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
        load_prj(xas_path)
    )  # this function loads the data from the project file, which is used for the fit
    # --- Create a dataset for the fit ---
    dset = feffit_dataset(data=data, transform=trans, pathlist=paths_dict)

    result = feffit(params_group, [dset])

    # transform the result into correct pydantic format for LLM to understand
    fitted_parameters = extract_fitted_parameters(result)
    path_parameters = extract_path_parameters(result)



    viz(name,paths_dict,result,xas_path=xas_path)  # this is the function that visualizes the result

    return Report(fitted_parameter=fitted_parameters, path_parameter=path_parameters)




def viz(name,path_list,result,xas_path:str  ):
    """
    Visualize the result
    """

    print("Visualizing the result...")

    data=load_prj(xas_path=xas_path)

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
        plt.figure(figsize=(10,5))
        
        mod = result.datasets[i].model
        dat = result.datasets[i].data
        data_chik  = dat.chi * dat.k**kweight
        model_chik = mod.chi * mod.k**kweight

        plt.subplot(131)
        plt.plot(dat.k, data_chik, color='navy', label='data', alpha=0.6, lw=2)
        plt.plot(mod.k, model_chik, color='crimson', label='fit', alpha=0.6, lw=2)

        for i, path_i in enumerate(list(path_list.values())[:usepath]):
            path_i_data = ff2chi([path_i], params=result.paramgroup)
            path_chik  = path_i_data.chi * path_i_data.k**kweight
            path_name = path_i.filename.split('_')[-1].split('.')[0]
            
            plt.plot(path_i_data.k,
                    path_chik - step*(i+1),
                    label=path_name, 
                    color=colors[i], 
                    alpha=0.6, lw=1.5, ls='-.')
            
        plt.xlabel("$k$ [$\\AA^{-1}$]", fontsize=12)
        plt.ylabel("$k^2 \\chi (k)$ [$\\AA^{-2}$]", fontsize=12)
        plt.xlim(0, 9.5)
        # plt.ylim(-4, 1.25)

        plt.subplot(132)
        xftf(dat, kmin=3, kmax=kmax, kweight=kweight, dk=1, window='hanning', rmax_out=12)
        xftf(mod, kmin=3, kmax=kmax, kweight=kweight, dk=1, window='hanning', rmax_out=12)

        plt.plot(dat.r, dat.chir_mag, color='navy', label='data', alpha=0.6, lw=2)
        plt.plot(mod.r, mod.chir_mag, color='crimson', label='fit', alpha=0.6, lw=2)

        for i, path_i in enumerate(list(path_list.values())[:usepath]):
            path_i_data = ff2chi([path_i], params=result.paramgroup)
            path_chik  = path_i_data.chi * path_i_data.k**kweight
            xftf(path_i_data, kmin=3.5, kmax=9.5, kweight=kweight, dk=1, window='hanning', rmax_out=12)
            path_name = path_i.filename.split('_')[-1].split('.')[0]
            
            plt.plot(path_i_data.r,
                    path_i_data.chir_mag - step*(i+1),
                    label=path_name, 
                    color=colors[i], 
                    alpha=0.6, lw=1.5, ls='-.')
            
        plt.title(sample)
        plt.xlabel("$R$ [$\\AA$]", fontsize=12)
        plt.ylabel("$|\\chi(R)|$ [$\\AA ^{-3}$]", fontsize=12)
        plt.xlim(0, 5)
        # plt.ylim(-4, 1.25)

        plt.subplot(133)
        
        plt.plot(dat.r, dat.chir_re, color='navy', label='data', alpha=0.6, lw=2)
        plt.plot(mod.r, mod.chir_re, color='crimson', label='fit', alpha=0.6, lw=2)

        for i, path_i in enumerate(list(path_list.values())[:usepath]):
            path_i_data = ff2chi([path_i], params=result.paramgroup)
            path_chik  = path_i_data.chi * path_i_data.k**kweight
            xftf(path_i_data, kmin=3.5, kmax=9.5, kweight=kweight, dk=1, window='hanning', rmax_out=12)
            path_name = path_i.filename.split('_')[-1].split('.')[0]
            
            plt.plot(path_i_data.r,
                    path_i_data.chir_re - step*(i+1),
                    label=path_name, 
                    color=colors[i], 
                    alpha=0.6, lw=1.5, ls='-.')
            
        plt.xlabel("$R$ [$\\AA$]", fontsize=12)
        plt.ylabel("Re[$\\chi(R)$] [$\\AA ^{-3}$]", fontsize=12)
        plt.xlim(0, 5)
        # plt.ylim(-4, 1.25)
        plt.legend(loc='upper right', frameon=False)
        plt.tight_layout();

        origin = Path.cwd() 

        save_folder = 'physics/viz/'
        save_path = origin / save_folder / f"{sample}_all.jpg"
        plt.savefig(save_path, dpi = 300)
        # save_file_aws
        upload_file(save_path, "test-dr-xas", f"viz/{sample}_all.jpg")# what if file already exists?
        print(f"Visualization saved to {save_path}")


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
