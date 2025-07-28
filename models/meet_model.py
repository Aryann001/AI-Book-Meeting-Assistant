from pydantic import BaseModel, Field
from datetime import datetime


class MeetSchema(BaseModel):
    """Schema for the database to store the client's meeting information."""

    client_name: str = Field(description="name of the user.")
    client_email: str = Field(description="email of the user.")
    client_project_description: str = Field(description="project or idea description of the user.")
    date: datetime = Field(description="Schedule date and time for the meeting.")
    isCompleted: bool = Field(
        default=False,
        description="Meeting completed or not",
    )
    isVerified: bool = Field(
        default=False,
        description="User is verified or not",
    )
    OTP: int = Field(
        default=None, description="OTP for client's email verification."
    )
