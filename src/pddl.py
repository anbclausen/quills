from typing import TypeVar, Generic, Callable, Any, Type


class PDDLType:
    def __init__(self, name: str):
        self.name = name


class object_(PDDLType):
    pass


T = TypeVar("T")


class PDDLPredicate(Generic[T]):
    def __init__(self, parameters: T):
        self.parameters = parameters


not_ = PDDLPredicate[PDDLPredicate]


class PDDLAction:
    def __init__(
        self, function: Callable[..., tuple[list[PDDLPredicate], list[PDDLPredicate]]]
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
        predicates: list[Type[PDDLPredicate]] = [],
        initial_state: list[PDDLPredicate] = [],
        goal_state: list[PDDLPredicate] = [],
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
        # FIXME: Return the domain and problem as strings.
        return "", ""
