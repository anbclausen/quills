from pysat.card import CardEnc, EncType
import sympy
from abc import ABC, abstractmethod


next_id = 1
atoms = {}
atoms_by_id = {}


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

    inner_repr: sympy.logic.boolalg.Boolean

    @abstractmethod
    def __str__(self):
        pass

    def clausify(self) -> list[list[int]]:
        def clausify_atom(atom: sympy.Symbol | sympy.Not) -> int:
            match atom:
                case sympy.Symbol():
                    name = atom.name
                    return atoms[name].id
                case sympy.Not():
                    arg = atom.args[0]
                    if not isinstance(arg, sympy.Symbol):
                        raise ValueError(
                            f"Clausifying failed: non-symbol in inner representation of negation: {sympy.Not(arg)}"
                        )
                    name = arg.name
                    return -atoms[name].id

        cnf = sympy.to_cnf(self.inner_repr)
        clauses = cnf.args
        result = []
        for clause in clauses:
            match clause:
                case sympy.Or():
                    args = [arg for arg in clause.args]

                    clausified_args = [
                        clausify_atom(arg)
                        for arg in args
                        if isinstance(arg, sympy.Symbol) or isinstance(arg, sympy.Not)
                    ]

                    result.append(clausified_args)

                case _:
                    is_symbol = isinstance(clause, sympy.Symbol)
                    is_negated_symbol = isinstance(clause, sympy.Not)
                    if is_symbol or is_negated_symbol:
                        clausified_atom = clausify_atom(clause)
                        result.append([clausified_atom])
                    else:
                        raise ValueError(
                            f"Clausifying failed: non-disjunction in inner representation: {clause}"
                        )
        return result

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
        name_contains_comma = "," in name
        name_contains_space = " " in name
        if name_contains_comma or name_contains_space:
            raise ValueError(
                f"Atom name must not contain a comma or a space. Found '{name}'."
            )
        self.name = name
        self.id = get_next_id()
        atoms[self.name] = self
        atoms_by_id[self.id] = self

        self.inner_repr = sympy.symbols(name)

    def __str__(self):
        return self.name


class Or(Formula):
    def __init__(self, *args: Formula):
        self.args = args

        sympy_args = [arg.inner_repr for arg in self.args]
        self.inner_repr = sympy.Or(*sympy_args)

    def __str__(self):
        return f"({' | '.join([str(arg) for arg in self.args])})"


class And(Formula):
    def __init__(self, *args: Formula):
        self.args = args

        sympy_args = [arg.inner_repr for arg in self.args]
        self.inner_repr = sympy.And(*sympy_args)

    def __str__(self):
        return f"({' & '.join([str(arg) for arg in self.args])})"


class Iff(Formula):
    def __init__(self, a: Formula, b: Formula):
        self.a = a
        self.b = b

        self.inner_repr = sympy.And(
            sympy.Implies(a.inner_repr, b.inner_repr),
            sympy.Implies(b.inner_repr, a.inner_repr),
        )

    def __str__(self):
        return f"({self.a} <=> {self.b})"


class Implies(Formula):
    def __init__(self, a: Formula, b: Formula):
        self.a = a
        self.b = b

        self.inner_repr = sympy.Implies(a.inner_repr, b.inner_repr)

    def __str__(self):
        return f"({self.a} => {self.b})"


class Neg(Formula):
    def __init__(self, a: Formula):
        self.a = a

        self.inner_repr = ~a.inner_repr

    def __str__(self):
        return f"~{self.a}"


def exactly_one(atoms: list[Atom]) -> list[list[int]]:
    global next_id
    lits = [atom.id for atom in atoms]
    result = CardEnc.equals(lits, bound=1, encoding=EncType.pairwise)
    result.clausify()
    clauses = result.clauses
    update_id_from(clauses)
    return clauses


def at_most_one(atoms: list[Atom]) -> list[list[int]]:
    global next_id
    lits = [atom.id for atom in atoms]
    result = CardEnc.atmost(lits, bound=1, encoding=EncType.pairwise)
    result.clausify()
    clauses = result.clauses
    update_id_from(clauses)
    return clauses


def parse_solution(solution: list[int] | None) -> list[Atom | Neg] | None:
    if solution is None:
        return None
    result = []
    for var in solution:
        if var < 0:
            id = -var
            result.append(Neg(atoms_by_id[id]))
        else:
            id = var
            result.append(atoms_by_id[id])
    return result
