from pydantic import BaseModel


class Platform:
    def __init__(self, data):
        class PlatformData(BaseModel):
            name: str
            number_of_qubits: int
            connectivity_graph: set[tuple[int, int]]

        platform_data = PlatformData(**data)  # type: ignore

        self.name = platform_data.name
        self.number_of_qubits = platform_data.number_of_qubits

        # Connectivity graph is undirected.
        self.connectivity_graph = platform_data.connectivity_graph.union(
            {(j, i) for i, j in platform_data.connectivity_graph}
        )
