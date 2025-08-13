from fastapi import APIRouter, HTTPException, Request, Query
from utils.limiter import limiter
from controllers.chat import stream_chat_response
# The pydantic model is no longer needed for a GET request
# from pydantic import BaseModel 
from fastapi.responses import StreamingResponse

router = APIRouter(prefix="/chat")

# The ChatRequest model is removed as we are now using query parameters

@router.get("/stream") # Changed from @router.post to @router.get
@limiter.limit("1/second")
# The function now accepts 'user_message' and 'thread_id' as query parameters
# instead of a request body.
async def chat_stream(
    request: Request,
    user_message: str = Query(..., min_length=1), # Use Query for validation
    thread_id: str = Query(...)
):
    """
    Handles a GET request to stream chat responses using Server-Sent Events.
    Accepts user_message and thread_id as URL query parameters.
    Example: /chat/stream?user_message=Hello&thread_id=12345
    """
    # The check for empty input is now handled by Query(..., min_length=1)
    # but you can keep an explicit check if you prefer.
    if not user_message:
        raise HTTPException(status_code=400, detail="user_message cannot be empty.")

    # Call the controller with the query parameters
    return StreamingResponse(
        stream_chat_response(request, user_message, thread_id),
        media_type="text/event-stream",
    )
