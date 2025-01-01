from pydantic import BaseModel


class _CountryBrief(BaseModel):
    country: str
    iso2: str
    
class _StateBrief(BaseModel):
    state: str
    iso2: str