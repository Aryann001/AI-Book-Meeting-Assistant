from fastapi import APIRouter, HTTPException, Request
from utils.limiter import limiter
from controllers.chat import stream_chat_response
from pydantic import BaseModel
from fastapi.responses import StreamingResponse

router = APIRouter(prefix="/chat")


class ChatRequest(BaseModel):
    user_input: str
    thread_id: str


@router.post("/stream")
@limiter.limit("1/second")
async def chat_stream(body: ChatRequest, request: Request):
    if not body.user_input:
        raise HTTPException(status_code=400, detail="User input cannot be empty.")

    return StreamingResponse(
        stream_chat_response(request, body.user_input, body.thread_id),
        media_type="text/event-stream",
    )
