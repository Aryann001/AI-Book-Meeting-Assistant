import os
from typing import TypedDict, Annotated
from dotenv import load_dotenv
from langgraph.graph import StateGraph, START, END, add_messages
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import AIMessage, HumanMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.prebuilt import ToolNode
from langchain_tavily import TavilySearch
import aiosqlite  # Use the async version of sqlite

from utils.database_operations import find_portfolio_data
from utils.meeting_tools import (
    check_slot_availability,
    book_meeting_tool,
    verify_meeting_tool,
    decline_meeting_tool,
    get_client_details_tool,
    is_user_exist_tool,
    reschedule_tool,
)
from utils.validate_email import validate_email_tool

load_dotenv()

# --- Define Components (but don't initialize async parts) ---


# ✅ --- Graph State ---
class AgentState(TypedDict):
    messages: Annotated[list, add_messages]


# ✅ --- Tools and LLM ---
search_tool = TavilySearch(max_results=1)
tools = [
    check_slot_availability,
    book_meeting_tool,
    verify_meeting_tool,
    decline_meeting_tool,
    validate_email_tool,
    search_tool,
    get_client_details_tool,
    is_user_exist_tool,
    reschedule_tool,
]
llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash", temperature=0.5).bind_tools(
    tools=tools
)


# ✅ --- System Prompt Definition ---
def get_system_prompt():
    user, projects, meetings = find_portfolio_data()
    if not user and not projects:
        print("⚠️ WARNING: No user or project data found in the database.")

    user_context = "No user data found in the database."
    if user:
        # Get the list of stack objects, or an empty list if it doesn't exist
        stack_list = user.get("stack", [])

        # Use a list comprehension to pull the 'description' string from each object
        stack_descriptions = [item.get("description", "N/A") for item in stack_list]

        # Now, join the list of strings
        stack_str = ", ".join(stack_descriptions)

        # Build the final context string
        user_context = f"Name: {user.get('name', 'N/A')}\nTitle: {user.get('title', 'N/A')}\nDescription: {user.get('description', 'N/A')}\nStack: {stack_str}"

    projects_context = "No projects found in the database."
    if projects:
        projects_context = "\n".join(
            [
                f"- {p.get('title', 'Untitled')}: {p.get('description', 'No description')}"
                for p in projects
            ]
        )

    full_context = f"USER DATA:\n{user_context}\n\nPROJECTS:\n{projects_context}"

    return f"""
You are Aryan Baghel's specialized assistant. Your persona is professional, friendly, and highly conversational. You are an intelligent aide, not a robot.

**Your Knowledge Base:**
You must base your answers on the following context. If information is missing, politely state that you don't have that detail.
{full_context}

---
**Core Conversational Rules:**
- **Creative & Natural:** Avoid canned responses. Your goal is to have a flowing, human-like conversation.
- **Greeting Command:** DO NOT greet the user unless their first message is a greeting. For any other opener, answer their question directly.
- **No Examples for User:** When asking for information (like name, email, or time), pose a direct, open-ended question. DO NOT provide the user with examples like "e.g., 'tomorrow afternoon'".
- **Act on Behalf of Aryan:** When asked about Aryan's approach, synthesize an answer from his perspective using the provided context.

---
**The Intelligent Booking & Rescheduling Process:**

**Step 1: Smart Onboarding**
When a user wants to book or reschedule, you MUST follow this sequence precisely:
- **A. First, ask for their email address.**
- **B. Once you receive the email, you MUST first call `validate_email_tool` to ensure the format is correct.**
- **C. Only after the email is validated**, you MUST then immediately call `is_user_exist_tool`.
- **If user exists (`is_user_exist_tool` returns success):** Call `get_client_details_tool` to get their name. Greet them warmly by name (e.g., "Welcome back, [User's Name]!"). Then, ask if they want to book a NEW meeting or RESCHEDULE their existing one.
- **If user does not exist:** Proceed to the standard booking flow by asking for their full name.

**Step 2: Standard Booking Flow (for New Users)**
- **Gather Details Sequentially:** You already have the email. Now ask for their name, then their project description. ONE AT A TIME.

**Step 3: Finding a Time (for Booking or Rescheduling)**
- Ask the user for their preferred time.
- **Internal Process:** Use `TavilySearch` for the current time, then call `check_slot_availability` with the converted ISO string.
- **Communicate Availability:** If the slot is open, you MUST ask for permission to proceed. **CRITICAL:** Your response MUST be a question like, "Good news! That time is available. Shall I go ahead and book it for you?" and then you MUST STOP and wait for their reply.

**Step 4: The Booking/Rescheduling Action**
- **CRITICAL:** Only after the user explicitly agrees (e.g., "Yes, please do"), you will call the appropriate tool:
    - For new meetings, call `book_meeting_tool`.
    - For rescheduling, call `reschedule_tool`.

**Step 5: The OTP Verification (for New Bookings Only)**
- After `book_meeting_tool` is called, announce that a verification code has been sent.
- The next user message is the OTP. Your sole focus is to call `verify_meeting_tool`.

**Step 6: Post-Confirmation Behavior**
- After a successful `verify_meeting` or `reschedule_tool` call, the process is COMPLETE.
- **Your New Goal:** Be a helpful assistant for any follow-up questions.
- **CRITICAL RULE:** DO NOT suggest booking or rescheduling again. If the user asks, remind them they already have a confirmed meeting.
"""


# --- Graph Definition ---
def build_graph():
    agent_system_prompt = get_system_prompt()
    agent_system_template = ChatPromptTemplate.from_messages(
        [
            ("system", agent_system_prompt),
            MessagesPlaceholder(variable_name="messages"),
        ]
    )
    agent = agent_system_template | llm

    async def agent_node(state: AgentState):
        # Use .ainvoke() for async tool calls
        result = await agent.ainvoke(state)
        return {"messages": [result]}

    tool_node = ToolNode(tools=tools)

    def should_continue(state: AgentState):
        last_message = state["messages"][-1]
        if hasattr(last_message, "tool_calls") and len(last_message.tool_calls) > 0:
            return "tools"
        return END

    graph = StateGraph(AgentState)
    graph.add_node("agent", agent_node)
    graph.add_node("tools", tool_node)
    graph.set_entry_point("agent")
    graph.add_conditional_edges("agent", should_continue, {"tools": "tools", END: END})
    graph.add_edge("tools", "agent")
    return graph


# --- ASYNC INITIALIZATION FUNCTION ---
# This function will be called from our async controller to create the app instance.
async def get_app(conn: aiosqlite.Connection):
    checkpointer = AsyncSqliteSaver(conn=conn)

    graph = build_graph()

    # Compile the graph with the async checkpointer
    app = graph.compile(checkpointer=checkpointer)
    return app
