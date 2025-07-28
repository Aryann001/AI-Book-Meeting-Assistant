from langchain.tools import tool
from pydantic import BaseModel, Field
from email_validator import validate_email, EmailNotValidError


class ValidEmailSchema(BaseModel):
    email: str = Field(description="Email of the user")


def is_valid_email(email: str) -> bool:
    try:
        valid = validate_email(email)
        return True
    except EmailNotValidError as e:
        return False


@tool("validate_email", args_schema=ValidEmailSchema)
def validate_email_tool(email: str):
    """Validate an email"""
    valid = is_valid_email(email)
    if valid:
        return {"success": True, "message": "Email is valid"}
    else:
        return {"success": False, "message": "Email is not valid"}
