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
