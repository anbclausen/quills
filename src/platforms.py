class Platform:
    def __init__(
        self, name: str, qubits: int, connectivity_graph: set[tuple[int, int]]
    ):
        self.name = name
        self.qubits = qubits

        # Connectivity graph is an undirected graph.
        self.connectivity_graph = connectivity_graph.union(
            {(j, i) for i, j in connectivity_graph}
        )


TOY = Platform("toy", 4, {(0, 1), (1, 2), (1, 3)})
TENERIFE = Platform("tenerife", 5, {(1, 0), (2, 0), (2, 1), (3, 2), (3, 4), (4, 2)})
