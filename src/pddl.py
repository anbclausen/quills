from typing import Callable, Type


class PDDLType:
    def __init__(self, name: str):
        self.name = name
        self.type_name = self.__class__.__name__

    def __str__(self) -> str:
        return self.name

    def type_str(self) -> str:
        return self.type_name


class object_(PDDLType):
    def type_str(self) -> str:
        return "object"


class PDDLPredicateInstance:
    def __init__(self, name: str, args: list[str]):
        self.name = name
        self.args = args


class PDDLPredicate:
    def __init__(self, function: Callable[..., None]):
        self.function = function
        self.predicate_name = function.__name__
        self.args = {
            name: class_.__name__ for name, class_ in function.__annotations__.items()
        }

    def __call__(self, *args):
        argstrs = [str(arg) for arg in args]
        return PDDLPredicateInstance(self.predicate_name, argstrs)


@PDDLPredicate
def not_(predicate: PDDLPredicate):
    pass


class PDDLAction:
    def __init__(
        self,
        function: Callable[
            ..., tuple[list[PDDLPredicateInstance], list[PDDLPredicateInstance]]
        ],
    ):
        self.function = function

    def __call__(self, *args):
        return self.function(*args)


class PDDLInstance:
    def __init__(
        self,
        objects: list[PDDLType] = [],
        types: list[Type[PDDLType]] = [],
        constants: list[PDDLType] = [],
        predicates: list[PDDLPredicate] = [],
        initial_state: list[PDDLPredicateInstance] = [],
        goal_state: list[PDDLPredicateInstance] = [],
        actions: list[PDDLAction] = [],
    ):
        self.domain = "Quantum"
        self.problem = "circuit"
        self.objects = objects
        self.types = types
        self.constants = constants
        self.predicates = predicates
        self.initial_state = initial_state
        self.goal_state = goal_state
        self.actions = actions

    def compile(self) -> tuple[str, str]:
        problem = f"""
(define (problem {self.problem})
    (:domain {self.domain})
    (:objects
        {" ".join(map(str, self.objects))}
    )
    (:init
        {" ".join(map(str, self.initial_state))}
    )
    (:goal
        (and
            {" ".join(map(str, self.goal_state))}
        )
    )
)
"""

        # FIXME: Return the domain and problem as strings.
        return "", ""
