from functools import partial
from pydantic import Field, computed_field
from src.app.utils.tools import id_generator, pwd_context
from src.app.utils.base import EnhancedBaseModel

class Token(EnhancedBaseModel):
    access_token: str
    token_type: str
    
class User(EnhancedBaseModel):
    
    user_id: str = Field(
        default_factory=partial( # type: ignore
            id_generator,
            prefix='usr-',
            length=10,
            only_alpha_numeric=True, # need to be only alpha numeric for user id
        ),
        frozen=True,
    )
    username: str = Field(max_length=20)
    is_admin: bool = Field(default=False)
    
class UserInternalRead(User):
    hashed_password: str
    
    def verify_password(self, password: str) -> bool:
        return pwd_context.verify(password, self.hashed_password) # type: ignore
    
class UserCreate(User):
    password: str = Field(min_length=8, max_length=20)
    
    @computed_field
    def hashed_password(self) -> str:
        return pwd_context.hash(self.password)

class UserRegister(EnhancedBaseModel):
    username: str = Field(max_length=20)
    password: str = Field(min_length=8, max_length=20)
