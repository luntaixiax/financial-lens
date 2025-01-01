from functools import wraps
import os
from typing import Any
import requests

from utils.exceptions import AlreadyExistError, FKNoDeleteUpdateError, FKNotExistError, NotExistError, NotMatchWithSystemError, OpNotPermittedError

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
            else:
                raise

    return decorated


def assemble_url(prefix:str, endpoint: str) -> str:
    return f"{BASE_URL}/{prefix}/{endpoint}"

@handle_error
def get_req(prefix:str, endpoint: str, params:dict=None, data:dict = None) -> dict:
    headers = {
        "Content-type" : "application/json"
    }
    return requests.get(
        url = assemble_url(prefix, endpoint),
        params = params,
        json = data,
        headers = headers
    )

@handle_error
def post_req(prefix:str, endpoint: str, params:dict=None, data:dict = None) -> dict:
    headers = {
        "Content-type" : "application/json"
    }
    return requests.post(
            url = assemble_url(prefix, endpoint),
            params = params,
            json = data,
            headers = headers
        )

@handle_error
def put_req(prefix:str, endpoint: str, params:dict=None, data:dict = None) -> dict:
    headers = {
        "Content-type" : "application/json"
    }
    return requests.put(
        url = assemble_url(prefix, endpoint),
        params = params,
        json = data,
        headers = headers
    )

def delete_req(prefix:str, endpoint: str,params:dict=None, data:dict = None) -> dict:
    headers = {
        "Content-type" : "application/json"
    }
    return requests.delete(
        url = assemble_url(prefix, endpoint),
        params = params,
        json = data,
        headers = headers
    )