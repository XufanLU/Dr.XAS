# FastAPi + html as web app framework . (lightweight, seemlessly interaction with the agent(in python))
#https://ai.pydantic.dev/examples/chat-app/


import fastapi
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
import logfire
from pathlib import Path

logfire.configure(send_to_logfire='if-token-present')


THIS_DIR = Path(__file__).parent


app = fastapi.FastAPI()
app.mount("/static", StaticFiles(directory="webapp/static"), name="static")
logfire.instrument_fastapi(app)


@app.get('/')
async def index() -> FileResponse:
    return FileResponse((THIS_DIR / 'chat_app.html'), media_type='text/html')


if __name__ == '__main__':
    import uvicorn

    uvicorn.run(
        'main:app', reload=True, reload_dirs=[str(THIS_DIR)]
    )