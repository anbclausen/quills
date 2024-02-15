class A:
    pass


class B(A):
    __match_args__ = ("name",)

    def __init__(self, name):
        self.name = name


class C:
    pass


a: A = B("a")

match a:
    case B(name):
        print(name)
    case C():
        print("C")
    case _:
        print("other")
