from datetime import datetime, timedelta
from jose import jwt, JWTError
from src.app.utils.tools import get_secret
from src.app.model.exceptions import PermissionDeniedError
from src.app.model.user import Token, UserMeta
from src.app.dao.user import userDao

def create_access_token(user_meta: UserMeta, secret_key: str, 
            algorithm: str="HS256", expires_minutes: int = 15) -> str:
    to_encode = user_meta.model_dump()
    expire = datetime.utcnow() + timedelta(minutes=expires_minutes)
    to_encode.update({"exp": expire}) # type: ignore # this can only be named as exp
    encoded_jwt = jwt.encode(to_encode, secret_key, algorithm=algorithm)
    
    return encoded_jwt

def decode_token(token: str, secret_key: str, algorithm: str="HS256") -> UserMeta:
    try:
        payload = jwt.decode(token, secret_key, algorithms=algorithm)
    except JWTError:
        raise PermissionError("Invalid token")
    return UserMeta(
        username=payload.get('username'), # type: ignore
        is_admin=payload.get('is_admin') # type: ignore
    )

class AuthService:

    def __init__(self, user_dao: userDao):
        self.user_dao = user_dao

    def login(self, username: str, password: str) -> Token:
        internal_user = self.user_dao.get_internal_user_by_name(username)
        
        if not internal_user.verify_password(password):
            raise PermissionDeniedError("Wrong password")
        
        auth_config = get_secret()['auth']
        access_token = create_access_token(
            user_meta=UserMeta(
                username=username,
                is_admin=internal_user.is_admin
            ),
            secret_key=auth_config['secret_key'],
            algorithm=auth_config['algorithm'],
            expires_minutes=auth_config['expires_minutes']
        )
        return Token(access_token=access_token, token_type="bearer")
    
    def verify_token(self, token: str) -> UserMeta:
        auth_config = get_secret()['auth']
        try:
            decoded_token = decode_token(
                token=token,
                secret_key=auth_config['secret_key'],
                algorithm=auth_config['algorithm']
            )
        except PermissionError:
            raise PermissionDeniedError(
                message="Invalid token",
                details=token
            )
        
        username = decoded_token.get("username") # type: ignore
        if username is None:
            raise PermissionDeniedError(
                message="Invalid token",
                details=token
            )
        
        return decoded_token