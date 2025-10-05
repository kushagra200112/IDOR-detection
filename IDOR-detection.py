import requests
from dataclasses import dataclass, field
from typing import List, Tuple, Literal, Dict

ACtiontype=Literal['state-changing', 'state-preserving']

@dataclass
class role:
    name: str
    rank:int
    cookies: Dict[str, str] = field(default_factory=dict)

@dataclass
class Requesttype:
    method: str
    endpoint: str
    headers: Dict[str, str] = field(default_factory=dict)
    

@dataclass
class Action:
    id: str
    type: ACtiontype
    HTTP_request: Requesttype

@ dataclass
class usecase:
    role: str
    action: Action
    dependencies: List[Tuple[str, str]] = field(default_factory=list) # dependencies in form of [(action_id, role)]
    cancellation: List[Tuple[str, str]] = field(default_factory=list) # cancellation in form of [(action_id, role)]
    
# Static configuration for now

ROLES: List[role] = [
    role("Admin",   rank=2, cookies={"PHPSESSID": "admin_cookie_val"}),   # put real cookie later
    role("Student", rank=1, cookies={"PHPSESSID": "student_cookie_val"}),
    role("Public",  rank=0, cookies={}),
]

ACTIONS: List[Action] = [
    Action(
        id="login",
        type="state-changing",
        HTTP_request=Requesttype(
            method="POST",
            endpoint="/login",
            headers={"username": "{user}", "password": "{pass}"}
        ),
    ),
    Action(
        id="view_course",
        type="state-preserving",
        HTTP_request=Requesttype(
            method="GET",
            endpoint="/courses/{course_id}"
        ),
    ),
    Action(
        id="create_course",
        type="state-changing",
        HTTP_request=Requesttype(
            method="POST",
            endpoint="/api/courses",
            headers={"title": "{title}", "desc": "{desc}"}
        ),
        
    ),
]

ACTION_BY_ID = {a.id: a for a in ACTIONS}


USE_CASES: List[usecase] = [
    usecase(
        role="Student",
        action=ACTION_BY_ID["login"],
    ),
    usecase(
        role="Student",
        action=ACTION_BY_ID["view_course"],
        dependencies=[("login", "Student")],
    ),
    usecase(
        role="Admin",
        action=ACTION_BY_ID["login"],
    ),
    usecase(
        role="Admin",
        action=ACTION_BY_ID["create_course"],
        dependencies=[("login", "Admin")],
    ),
]
# Enumerate roles, actions, and use cases
def index_roles(roles: List[role]) -> Dict[str, role]:
    return {r.name: r for r in roles}

def index_actions(actions: List[Action]) -> Dict[str, Action]:
    ix: Dict[str, Action] = {}
    for a in actions:
        if a.id in ix:
            raise ValueError(f"Duplicate Action id: {a.id}")
        ix[a.id] = a
    return ix

def index_use_cases(ucs: List[usecase]) -> Dict[Tuple[str, str], usecase]:
    ix: Dict[Tuple[str, str], usecase] = {}
    for uc in ucs:
        key = (uc.action.id, uc.role)
        if key in ix:
            raise ValueError(f"Duplicate usecase: {key}")
        ix[key] = uc
    return ix


def enumerate_all() -> None:
    role_ix   = index_roles(ROLES)
    action_ix = index_actions(ACTIONS)
    uc_ix     = index_use_cases(USE_CASES)
    #validate_graph(role_ix, action_ix, uc_ix)

    #print(f"Base URL: {BASE_URL}\n")
    print("Roles:")
    for r in role_ix.values():
        print(f"  - {r.name} (rank={r.rank}) cookies={bool(r.cookies)}")

    print("\nActions:")
    for a in action_ix.values():
        tmpl = a.HTTP_request
        print(f"  - {a.id} [{a.type}] {tmpl.method} {tmpl.endpoint}")

    print("\nUseCases (action, role):")
    for (aid, role), uc in uc_ix.items():
        print(f"  - ({aid}, {role}) deps={uc.dependencies or '-'} cancels={uc.cancellation or '-'}")

if __name__ == "__main__":
    enumerate_all()



