from datetime import datetime, timedelta
from jose import jwt, JWTError, ExpiredSignatureError
from pydantic import ValidationError
from src.app.utils.tools import get_secret
from src.app.model.exceptions import NotExistError, PermissionDeniedError
from src.app.model.user import Token, User
from src.app.dao.user import userDao

def create_access_token(user: User, secret_key: str, 
            algorithm: str="HS256", expires_minutes: int = 15) -> str:
    to_encode = user.model_dump()
    expire = datetime.utcnow() + timedelta(minutes=expires_minutes)
    to_encode.update({"exp": expire}) # type: ignore # this can only be named as exp
    encoded_jwt = jwt.encode(to_encode, secret_key, algorithm=algorithm)
    
    return encoded_jwt

def decode_token(token: str, secret_key: str, algorithm: str="HS256") -> User:
    try:
        payload = jwt.decode(token, secret_key, algorithms=algorithm)
    except ExpiredSignatureError:   
        raise PermissionError("Token expired")
    except JWTError:
        raise PermissionError("Invalid token")
    user = User(
        user_id=payload.get('user_id'), # type: ignore
        username=payload.get('username'), # type: ignore
        is_admin=payload.get('is_admin') # type: ignore
    )
    return user

class AuthService:

    def __init__(self, user_dao: userDao):
        self.user_dao = user_dao

    def login(self, username: str, password: str) -> Token:
        try:
            internal_user = self.user_dao.get_internal_user_by_name(username)
        except NotExistError:
            raise PermissionDeniedError("User not found")
        
        if not internal_user.verify_password(password):
            raise PermissionDeniedError("Wrong password")
        
        auth_config = get_secret()['auth']
        access_token = create_access_token(
            user=User(
                user_id=internal_user.user_id,
                username=username,
                is_admin=internal_user.is_admin
            ),
            secret_key=auth_config['secret_key'],
            algorithm=auth_config['algorithm'],
            expires_minutes=int(auth_config['expires_minutes'])
        )
        return Token(access_token=access_token, token_type="bearer")
    
    def verify_token(self, token: str) -> User:
        auth_config = get_secret()['auth']
        try:
            decoded_token = decode_token(
                token=token,
                secret_key=auth_config['secret_key'],
                algorithm=auth_config['algorithm']
            )
        except ValidationError:
            raise PermissionDeniedError("Cannot parse token")
        except PermissionError as e:
            raise PermissionDeniedError(
                message=str(e),
                details=token
            )
        return decoded_token