import requests
from dataclasses import dataclass
from typing import List, Tuple, Literal, Dict, Field

ACtiontype=Literal['state-changing', 'state-preserving']

@dataclass
class role:
    name: str
    cookie: str
    role:str

@dataclass
class Requesttype:
    method: str
    endpoint: str
    headers: Dict[str, str] = Field(default_factory=dict)

@dataclass
class Action:
    HTTP_request: Requesttype
    type: ACtiontype
    id: str

@ dataclass
class usecase:
    role: str
    action: Action
    dependencies: List[Tuple[str, str]] = Field(default_factory=list) # dependencies in form of [(action_id, role)]
    cancellation: List[Tuple[str, str]] = Field(default_factory=list) # cancellation in form of [(action_id, role)]
    

    
def get_headers(url):
    response=requests.get(url)

    print(response.headers)
    return (response.headers)

get_headers("https://github.com/kushagra200112/IDOR-detection/commits/main/IDOR-detection.py")
