from typing import Callable, Type, ParamSpec, Generic


class PDDLType:
    def __init__(self, name: str):
        self.name = name
        self.type_name = self.__class__.__name__

    def __str__(self) -> str:
        return self.name


class object_(PDDLType):
    def type_str(self) -> str:
        return "object"


class PDDLPredicateInstance:
    def __init__(self, name: str, args: list[str]):
        self.name = name
        self.args = args

    def __str__(self) -> str:
        return f"({self.name} {' '.join(self.args)})"


P = ParamSpec("P")


class _PDDLPredicate(Generic[P]):
    def __init__(self, function: Callable[P, None], name: str | None):
        self.function = function
        self.predicate_name = function.__name__ if name is None else name
        self.args = {
            name: class_.__name__ for name, class_ in function.__annotations__.items()
        }

    def __call__(self, *args: P.args, **kwargs: P.kwargs) -> PDDLPredicateInstance:
        argstrs = [str(arg) for arg in args]
        return PDDLPredicateInstance(self.predicate_name, argstrs)

    def __str__(self) -> str:
        args_grouped_by_type: dict[str, list[str]] = {}
        for arg, type_ in self.args.items():
            if type_ not in args_grouped_by_type:
                args_grouped_by_type[type_] = []
            args_grouped_by_type[type_].append(f"?{arg}")

        arg_strings = [
            " ".join(args) + " - " + type_
            for type_, args in args_grouped_by_type.items()
        ]

        return f"({self.predicate_name} {" ".join(arg_strings)})"


def PDDLPredicate(
    name: str | None = None,
):
    def decorator(function: Callable[P, None]):
        return _PDDLPredicate(function, name)

    return decorator


@PDDLPredicate(name="not")
def not_(predicate: PDDLPredicateInstance):
    pass


class _PDDLAction:
    def __init__(
        self,
        function: Callable[
            ..., tuple[list[PDDLPredicateInstance], list[PDDLPredicateInstance]]
        ],
        name: str | None,
    ):
        self.function = function
        self.name = function.__name__ if name is None else name
        self.args = {
            name: class_.__name__ for name, class_ in function.__annotations__.items()
        }
        args = self.function.__annotations__

        self.preconditions, self.effects = self.function(
            *[type_(f"?{arg}") for arg, type_ in args.items()]
        )

    def __call__(self, *args):
        return self.function(*args)

    def __str__(self) -> str:
        parameters_grouped_by_type: dict[str, list[str]] = {}
        for arg, type_ in self.args.items():
            if type_ not in parameters_grouped_by_type:
                parameters_grouped_by_type[type_] = []
            parameters_grouped_by_type[type_].append(f"?{arg}")

        parameter_strings = [
            " ".join(parameters) + " - " + type_
            for type_, parameters in parameters_grouped_by_type.items()
        ]

        return f"""
    (:action {self.name}
        :parameters ({' '.join(parameter_strings)})
        :precondition (and {" ".join(map(str, self.preconditions))})
        :effect (and {" ".join(map(str, self.effects))})
    )"""


def PDDLAction(
    name: str | None = None,
):
    def decorator(
        function: Callable[
            ..., tuple[list[PDDLPredicateInstance], list[PDDLPredicateInstance]]
        ]
    ):
        return _PDDLAction(function, name)

    return decorator


class PDDLInstance:
    def __init__(
        self,
        objects: list[PDDLType] = [],
        types: list[Type[PDDLType]] = [],
        constants: list[PDDLType] = [],
        predicates: list[_PDDLPredicate] = [],
        initial_state: list[PDDLPredicateInstance] = [],
        goal_state: list[PDDLPredicateInstance] = [],
        actions: list[_PDDLAction] = [],
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
        object_grouped_by_type: dict[str, list[PDDLType]] = {}
        for obj in self.objects:
            if obj.type_name not in object_grouped_by_type:
                object_grouped_by_type[obj.type_name] = []
            object_grouped_by_type[obj.type_name].append(obj)

        object_strings = [
            " ".join(map(lambda o: o.name, objects)) + " - " + type_
            for type_, objects in object_grouped_by_type.items()
        ]

        init_strings = [
            str(predicate_instance) for predicate_instance in self.initial_state
        ]

        goal_strings = [
            str(predicate_instance) for predicate_instance in self.goal_state
        ]

        problem = f"""
(define (problem {self.problem})
    (:domain {self.domain})
    (:objects
        {"\n        ".join(object_strings)}
    )
    (:init
        {"\n        ".join(init_strings)}
    )
    (:goal
        (and
            {"\n            ".join(goal_strings)}
        )
    )
)
"""
        types_grouped_by_super_type: dict[str, list[Type[PDDLType]]] = {}
        for type_ in self.types:
            super_class = (
                type_.__base__.__name__
                if type_.__base__.__name__ != "object_"
                else "object"
            )
            if super_class not in types_grouped_by_super_type:
                types_grouped_by_super_type[super_class] = []
            types_grouped_by_super_type[super_class].append(type_)

        type_strings = [
            " ".join(map(lambda t: t.__name__, types)) + " - " + super_type
            for super_type, types in types_grouped_by_super_type.items()
        ]

        constants_grouped_by_type: dict[str, list[PDDLType]] = {}
        for constant in self.constants:
            if constant.type_name not in constants_grouped_by_type:
                constants_grouped_by_type[constant.type_name] = []
            constants_grouped_by_type[constant.type_name].append(constant)

        constant_strings = [
            " ".join(map(lambda c: c.name, constants)) + " - " + type_
            for type_, constants in constants_grouped_by_type.items()
        ]

        domain = f"""
(define (domain {self.domain})
    (:requirements :strips :typing :strips :negative-preconditions)
    (:types
        {"\n        ".join(type_strings)}
    )
    (:constants
        {"\n        ".join(constant_strings)}
    )
    (:predicates
        {"\n        ".join(map(str, self.predicates))}
    )
    {"\n    ".join(map(str, self.actions))}
)
"""
        return domain, problem
