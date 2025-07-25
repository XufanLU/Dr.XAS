from openai import OpenAI
import os
from dotenv import load_dotenv
from agents import Agent, Runner, WebSearchTool
import physics
from physics.physic_functions import (
    get_absorber_from_cif,
    make_and_run_feff,
    load_paths,
    transform_paths,
)
from function_calling import fit_ffef
import asyncio


load_dotenv()


async def prepocessing(
    name: str, cif_file: str
) -> list:  # only need the name, if we fix the location of the file.
    """
    Preprocessing function to clean and prepare the input text.
    """

    absorber = get_absorber_from_cif(cif_file)
    dat_paths = make_and_run_feff(name, absorber)
    dat_paths_str = load_paths(dat_paths)
    # path_list=transform_paths(dat_paths_str)

    return dat_paths_str


async def create_agent(name: str, cif_file: str) -> Agent:
    """
    Create an agent that can perform the fitting task.
    """

    paths_str = await prepocessing(name, cif_file)
    try:

        agent = Agent(
            name="Assistant",
            instructions=f"You are a helpful assistant. You will be provided with a list parameters, please fit XAFS data with name {name} using the provided parameters to FEFF paths {paths_str}",
            tools=[fit_ffef],
        )

        return agent
    except Exception as e:
        print(f"Error creating agent: {e}")
        raise e 

async def main():
    name = "Ni_foil"  # user input file
    cif_file = "physics/cif_files/Ni_foil.cif"  # user input file

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
    }
    agent = await create_agent(name, cif_file)

    content = f""" 
    params: {params}
    """
    # Run the agent with the input content

    result = await Runner.run(agent, content)
    print(result.final_output)


if __name__ == "__main__":
    asyncio.run(main())
