from functools import partial
import hashlib
from pydantic import BaseModel, ConfigDict, Field, model_validator, computed_field
from src.app.utils.tools import id_generator

class FileWrapper(BaseModel):
    file_id: str = Field(
        default_factory=partial( # type: ignore
            id_generator,
            prefix='file-',
            length=12,
        ),
        frozen=True,
    )
    filename: str
    content: str
    
    @computed_field()
    def filehash(self) -> str:
        return hashlib.md5(self.filename.encode()).hexdigest() # TODO: find efficient way to hash content
    

class _CountryBrief(BaseModel):
    country: str
    iso2: str
    
class _StateBrief(BaseModel):
    state: str
    iso2: str