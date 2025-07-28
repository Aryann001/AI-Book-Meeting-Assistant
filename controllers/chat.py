# chat_app/controllers/chat.py
from fastapi import Request
import json
from langchain_core.messages import AIMessageChunk, HumanMessage


# Controller
async def stream_chat_response(request: Request, user_message: str, thread_id: str):
    """
    This async generator calls the LangGraph agent and streams back the response.
    """
    # Get the initialized app from our lifespan context
    chat_app = request.app.state.chat_app
    if not chat_app:
        # This is a safeguard in case the app didn't initialize correctly
        raise RuntimeError("Application is not initialized. Check server logs.")

    try:
        input_data = {"messages": [HumanMessage(content=user_message)]}
        # print("thread_id : ", thread_id)
        config = {"configurable": {"thread_id": thread_id}}

        # Asynchronously stream events from the LangGraph application
        async for event in chat_app.astream_events(
            input_data, version="v2", config=config
        ):
            # We are interested in the 'on_chat_model_stream' events which contain the AI's content
            if event["event"] == "on_chat_model_stream":
                chunk = event["data"]["chunk"]
                if isinstance(chunk, AIMessageChunk) and chunk.content:
                    # Format the data as a Server-Sent Event (SSE) and yield it.
                    # This is the standard format for web streaming.
                    yield f"data: {json.dumps({'event': 'data', 'data': chunk.content})}\n\n"

        # After the main stream is finished, send a final 'end' event
        yield f"data: {json.dumps({'event': 'end'})}\n\n"

    except Exception as e:
        print(f"An error occurred during the stream for thread {thread_id}: {e}")
        # Send a specific error event to the client if something goes wrong
        error_event = {
            "event": "error",
            "data": "An error occurred while processing your request.",
        }
        yield f"data: {json.dumps(error_event)}\n\n"
