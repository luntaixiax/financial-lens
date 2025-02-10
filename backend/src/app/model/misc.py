from functools import partial
from pydantic import BaseModel, Field
from src.app.utils.tools import id_generator

class File(BaseModel):
    file_id: str = Field(
        default_factory=partial(
            id_generator,
            prefix='file-',
            length=12,
        ),
        frozen=True,
    )
    filename: str
    filehash: str

class _CountryBrief(BaseModel):
    country: str
    iso2: str
    
class _StateBrief(BaseModel):
    state: str
    iso2: str