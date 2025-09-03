import logging
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from agents import (
    Runner,
    ItemHelpers,
    MessageOutputItem,
    HandoffOutputItem,
    ToolCallItem,
    ToolCallOutputItem,
    InputGuardrailTripwireTriggered,
    Handoff,
)
from aws import create_bucket
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from uuid import uuid4
from agent import create_agent
from aws import (
    upload_file,
    download_file,
    delete_file,
    create_s3_client,
    create_bucket)
from dotenv import load_dotenv
import os

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
from pathlib import Path
from physics.physic_functions import _make_and_run_feff, make_and_run_feff,get_absorber_from_cif, load_paths, transform_paths,_fit_ffef

from spectrum_database import get_datasets, get_data_by_id

load_dotenv()
app = FastAPI()



# CORS configuration (adjust as needed for deployment)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://lbc-dr-xas-2-1793621863.eu-north-1.elb.amazonaws.com:3000",
        "http://localhost:3000"
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=[
        "Content-Type",
        "Authorization",
        "Accept",
        "X-Requested-With",
        "X-CSRF-Token",
        "Access-Control-Allow-Headers",
        "Access-Control-Allow-Origin",
        "Origin",
        "Referer",
        "User-Agent",
        "Cache-Control",
        "Pragma"
    ]
)

#============
# AWS setup
#============
#create_bucket("test-dr-xas")  # Create a bucket for storing data



#============
# Models 
#============


class ChatRequest(BaseModel):
    conversation_id: Optional[str] = None
    agent_id: Optional[str] = None
    message: str


# =========================
# In-memory store for conversation state
# =========================

class ConversationStore:
    def get(self, conversation_id: str) -> Optional[Dict[str, Any]]:
        pass

    def save(self, conversation_id: str, state: Dict[str, Any]):
        pass

class InMemoryConversationStore(ConversationStore):
    _conversations: Dict[str, Dict[str, Any]] = {}

    def get(self, conversation_id: str) -> Optional[Dict[str, Any]]:
        return self._conversations.get(conversation_id)

    def save(self, conversation_id: str, state: Dict[str, Any]):
        self._conversations[conversation_id] = state

# TODO: when deploying this app in scale, switch thisto normal database 
conversation_store = InMemoryConversationStore()

class InMemoryAgentStore(ConversationStore):
    _agents: Dict[str, Dict[str, Any]] = {}

    def get(self, agent_id: str) -> Optional[Dict[str, Any]]:
        return self._agents.get(agent_id)

    def save(self, agent_id: str, state: Dict[str, Any]):
        self._agents[agent_id] = state

# TODO: when deploying this app in scale, switch this to a normal database 
agent_store = InMemoryAgentStore()

@app.get("/health")
async def health_check():
    """
    Health check endpoint to verify the service is running.
    """
    return {"status": "ok", "message": "Service is running"}    
@app.get("/file_content")
async def get_file_content():
    """
    Endpoint to get the content of a file.
    """
    file_name = "Ni_foil"  # Example file name, can be parameterized
    try:
        origin = Path.cwd() / "physics/cif_files"
        cif_file = origin / f"{file_name}.cif"
        if not cif_file.exists():
            raise HTTPException(status_code=404, detail="File not found")   
        with open(cif_file, "r") as file:
            content = file.read()
        logger.info(f"File {file_name} content retrieved successfully.")

        return {"file_name": file_name, "content": content}
    except Exception as e:
        logger.error(f"Error getting file content: {e}")
        raise HTTPException(status_code=500, detail=str(e)) 
    
@app.get("/make_feff")
async def make_feff_endpoint():
    """
    Endpoint to create a FEFF calculation.
    """
    try:
        file_name = "Ni_foil"  
       
        origin = Path.cwd() / "physics/cif_files"
        cif_file = origin / f"{file_name}.cif"
        output_dir = Path.cwd() / "physics/FEFF_paths" / file_name
        path=make_and_run_feff(file_name="Ni_foil", absorber="Ni")

        return {"message": "FEFF calculation created successfully. {str(path)}" }
    except Exception as e:
        logger.error(f"Error creating FEFF calculation: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    
@app.get("/feff_paths")
async def get_feff_paths():
    """
    Endpoint to get the FEFF paths.
    """
    try:
        dat_paths=make_and_run_feff(file_name="Ni_foil", absorber="Ni")
        r_max = 5.0
        verbose = True

        # user feedback is needed here, what are the parameters that the user wants to set? We can provide some initial guesses

        amp = 0.8  # initial guess for the amplitude
        paths=load_paths(
        dat_paths, amp, r_max, verbose=True
    )  # of verbose == True, prints a table with the paths
        result= transform_paths(paths)
        return {"message": "FEFF paths retrieved successfully", "paths": str(result)}
    except Exception as e:
        logger.error(f"Error getting FEFF paths: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    

@app.get("/fit")
async def fit_feff():
    try:
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
    )   
        return {"message": "FEFF fitting completed successfully", "result": str(result)}
    except Exception as e:
        logger.error(f"Error fitting FEFF: {e}")
        raise HTTPException(status_code=500, detail=str(e))





@app.post("/chat")# need conversation ifd 
async def chat_endpoint(req: ChatRequest):
    """
    Endpoint to handle chat messages.
    """
 
    is_new = not req.conversation_id or conversation_store.get(req.conversation_id) is None
    if is_new:
        conversation_id: str = uuid4().hex

    else:
        conversation_id = req.conversation_id  # type: ignore
        # use the old agent



    # Check if agent already exists with agent_id
    if req.agent_id and conversation_store.get(req.agent_id):
        agent_id = agent_store.get(req.agent_id)
        # start the conversation with the existing agent . Take care the prompt! 
    else:
        #todo : add conversation id to the request

        #####place holder start######
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
        content = f""" 
        params: {params}"""
        #####place holer end######


        try:
            # Create a new runner instance
            req.message = req.message.strip()
            name=req.message.split()[0]  # Assuming the first word is the name

          #  file_name = name + ".cif"

           # download_file("test-dr-xas", "cif_file", file_name)  # Download the CIF file from S3 # when upload use objectname : cif_file

            cif_file = "physics/cif_files/" + name + ".cif"  #
            agent = await create_agent(name, cif_file)

           # agent_id store for reuse? 

            result = await Runner.run(agent, content)
            print(result.final_output)
            return result.final_output

        except Exception as e:
            logger.error(f"Error processing chat request: {e} {cif_file}")
            raise HTTPException(status_code=500, detail=str(e))


@app.get("/xafs_database")# 
def xafs_database_endpoint():
    """
    Endpoint to handle XAFS database requests.
    """

    return get_datasets()

@app.get("/xafs/{id}")
def xafs_item_endpoint(id: str):
    """
    Endpoint to handle XAFS item requests.
    """
    file_paths = get_data_by_id(id)
    if file_paths:
        return file_paths
    else:
        raise HTTPException(status_code=404, detail="Item not found")
