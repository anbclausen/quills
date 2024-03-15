class Platform:
    def __init__(
        self,
        name: str,
        qubits: int,
        connectivity_graph: set[tuple[int, int]],
        description: str = "No description.",
        connectivity_graph_drawing: str | None = None,
    ):
        self.name = name
        self.qubits = qubits
        self.description = description
        self.connectivity_graph_drawing = connectivity_graph_drawing

        # Connectivity graph is an undirected graph.
        self.connectivity_graph = connectivity_graph.union(
            {(j, i) for i, j in connectivity_graph}
        )


TOY = Platform(
    "toy",
    4,
    {(0, 1), (1, 2), (1, 3)},
    description="A simple proprietary platform designed to require one swap for 'benchmarks/toy_example.qasm'.",
    connectivity_graph_drawing="""
0 - 1 - 3
    |
    2""",
)
TOY2 = Platform(
    "toy",
    4,
    {(0, 1), (1, 2), (2, 3), (3, 0)},
    description="A simple platform designed to require no swaps for 'benchmarks/toy_example.qasm'.",
)
TENERIFE = Platform(
    "tenerife",
    5,
    {(1, 0), (2, 0), (2, 1), (3, 2), (3, 4), (4, 2)},
    description="IBM Q Tenerife.",
    connectivity_graph_drawing="""
4       0
| \\   / |
|   2   |
| /   \\ |
3       1""",
)

MELBOURNE = Platform(
    "melbourne",
    14,
    {
        (1, 0),
        (1, 2),
        (2, 3),
        (4, 3),
        (4, 10),
        (5, 4),
        (5, 6),
        (5, 9),
        (6, 8),
        (7, 8),
        (9, 8),
        (9, 10),
        (11, 3),
        (11, 10),
        (11, 12),
        (12, 2),
        (13, 1),
        (13, 12),
    },
    description="IBM Q Melbourne.",
    connectivity_graph_drawing="""
0 - 1 - 2 - 3 - 4 - 5 - 6
    |   |   |   |   |   |
    13- 12- 11- 10- 9 - 8
                        |
                        7""",
)

SYCAMORE = Platform(
    "sycamore",
    54,
    {
        (0, 6),
        (1, 6),
        (1, 7),
        (2, 7),
        (2, 8),
        (3, 8),
        (3, 9),
        (4, 9),
        (4, 10),
        (5, 10),
        (5, 11),
        (6, 12),
        (6, 13),
        (7, 13),
        (7, 14),
        (8, 14),
        (8, 15),
        (9, 15),
        (9, 16),
        (10, 16),
        (10, 17),
        (11, 17),
        (12, 18),
        (13, 18),
        (13, 19),
        (14, 19),
        (14, 20),
        (15, 20),
        (15, 21),
        (16, 21),
        (16, 22),
        (17, 22),
        (17, 23),
        (18, 24),
        (18, 25),
        (19, 25),
        (19, 26),
        (20, 26),
        (20, 27),
        (21, 27),
        (21, 28),
        (22, 28),
        (22, 29),
        (23, 29),
        (24, 30),
        (25, 30),
        (25, 31),
        (26, 31),
        (26, 32),
        (27, 32),
        (27, 33),
        (28, 33),
        (28, 34),
        (29, 34),
        (29, 35),
        (30, 36),
        (30, 37),
        (31, 37),
        (31, 38),
        (32, 38),
        (32, 39),
        (33, 39),
        (33, 40),
        (34, 40),
        (34, 41),
        (35, 41),
        (36, 42),
        (37, 42),
        (37, 43),
        (38, 43),
        (38, 44),
        (39, 44),
        (39, 45),
        (40, 45),
        (40, 46),
        (41, 46),
        (41, 47),
        (42, 48),
        (42, 49),
        (43, 49),
        (43, 50),
        (44, 50),
        (44, 51),
        (45, 51),
        (45, 52),
        (46, 52),
        (46, 53),
        (47, 53),
    },
    description="Google Sycamore",
    connectivity_graph_drawing="""
0   1   2   3   4   5
 \\ / \\ / \\ / \\ / \\ / \\
  6   7   8   9   10  11
 / \\ / \\ / \\ / \\ / \\ /
12  13  14  15  16  17
 \\ / \\ / \\ / \\ / \\ / \\
  18  19  20  21  22  23
 / \\ / \\ / \\ / \\ / \\ /
24  25  26  27  28  29
 \\ / \\ / \\ / \\ / \\ / \\
  30  31  32  33  34  35
 / \\ / \\ / \\ / \\ / \\ /
36  37  38  39  40  41
 \\ / \\ / \\ / \\ / \\ / \\
  42  43  44  45  46  47
 / \\ / \\ / \\ / \\ / \\ /
48  49  50  51  52  53"""
)
