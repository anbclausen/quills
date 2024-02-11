from typing import Type, TypeVar, Generic


class PDDLType:
    type_name = None
    super_type = None

    def __init__(self, name: str):
        self.name = name


class PDDLObject(PDDLType):
    type_name = "object"


T = TypeVar("T")


class PDDLPredicate(Generic[T]):
    predicate_name = None

    def __init__(self, parameters: T):
        self.parameters = parameters


class PDDLAction(Generic[T]):
    action_name = None

    def __init__(
        self,
        parameters: T,
        preconditions: list[PDDLPredicate],
        effects: list[PDDLPredicate],
    ):
        self.parameters = parameters
        self.preconditions = preconditions
        self.effects = effects


class PDDLInstance:
    def __init__(self):
        self.domain = "Quantum"
        self.problem = "circuit"
        self.objects = []
        self.types = []
        self.constants = []
        self.predicates = []
        self.initial_state = []
        self.goal_state = []
        self.actions = []

    def with_types(self, types: list[Type[PDDLType]]):
        self.types = types
        return self

    def with_objects(self, objects: list[PDDLType]):
        self.objects = objects
        return self

    def with_constants(self, constants: list[PDDLType]):
        self.constants = constants
        return self

    def with_predicates(self, predicates: list[Type[PDDLPredicate]]):
        self.predicates = predicates
        return self

    def with_initial_state(self, initial_state: list[PDDLPredicate]):
        self.initial_state = initial_state
        return self

    def with_goal_state(self, goal_state: list[PDDLPredicate]):
        self.goal_state = goal_state
        return self

    def with_actions(self, actions: list[PDDLAction]):
        self.actions = actions
        return self

    def compile(self) -> tuple[str, str]:
        # FIXME: Return the domain and problem as strings.
        return "", ""
