from functools import wraps
import os
from typing import Tuple
import requests

from utils.exceptions import AlreadyExistError, FKNoDeleteUpdateError, FKNotExistError, NotExistError, \
    NotMatchWithSystemError, OpNotPermittedError, UnprocessableEntityError, PermissionDeniedError

SERVE_APP_HOST = os.environ.get('SERVE_APP_HOST', 'localhost')
SERVE_APP_PORT = os.environ.get('SERVE_APP_PORT', 8181)
BASE_URL = f"http://{SERVE_APP_HOST}:{SERVE_APP_PORT}/api/v1"

def handle_error(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        try:
            r = f(*args, **kwargs)
        except Exception as e:
            raise e # TODO
        else:
            js = r.json()
            if r.status_code == 200:
                return js
            elif r.status_code == 520:
                raise AlreadyExistError(**js)
            elif r.status_code == 521:
                raise NotExistError(**js)
            elif r.status_code == 530:
                raise FKNotExistError(**js)
            elif r.status_code == 531:
                raise FKNoDeleteUpdateError(**js)
            elif r.status_code == 540:
                raise OpNotPermittedError(**js)
            elif r.status_code == 550:
                raise NotMatchWithSystemError(**js)
            elif r.status_code == 422:
                # unprocess entity
                raise UnprocessableEntityError()
            elif r.status_code == 403:
                raise PermissionDeniedError(**js)
            else:
                raise

    return decorated


def assemble_url(prefix:str, endpoint: str) -> str:
    return f"{BASE_URL}/{prefix}/{endpoint}"

def plain_get_req(
    prefix:str, 
    endpoint: str, 
    params:dict=None, 
    json_:dict = None,
    data:dict = None,
    headers: dict | None= None,
    access_token: str | None = None,
) -> str:
    base_headers = {
        "Content-Type" : "application/json"
    }
    if access_token:
        base_headers.update(
            {
                "Authorization" : f"Bearer {access_token}"
            }
        )
    if headers:
        base_headers.update(
            **headers
        )
    resp = requests.get(
        url = assemble_url(prefix, endpoint),
        params = params,
        json = json_,
        data = data,
        headers = base_headers
    )
    if resp.status_code == 200:
        return resp.text
    else:
        raise UnprocessableEntityError()

@handle_error
def get_req(
    prefix:str, 
    endpoint: str, 
    access_token: str | None = None,
    headers: dict | None= None,
    params:dict=None, 
    json_:dict = None
) -> dict:
    base_headers = {
        "Content-Type" : "application/json"
    }
    if access_token:
        base_headers.update(
            {
                "Authorization" : f"Bearer {access_token}"
            }
        )
    if headers:
        base_headers.update(
            **headers
        )
    return requests.get(
        url = assemble_url(prefix, endpoint),
        params = params,
        json = json_,
        headers = base_headers
    )

@handle_error
def post_req(
    prefix:str, 
    endpoint: str,
    access_token: str | None = None,
    headers: dict | None= None,
    params:dict=None, 
    data: dict | None = None,
    json_: dict | None = None,
    files: list[Tuple[str, bytes]] | None = None
) -> dict:
    if files is None:
        base_headers = {
            "Content-Type" : "application/json"
        }
    else:
        base_headers = {}
    if access_token:
        base_headers.update(
            {
                "Authorization" : f"Bearer {access_token}"
            }
        )
    if headers:
        base_headers.update(
            **headers
        )
    return requests.post(
            url = assemble_url(prefix, endpoint),
            params = params,
            data = data,
            json = json_,
            headers = base_headers,
            files = files
        )

@handle_error
def put_req(
    prefix:str, 
    endpoint: str,
    access_token: str | None = None,
    headers: dict | None= None,
    params:dict=None, 
    json_:dict = None
) -> dict:
    base_headers = {
        "Content-Type" : "application/json"
    }
    if access_token:
        base_headers.update(
            {
                "Authorization" : f"Bearer {access_token}"
            }
        )
    if headers:
        base_headers.update(
            **headers
        )
    return requests.put(
        url = assemble_url(prefix, endpoint),
        params = params,
        json = json_,
        headers = base_headers
    )

@handle_error
def delete_req(
    prefix:str, 
    endpoint: str,
    access_token: str | None = None,
    headers: dict | None= None,
    params:dict=None, 
    json_:dict = None
) -> dict:
    base_headers = {
        "Content-Type" : "application/json"
    }   
    if access_token:
        base_headers.update(
            {
                "Authorization" : f"Bearer {access_token}"
            }
        )
    if headers:
        base_headers.update(
            **headers
        )
    return requests.delete(
        url = assemble_url(prefix, endpoint),
        params = params,
        json = json_,
        headers = base_headers
    )