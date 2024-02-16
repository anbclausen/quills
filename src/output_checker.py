from synthesizers.synthesizer import PhysicalQubit, LogicalQubit, line_gate_mapping
from platforms import Platform
from qiskit import QuantumCircuit


class OutputChecker:
    @staticmethod
    def check(
        input_circuit: QuantumCircuit,
        output_circuit: QuantumCircuit,
        initial_mapping: dict[LogicalQubit, PhysicalQubit],
        platform: Platform,
    ) -> bool:
        """
        Returns True if the output circuit represents the input circuit faithfully.
        Otherwise returns False.
        TODO: give error messages
        TODO: check connectivity
        """

        input_line_gates = line_gate_mapping(input_circuit)
        output_line_gates = line_gate_mapping(output_circuit)

        print(f"input: {input_line_gates}")
        print(f"output: {output_line_gates}")

        """
        Circuit equivalence checks:
        First splits the lists of output gates for each qubit whenever there is a 
        SWAP gate in the list. Each list starts with a SWAP gate, except for the 
        first.
        Then remakes the lists without SWAPs by taking the first list for
        each qubit as is and for each list that starts with a SWAP putting the rest
        of the list on the qubit that was swapped with. Also the rest of the lists
        for the involved qubits switch places.
        Finally compares the resulting lists to the lists for the input - they should
        be equal when looking at the correct qubits according to the initial mapping.
        """
        output_line_gates_split = {key: [] for key in output_line_gates.keys()}
        longest_list_length = 0
        # split each list of gates whenever there is a swap gate
        for line, gates in output_line_gates.items():
            size = len(gates)
            # indexes of SWAPs
            idx_list = [idx for idx, val in enumerate(gates) if val.startswith("swap")]
            # check whether there were any SWAPs
            if idx_list:
                # if there were, split the lists
                split_gates = [
                    gates[i:j]
                    for i, j in zip(
                        [0] + idx_list,
                        idx_list + ([size] if idx_list[-1] != size else []),
                    )
                ]
            else:
                # otherwise just take the given list
                split_gates = [gates]
            output_line_gates_split[line] = split_gates

            # also keep track of the longest list of lists of gates
            if len(split_gates) > longest_list_length:
                longest_list_length = len(split_gates)
        print(f"split: {output_line_gates_split}, longest: {longest_list_length}")

        # now reconstruct the lists by respecting the SWAPs
        output_line_gates_no_swaps = {key: [] for key in output_line_gates.keys()}
        for i in range(longest_list_length):
            # pull out the first list remaining for each qubit and remove from remaining
            first_lists = {
                line: gate_lists[0]
                for line, gate_lists in output_line_gates_split.items()
                if len(gate_lists) > 0
            }
            for line in first_lists.keys():
                output_line_gates_split[line] = output_line_gates_split[line][1:]

            # now add the first lists in the correct places
            for line, gate_list in first_lists.items():
                first_gate = gate_list[0]
                # check if the first gate is a SWAP
                if first_gate.startswith("swap"):
                    # if it is, find the line to swap with
                    swap_line = int(first_gate[4:])
                    # put the gates on the correct line (without the SWAP gate)
                    output_line_gates_no_swaps[swap_line].extend(gate_list[1:])

                    # switch around the remaining gates for the two lines
                    tmp = output_line_gates_split[swap_line]
                    output_line_gates_split[swap_line] = output_line_gates_split[line]
                    output_line_gates_split[line] = tmp
                else:
                    # if it is not, just put the gates on the given line
                    output_line_gates_no_swaps[line].extend(gate_list)
        print(f"swaps removed: {output_line_gates_no_swaps}")

        # now check for equivalence with the input
        for line, gates in input_line_gates.items():
            # for a qubit in the input find the corresponding qubit in
            # the reconstructed output according to the initial mapping
            mapped_line = initial_mapping[LogicalQubit(line)].id
            mapped_line_gates = output_line_gates_no_swaps[mapped_line]

            # if the number of gates does not match something is wrong
            if len(mapped_line_gates) != len(gates):
                return False

            # if the types of the gates do not match something is wrong
            for i, gate in enumerate(gates):
                if gate != mapped_line_gates[i]:
                    return False

        # TODO check connectivity

        # nothing wrong was found, so the circuits are equivalent
        return True
