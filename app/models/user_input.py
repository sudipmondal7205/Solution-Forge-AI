from pydantic import BaseModel


class UserInput(BaseModel):
    """Raw project requirements captured from the client."""
    business_idea: str
    technology_preference: str
    cloud_preference: str
    expected_daily_traffic: int
    delivery_timeline_months: int
    data_hosting_country: str
