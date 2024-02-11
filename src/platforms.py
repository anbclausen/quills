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


TOY = Platform("toy", 4, {(0, 1), (1, 2), (2, 3), (3, 0)})
