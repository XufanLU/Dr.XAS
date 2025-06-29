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
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from uuid import uuid4
from agent import create_agent

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

# CORS configuration (adjust as needed for deployment)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)




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
            cif_file = "physics/cif_files/" + name + ".cif"  #
            agent = await create_agent(name, cif_file)
           # agent_id store for reuse? 

            result = await Runner.run(agent, content)
            print(result.final_output)
            return result.final_output

        except Exception as e:
            logger.error(f"Error processing chat request: {e}")
            raise HTTPException(status_code=500, detail=str(e))
