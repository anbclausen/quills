from pysat.card import CardEnc
import pysat.formula
from abc import ABC, abstractmethod


next_id = 1
atoms = {}


def get_next_id():
    global next_id
    next_id += 1
    return next_id - 1


def update_id_from(formula: list[list[int]]):
    global next_id
    for clause in formula:
        for lit in clause:
            next_id = max(next_id, abs(lit) + 1)


class Formula(ABC):
    """
    A boolean formula.

    Infix operators:
    - `f | f'` for disjunction
    - `f & f'` for conjunction
    - `~f` for negation
    - `f >> f'` for implication
    - `f @ f'` for biimplication
    """

    @abstractmethod
    def clausify(self) -> list[list[int]]:
        pass

    @abstractmethod
    def inner(self):
        pass

    @abstractmethod
    def __str__(self):
        pass

    def __or__(self, other):
        return Or(self, other)

    def __and__(self, other):
        return And(self, other)

    def __invert__(self):
        return Neg(self)

    def __rshift__(self, other):
        return Implies(self, other)

    def __matmul__(self, other):
        return Iff(self, other)


class Atom(Formula):
    def __init__(self, name: str):
        self.name = name
        self.id = get_next_id()
        atoms[self.id] = self
        self.inner_repr = pysat.formula.Atom(self.id)

    def clausify(self) -> list[list[int]]:
        return [[self.id]]

    def inner(self):
        return self.inner_repr

    def __str__(self):
        return self.name


class Or(Formula):
    def __init__(self, *args: Formula):
        self.args = args

        pysat_args = [arg.inner() for arg in self.args]
        self.inner_repr = pysat.formula.Or(*pysat_args)
        self.inner_repr.clausify()
        self.clauses = self.inner_repr.clauses
        update_id_from(self.clauses)

    def clausify(self) -> list[list[int]]:
        return self.clauses

    def inner(self):
        return self.inner_repr

    def __str__(self):
        return f"({' | '.join([str(arg) for arg in self.args])})"


class And(Formula):
    def __init__(self, *args: Formula):
        self.args = args

        pysat_args = [arg.inner() for arg in self.args]
        self.inner_repr = pysat.formula.And(*pysat_args)
        self.inner_repr.clausify()
        self.clauses = self.inner_repr.clauses
        update_id_from(self.clauses)

    def clausify(self) -> list[list[int]]:
        return self.clauses

    def inner(self):
        return self.inner_repr

    def __str__(self):
        return f"({' & '.join([str(arg) for arg in self.args])})"


class Iff(Formula):
    def __init__(self, a: Formula, b: Formula):
        self.a = a
        self.b = b
        self.inner_repr = pysat.formula.Equals(a.inner(), b.inner())
        self.inner_repr.clausify()
        self.clauses = self.inner_repr.clauses
        update_id_from(self.clauses)

    def clausify(self) -> list[list[int]]:
        return self.clauses

    def inner(self):
        return self.inner_repr

    def __str__(self):
        return f"({self.a} <=> {self.b})"


class Implies(Formula):
    def __init__(self, a: Formula, b: Formula):
        self.a = a
        self.b = b
        self.inner_repr = pysat.formula.Implies(a.inner(), b.inner())
        self.inner_repr.clausify()
        self.clauses = self.inner_repr.clauses
        update_id_from(self.clauses)

    def clausify(self) -> list[list[int]]:
        return self.clauses

    def inner(self):
        return self.inner_repr

    def __str__(self):
        return f"({self.a} => {self.b})"


class Neg(Formula):
    def __init__(self, a: Formula):
        self.a = a
        self.inner_repr = pysat.formula.Neg(a.inner())
        self.inner_repr.clausify()
        self.clauses = self.inner_repr.clauses
        update_id_from(self.clauses)

    def clausify(self) -> list[list[int]]:
        return self.clauses

    def inner(self):
        return self.inner_repr

    def __str__(self):
        return f"~{self.a}"


def exactly_one(atoms: list[Atom]):
    global next_id
    lits = [atom.id for atom in atoms]
    result = CardEnc.equals(lits, bound=1, top_id=next_id - 1)
    result.clausify()
    clauses = result.clauses
    for clause in clauses:
        biggest = max(clause)
        next_id = max(next_id, biggest + 1)
    return clauses


def at_most_one(atoms: list[Atom]):
    global next_id
    lits = [atom.id for atom in atoms]
    result = CardEnc.atmost(lits, bound=1, top_id=next_id - 1)
    result.clausify()
    clauses = result.clauses
    for clause in clauses:
        biggest = max(clause)
        next_id = max(next_id, biggest + 1)
    return clauses


def parse_solution(solution: list[int] | None) -> list[Atom] | None:
    if solution is None:
        return None
    pysat_atoms = pysat.formula.Formula.formulas(solution, atoms_only=True)
    pysat_atom_strs = [str(atom) for atom in pysat_atoms]
    result = []
    for atom_str in pysat_atom_strs:
        if atom_str.startswith("~"):
            id = int(atom_str[1:])
            result.append(Neg(atoms[id]))
        else:
            id = int(atom_str)
            result.append(atoms[id])
    return result
