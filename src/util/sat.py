from pysat.card import CardEnc, EncType

type Atom = int
type Clause = list[Atom]
type Formula = list[Clause]

next_id: Atom = 1
atoms: dict[str, Atom] = {}
atom_names: dict[Atom, str] = {}


def get_next_id():
    global next_id
    next_id += 1
    return next_id - 1


def update_id_from(formula: Formula):
    global next_id
    for clause in formula:
        for lit in clause:
            next_id = max(next_id, abs(lit) + 1)


def reset():
    global next_id
    global atoms
    global atom_names
    next_id = 1
    atoms = {}
    atom_names = {}


def new_atom(name: str) -> Atom:
    """Create a new atom with the given name."""
    global atoms
    global atom_names
    id = get_next_id()
    atoms[name] = id
    atom_names[id] = name
    return id


def new_aux() -> Atom:
    """Create a new auxiliary atom."""
    return get_next_id()


def neg(atom: Atom) -> Atom:
    """Negate the given atom."""
    return -atom


def or_(*args: Atom) -> Formula:
    """Create a disjunction of the given atoms."""
    return [[atom for atom in args]]


def and_(*args: Atom) -> Formula:
    """Create a conjunction of the given atoms."""
    return [[atom] for atom in args]


def andf(*args: Formula) -> Formula:
    """Create a conjunction of the given formulas."""
    result = []
    for arg in args:
        result.extend(arg)
    return result


def impl(atom: Atom, f: Formula) -> Formula:
    """Create an implication from the given atom to the given formula."""
    return [new_clause for clause in f for new_clause in or_(neg(atom), *clause)]


def impl_conj(atoms: list[Atom], f: Formula) -> Formula:
    """Create an implication from the _conjunction_ of atoms to the given formula."""
    negated = [neg(atom) for atom in atoms]
    return [new_clause for clause in f for new_clause in or_(*negated, *clause)]


def impl_disj(clause: Clause, atom: Atom) -> Formula:
    """Create an implication from the given clause to the given atom."""
    return [[neg(lit), atom] for lit in clause]


def iff(a: Atom, b: Atom) -> Formula:
    """Create an equivalence between the given atoms."""
    return [[neg(a), b], [a, neg(b)]]


def iff_disj(atoms: Clause, b: Atom) -> Formula:
    """Create an equivalence between the given clause (disjunction of atoms) and the given atom."""

    # I use here that (p | q) -> r is equivalent to (p -> r) & (q -> r)
    left_to_right = andf(*[impl(atom, [[b]]) for atom in atoms])
    right_to_left = impl(b, or_(*atoms))

    return left_to_right + right_to_left


def exactly_one(atoms: list[Atom]) -> Formula:
    """Create a formula that ensures exactly one of the given atoms is true."""
    result = CardEnc.equals(
        atoms, bound=1, top_id=next_id - 1, encoding=EncType.pairwise
    )
    result.clausify()
    clauses = result.clauses
    update_id_from(clauses)
    return clauses


def at_most_one(atoms: list[Atom]) -> Formula:
    """Create a formula that ensures at most one of the given atoms is true."""
    result = CardEnc.atmost(
        atoms, bound=1, top_id=next_id - 1, encoding=EncType.pairwise
    )
    result.clausify()
    clauses = result.clauses
    update_id_from(clauses)
    return clauses


def parse_solution(solution: list[Atom] | None) -> list[str] | None:
    if solution is None:
        return None
    result = []
    for var in solution:
        if var not in atom_names:
            continue
        if var < 0:
            id = -var
            result.append(f"~{atom_names[id]}")
        else:
            id = var
            result.append(atom_names[id])
    return result
