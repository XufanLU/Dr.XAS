## define the functions to be called. 
from openai import OpenAI
import os
from dotenv import load_dotenv
from typing import List


from larch.xafs.feffrunner import feffrunner
from larch.xafs import (pre_edge, autobk, sort_xafs, xftf, xftr, ff2chi, feffpath, feffit_transform, feffit_dataset, feffit, feffit_report, cauchy_wavelet)
from larch.fitting import param, guess, param_group
from larch.io import read_ascii
from physics.physic_functions import load_prj

from agents import function_tool
from pydantic import BaseModel


load_dotenv()

class Report(BaseModel):
    value: float
    error: float

class Param(BaseModel):
    amp: float
    e0: float
    alpha: float
    sigma2: float
    sigma2_2: float
    sigma2_4: float
# Define the function to fit XAFS data using FEFF paths

class FEFF_Path(BaseModel):
    path_name: str
    file_path: list[str]

@function_tool
def fit_ffef(name:str,params:Param,paths:List[FEFF_Path])-> Report:# bug fixinf: https://github.com/fastapi/fastapi/discussions/10623
    """
    Fit XAFS data using the provided parameters to FEFF paths
    """
    # This function is a placeholder for future implementation
    # It should take a path from the FEFF output and perform a fit

  
    params_group = param_group(
        amp=param(params.amp, vary=True),
        e0=param(params.e0, vary=True),
        alpha=param(params.alpha, vary=True),
        sigma2=param(params.sigma2, vary=True),
        sigma2_2=param(params.sigma2_2, vary=True),
        sigma2_4=param(params.sigma2_4, vary=True)
    )
    paths_dict = {path.path_name: path.file_path for path in paths}

    # --- Define fourier transform ---
    trans = feffit_transform(kmin=3, kmax=13, 
                         rmin=1, rmax=5.0,
                         kweight=[1, 2, 3], dk=1, window='Hanning') # TODO : this can also be given as a parameter. hyper parameter. => we can use this for now
    data=load_prj()# this function loads the data from the project file, which is used for the fit
    # --- Create a dataset for the fit ---
    dset= feffit_dataset(data=data[name], 
                              transform=trans, 
                              pathlist=paths_dict)



   # result=feffit(params, [dset])
    #report=feffit_report(result)
    #report='this report is a placeholder for the future implementation of the fit function'
    return Report(value=0.7, error=0.0)  # Placeholder return value
