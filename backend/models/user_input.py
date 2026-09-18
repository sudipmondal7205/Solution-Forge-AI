"""
User input model — what the client submits for one consultation
(business idea + preferences/constraints).

These 6 fields feed the agent pipeline. We validate them NOW so later
stages never receive junk data.
"""

from pydantic import BaseModel, Field


class UserInput(BaseModel):
    business_idea: str = Field(
        min_length=10,
        description="What the user wants to build.",
    )
    technology_preference: str = Field(
        default="No preference",
        description="e.g. Open-source, Enterprise, No preference.",
    )
    cloud_preference: str = Field(
        default="No preference",
        description="e.g. AWS, Azure, GCP, No preference.",
    )
    expected_daily_traffic: int = Field(
        default=1000,
        ge=0,
        description="Expected daily users/traffic.",
    )
    delivery_timeline_months: int = Field(
        default=3,
        ge=1,
        le=60,
        description="Delivery deadline in months.",
    )
    data_hosting_country: str = Field(
        default="India",
        description="Country where data must be hosted.",
    )