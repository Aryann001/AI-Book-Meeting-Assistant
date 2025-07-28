# chat-app/utils/meeting_tools.py
from langchain.tools import tool
from pydantic import BaseModel, Field
from datetime import datetime
from utils.database_operations import (
    is_slot_available,
    get_alternative_slots,
    book_meeting,
    verify_meeting,
    delete_unverified_meeting,
    get_client_details,
    is_client_exist,
    reschedule,
)


class CheckSlotInput(BaseModel):
    """Input for the check_slot_availability tool."""

    datetime_str: str = Field(
        description="The proposed meeting date and time in a strict ISO 8601 format (e.g., '2024-08-15T14:30:00')."
    )


@tool("check_slot_availability", args_schema=CheckSlotInput)
def check_slot_availability(datetime_str: str):
    """
    Checks if a specific date and time slot is available for a meeting.
    The AI must first determine the current time to correctly interpret user requests like 'tomorrow'.
    """
    try:
        dt = datetime.fromisoformat(datetime_str)
        if is_slot_available(dt):
            return {"available": True, "slot": datetime_str}
        else:
            return {"available": False, "suggestions": get_alternative_slots()}
    except ValueError:
        return {
            "error": "Invalid datetime format. The AI must provide a string in YYYY-MM-DDTHH:MM:SS format."
        }


class BookMeetingInput(BaseModel):
    """Input for the book_meeting_tool."""

    client_name: str = Field(
        description="The full name of the person booking the meeting."
    )
    client_email: str = Field(
        description="The email address of the person booking the meeting."
    )
    client_project_description: str = Field(
        description="A brief description of the user's project or idea."
    )
    datetime_str: str = Field(
        description="The confirmed meeting date and time in ISO format (e.g., '2025-07-25T14:30:00'). This must be a slot previously confirmed as available."
    )


@tool("book_meeting", args_schema=BookMeetingInput)
def book_meeting_tool(
    client_name: str,
    client_email: str,
    client_project_description: str,
    datetime_str: str,
):
    """
    Books a meeting for a specific date and time after confirming slot availability.
    This action will trigger an OTP to be sent to the user's email.
    """
    try:
        dt = datetime.fromisoformat(datetime_str)
        book_meeting(client_name, client_email, client_project_description, dt)
        return {
            "status": "tentative",
            "message": f"A verification OTP has been sent to {client_email}.",
        }
    except ValueError:
        return {
            "error": "Invalid datetime format. The AI must provide a string in YYYY-MM-DDTHH:MM:SS format."
        }


class VerifyMeetingInput(BaseModel):
    """Input for the verify_meeting_tool."""

    client_email: str = Field(
        description="The user's email address to identify the meeting to verify."
    )
    otp: int = Field(description="The One-Time Password (OTP) provided by the user.")


@tool("verify_meeting", args_schema=VerifyMeetingInput)
async def verify_meeting_tool(client_email: str, otp: int):
    """Verifies a booked meeting using the OTP sent to the user's email."""
    if await verify_meeting(client_email, otp):
        return {
            "status": "confirmed",
            "message": "Your meeting has been confirmed successfully!",
        }
    return {
        "status": "failed",
        "message": "The OTP provided is incorrect. Please try again.",
    }


class DeclineMeetingInput(BaseModel):
    """Input for the decline_meeting_tool."""

    client_email: str = Field(
        description="The email of the user whose unverified meeting should be cancelled."
    )


@tool("decline_meeting", args_schema=DeclineMeetingInput)
def decline_meeting_tool(client_email: str):
    """Cancels a meeting that has not yet been verified by OTP."""
    delete_unverified_meeting(client_email)
    return {
        "status": "declined",
        "message": "The meeting has been cancelled as requested.",
    }


class GetClientDetailsInput(BaseModel):
    """Input for the get_client_details."""

    client_email: str = Field(
        description="The email of the user to get all there details"
    )


@tool("get_client_details", args_schema=GetClientDetailsInput)
def get_client_details_tool(client_email: str):
    """Get all the information of the user based on there email"""
    client = get_client_details(client_email)

    if not client:
        return {"success": False, "message": "User not found"}
    return {
        "success": True,
        "message": "User retrieved successfully",
        "user_info": client,
    }


class IsUserExistInput(BaseModel):
    """Input for the is_user_exist."""

    client_email: str = Field(
        description="The email of the user to check whether they exist or not"
    )


@tool("is_user_exist", args_schema=IsUserExistInput)
def is_user_exist_tool(client_email: str):
    """Check where the user already exist and have booked a meeting"""
    exist = is_client_exist(client_email)

    if not exist:
        return {"success": False, "message": "User not found"}
    return {
        "success": True,
        "message": "User found",
    }


class RescheduleInput(BaseModel):
    """Input for the reschedule."""

    client_email: str = Field(
        description="The user's email address to identify the meeting to reschedule."
    )
    datetime_str: str = Field(
        description="The confirmed rescheduled meeting date and time in ISO format (e.g., '2025-07-25T14:30:00'). This must be a slot previously confirmed as available."
    )


@tool("reschedule", args_schema=RescheduleInput)
async def reschedule_tool(client_email: str, datetime_str: str):
    """Reschedule the meeting"""
    try:
        # ✅ FIX: Convert the string to a datetime object before passing it
        dt = datetime.fromisoformat(datetime_str)
        if await reschedule(client_email, dt): # Pass the datetime object here
            return {
                "status": "confirmed",
                "message": "Your meeting has been rescheduled successfully!",
            }
        return {
            "status": "failed",
            "message": "Something went wrong. Please try again.",
        }
    except ValueError:
        return {
            "error": "Invalid datetime format. The AI must provide a string in YYYY-MM-DDTHH:MM:SS format."
        }