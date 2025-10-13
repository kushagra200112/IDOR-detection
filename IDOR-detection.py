import requests
from dataclasses import dataclass, field
from typing import List, Tuple, Literal, Dict, Optional
import uuid
from typing import Set, Iterable

ACtiontype=Literal['state-changing', 'state-preserving']
UCKey = Tuple[str, str]  # (action_id, role)
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
    
# creation of 2 groupf of users so that each user must have its own HTTP session so state (auth cookies, CSRF tokens, navigational context) does not bleed between tests.
@dataclass
class User:
    """Concrete user instance bound to a role with its own HTTP session."""
    id: str
    role: role
    session: requests.Session

def _make_session(base_headers: Optional[Dict[str, str]] = None,
                  cookies: Optional[Dict[str, str]] = None) -> requests.Session:
    s = requests.Session()
    if base_headers:
        s.headers.update(base_headers)
    if cookies:
        s.cookies.update(dict(cookies))  # copy to avoid shared refs
    return s

def _create_user_for_role(r: role, label: str) -> User:
    """
    Create a concrete user for a given role.
    `label` helps distinguish groups (e.g., 'G1' vs 'G2') in logs.
    """
    return User(
        id=f"{r.name}-{label}-{uuid.uuid4().hex[:8]}",
        role=r,
        session=_make_session(
            base_headers={"User-Agent": f"IDOR-Scanner/0.1 (+{r.name}/{label})"},
            cookies=r.cookies,
        ),
    )

def create_two_user_groups(roles_ix: Dict[str, role]) -> Tuple[Dict[str, User], Dict[str, User]]:
    """
    Returns (group1, group2), each a dict: role_name -> User.
    Each user has an isolated requests.Session (separate cookies/state).
    """
    group1: Dict[str, User] = {}
    group2: Dict[str, User] = {}
    for rname, r in roles_ix.items():
        group1[rname] = _create_user_for_role(r, "G1")
        group2[rname] = _create_user_for_role(r, "G2")
    return group1, group2
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


def _uc_key(uc: usecase) -> UCKey:
    return (uc.action.id, uc.role)

def build_uc_graph(ucs: List[usecase]) -> Tuple[
    Dict[UCKey, usecase],                # uc_by_key
    Dict[UCKey, Set[UCKey]],             # deps: uc -> set(prereq uc keys)
    Dict[UCKey, Set[UCKey]],             # cancels: uc -> set(uc keys it cancels)
    Dict[UCKey, Set[UCKey]]              # dependents: uc -> set(ucs that depend on it)
]:
    uc_by_key: Dict[UCKey, usecase] = {}
    for uc in ucs:
        k = _uc_key(uc)
        if k in uc_by_key:
            raise ValueError(f"Duplicate use case key: {k}")
        uc_by_key[k] = uc

    deps: Dict[UCKey, Set[UCKey]] = {k: set() for k in uc_by_key}
    cancels: Dict[UCKey, Set[UCKey]] = {k: set() for k in uc_by_key}
    dependents: Dict[UCKey, Set[UCKey]] = {k: set() for k in uc_by_key}

    # resolve dependency and cancellation pairs to UC keys
    def _resolve_pairs(pairs: Iterable[Tuple[str, str]]) -> Set[UCKey]:
        out = set()
        for aid, role_name in pairs:
            key = (aid, role_name)
            if key not in uc_by_key:
                print(f"Use case dependency/cancellation refers to unknown use case: {key}")
                continue
            out.add(key)
        return out

    for k, uc in uc_by_key.items():
        # dependencies (prerequisites)
        deps[k] = _resolve_pairs(uc.dependencies)
        # cancellations
        cancels[k] = _resolve_pairs(uc.cancellation)

    # build reverse edges (dependents) for counting “satisfied dependencies” metric
    for k, pres in deps.items():
        for p in pres:
            if p in dependents:
                dependents[p].add(k)

    return uc_by_key, deps, cancels, dependents

def traverse_use_case_graph(ucs: List[usecase]) -> List[UCKey]:
    uc_by_key, deps, cancels, dependents = build_uc_graph(ucs)

    all_keys: Set[UCKey] = set(uc_by_key.keys())
    visited: Set[UCKey] = set()
    canceled: Set[UCKey] = set()  # UCs removed due to cancellation
    UCL: List[UCKey] = []

    def is_available(k: UCKey) -> bool:
        if k in visited or k in canceled:
            return False
        # available if all prereqs are visited (ignoring ones that were canceled)
        needed = {p for p in deps[k] if p not in canceled}
        return needed.issubset(visited)

    def count_cancels(k: UCKey) -> int:
        # how many *unvisited* UCs would be canceled if we execute k now
        return len([x for x in cancels[k] if x in all_keys and x not in visited and x not in canceled])

    def count_satisfied_deps(k: UCKey) -> int:
        # how many remaining UCs currently have k as an unmet prerequisite
        c = 0
        for u in dependents.get(k, ()):
            if u in visited or u in canceled:
                continue
            # If k is among dependencies and is not yet visited, executing k satisfies that edge.
            if k in deps[u]:
                c += 1
        return c

    # Initial availability
    def gather_available() -> List[UCKey]:
        return sorted([k for k in all_keys if is_available(k)], key=lambda t: (t[0], t[1]))

    available = gather_available()

    # Main loop
    while True:
        # stop when all remaining UCs are either visited or canceled
        remaining = [k for k in all_keys if k not in visited and k not in canceled]
        if not remaining:
            break

        # refresh available
        available = gather_available()

        if not available:
            # No available UCs left but some remain -> inconsistent graph (e.g., circular deps or canceled prereqs).
            # Strategy: pick any nonvisited UC with the smallest number of unmet deps (to make progress).
            candidates = sorted(
                remaining,
                key=lambda k: (len([p for p in deps[k] if p not in visited]), k[0], k[1])
            )
            chosen = candidates[0]
        else:
            #   - minimize cancels
            #   - maximize satisfied deps
            #   - deterministic tiebreaker
            def score(k: UCKey):
                return (count_cancels(k), -count_satisfied_deps(k), k[0], k[1])

            chosen = sorted(available, key=score)[0]

        # "Execute" chosen UC: record, mark visited
        UCL.append(chosen)
        visited.add(chosen)

        # applying cancellations made by chosen UC
        for victim in cancels.get(chosen, ()):
            if victim not in visited:
                canceled.add(victim)
                for w in deps:
                    if victim in deps[w]:
                        deps[w].discard(victim)

        # Loop continues; availability recalculated at top

    return UCL


def print_ucl(ucl: List[UCKey]) -> None:
    print("\nUse Case Execution List (UCL):")
    for i, (aid, rname) in enumerate(ucl, 1):
        print(f"  {i:02d}. ({aid}, {rname})")
        
if __name__ == "__main__":
    enumerate_all()
    role_ix = index_roles(ROLES)
    G1, G2 = create_two_user_groups(role_ix)

    print("\nUser Groups (Step 3):")
    print("Group 1:")
    for name, user in G1.items():
        # Show minimal cookie info for sanity; real cookies will come after actual logins
        ck = dict(user.session.cookies)
        print(f"  - {name}: user_id={user.id} cookies={ck or '-'}")

    print("Group 2:")
    for name, user in G2.items():
        ck = dict(user.session.cookies)
        print(f"  - {name}: user_id={user.id} cookies={ck or '-'}")
    
    # Traverse graph per IV-C and print UCL
    UCL = traverse_use_case_graph(USE_CASES)
    print_ucl(UCL)

