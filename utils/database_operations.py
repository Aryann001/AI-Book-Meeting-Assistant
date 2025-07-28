from config.db import db
from datetime import datetime, timedelta
import random
from utils.send_mail import send_email
import os
import asyncio

# Connect to database
db.connect()
mongo_db = db.db

# Collections
Projects = mongo_db["projects"]
Users = mongo_db["users"]
Meetings = mongo_db["meetings"]


# Fetch all projects
def find_all_projects():
    return list(Projects.find({}))


# Fetch single user (first one)
def find_user():
    return Users.find_one({})  # returns dict or None


# Fetch verified meetings
def find_all_meetings():
    return list(Meetings.find({"isVerified": True}))


# Combine them
def find_portfolio_data():
    user = find_user()
    projects = find_all_projects()
    meetings = find_all_meetings()
    return user, projects, meetings


def is_slot_available(date: datetime) -> bool:
    """Checks if a slot is available and is not in the past."""
    # A slot in the past is never available.
    if date < datetime.utcnow():
        return False
    # Check if a meeting already exists at this time
    return Meetings.find_one({"date": date}) is None


def get_alternative_slots():
    """Generates a list of 3 upcoming available slots on future dates."""
    now = datetime.utcnow()
    slots = []
    # Start checking from the next day to avoid suggesting times that are too soon or in the past.
    check_date = now.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(
        days=1
    )

    # Keep searching until we find 3 slots
    while len(slots) < 3:
        # Check standard business hours: 10 AM, 2 PM, 4 PM UTC
        for hour in [10, 14, 16]:
            potential_slot = check_date.replace(hour=hour)
            if is_slot_available(potential_slot):
                # Add 'Z' to indicate UTC time, which is standard for ISO 8601
                slots.append(potential_slot.isoformat() + "Z")
                if len(slots) >= 3:
                    break
        # Move to the next day
        check_date += timedelta(days=1)
    return slots


def book_meeting(client_name, client_email, client_project_description, date: datetime):
    otp = random.randint(1000, 9999)
    Meetings.insert_one(
        {
            "client_name": client_name,
            "client_email": client_email,
            "client_project_description": client_project_description,
            "date": date,
            "isCompleted": False,
            "isVerified": False,
            "OTP": otp,
        }
    )

    # --- Improved Email Content ---
    subject = "Your Verification Code to Confirm Your Meeting with Aryan Baghel"
    content = f"""
Hello {client_name},

Thank you for your interest in meeting with Aryan Baghel.

To confirm your appointment, please use the following One-Time Password (OTP):

**Your OTP is: {otp}**

Please provide this code to the AI assistant in the chat to finalize your booking. This code is valid for the next 10 minutes.

If you did not request this meeting, please disregard this email.

Best regards,
Aryan Baghel's AI Assistant
"""
    send_email(client_email, subject, content)
    return otp


async def verify_meeting(client_email, otp: int) -> bool:
    meeting = Meetings.find_one({"client_email": client_email, "OTP": otp})
    if meeting:
        Meetings.update_one({"_id": meeting["_id"]}, {"$set": {"isVerified": True}})

        # --- Email to the Client ---
        client_name = meeting["client_name"]
        meeting_date = meeting["date"].strftime("%A, %B %d, %Y")
        meeting_time = meeting["date"].strftime("%I:%M %p UTC")
        project_desc = meeting["client_project_description"]

        client_subject = "Your Meeting with Aryan Baghel is Confirmed!"
        client_content = f"""
Hello {client_name},

This email confirms that your meeting with Aryan Baghel has been successfully booked.

Here are the details:
- **Date:** {meeting_date}
- **Time:** {meeting_time}
- **Topic:** {project_desc}

A separate calendar invitation with a video conference link will be sent to you shortly.

If you need to reschedule or cancel, please return to the chat on the website and our AI assistant will be happy to help.

We look forward to speaking with you!

Best regards,
Aryan Baghel's AI Assistant
"""
        send_email(client_email, client_subject, client_content)

        # --- Notification Email to Aryan ---
        aryan_subject = f"✅ New Confirmed Meeting with {client_name}"
        aryan_content = f"""
Hello Aryan,

A new meeting has been confirmed and added to your schedule.

Client Details:
- **Name:** {client_name}
- **Email:** {client_email}
- **Project:** {project_desc}

Meeting Details:
- **Date:** {meeting_date}
- **Time:** {meeting_time}

This has been added to the database.
"""
        print("Waiting for 2 seconds before sending notification...")
        await asyncio.sleep(2)

        send_email(os.environ["SMTP_USER"], aryan_subject, aryan_content)

        return True
    return False


def delete_unverified_meeting(client_email: str):
    Meetings.delete_many({"client_email": client_email, "isVerified": False})


def get_client_details(client_email: str):
    return Meetings.find_one({"client_email": client_email})


def is_client_exist(client_email: str):
    client = Meetings.find_one({"client_email": client_email})

    if not client:
        return False
    else:
        return True


async def reschedule(client_email, dt: datetime) -> bool:
    meeting = Meetings.find_one({"client_email": client_email})
    if meeting:
        Meetings.update_one({"_id": meeting["_id"]}, {"$set": {"date": dt}})

        # --- Email to the Client ---
        client_name = meeting["client_name"]
        new_date = dt.strftime("%A, %B %d, %Y")
        new_time = dt.strftime("%I:%M %p UTC")

        client_subject = "Your Meeting with Aryan Baghel has been Rescheduled"
        client_content = f"""
Hello {client_name},

This email confirms that your meeting with Aryan Baghel has been successfully rescheduled.

Here are your new meeting details:
- **New Date:** {new_date}
- **New Time:** {new_time}

Your calendar invitation will be updated to reflect this change.

If you have any further questions, please feel free to chat with our AI assistant on the website.

Best regards,
Aryan Baghel's AI Assistant
"""
        send_email(client_email, client_subject, client_content)

        # --- Notification Email to Aryan ---
        aryan_subject = f"🔄 Meeting Rescheduled by {client_name}"
        aryan_content = f"""
Hello Aryan,

A client has rescheduled their meeting.

Client Details:
- **Name:** {client_name}
- **Email:** {client_email}

Updated Meeting Details:
- **New Date:** {new_date}
- **New Time:** {new_time}

The database has been updated.
"""
        print("Waiting for 2 seconds before sending notification...")
        await asyncio.sleep(2)

        send_email(os.environ["SMTP_USER"], aryan_subject, aryan_content)

        return True
    return False
