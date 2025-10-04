import requests
from dataclasses import dataclass
from typing import List, Tuple, Literal, Dict, Field

ACtiontype=Literal['state-changing', 'state-preserving']

@dataclass
class role:
    name: str
    cookies: Dict[str, str] = Field(default_factory=dict)
    role:str

@dataclass
class Requesttype:
    method: str
    endpoint: str
    headers: Dict[str, str] = Field(default_factory=dict)
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
        representative=Requesttype(
            method="POST",
            path_template="/login",
            body_template={"username": "{user}", "password": "{pass}"}
        ),
        description="Authenticate a user"
    ),
    Action(
        id="view_course",
        type="state-preserving",
        representative=Requesttype(
            method="GET",
            path_template="/courses/{course_id}"
        ),
        description="View course details page"
    ),
    Action(
        id="create_course",
        type="state-changing",
        representative=Requesttype(
            method="POST",
            path_template="/api/courses",
            body_template={"title": "{title}", "desc": "{desc}"}
        ),
        description="Create a new course (Admin only)"
    ),
]

USE_CASES: List[usecase] = [
    usecase("login",         role="Student"),
    usecase("view_course",   role="Student", deps=[("login", "Student")]),
    usecase("login",         role="Admin"),
    usecase("create_course", role="Admin",   deps=[("login", "Admin")]),
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
        key = (uc.action_id, uc.role)
        if key in ix:
            raise ValueError(f"Duplicate usecase: {key}")
        ix[key] = uc
    return ix


def enumerate_all() -> None:
    role_ix   = index_roles(ROLES)
    action_ix = index_actions(ACTIONS)
    uc_ix     = index_use_cases(USE_CASES)
    #validate_graph(role_ix, action_ix, uc_ix)

    print(f"Base URL: {BASE_URL}\n")
    print("Roles:")
    for r in role_ix.values():
        print(f"  - {r.name} (rank={r.rank}) cookies={bool(r.cookies)}")

    print("\nActions:")
    for a in action_ix.values():
        tmpl = a.representative
        print(f"  - {a.id} [{a.type}] {tmpl.method} {tmpl.path_template}")

    print("\nUseCases (action, role):")
    for (aid, role), uc in uc_ix.items():
        print(f"  - ({aid}, {role}) deps={uc.deps or '-'} cancels={uc.cancels or '-'}")

if __name__ == "__main__":
    enumerate_all()
