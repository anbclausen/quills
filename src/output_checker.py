from synthesizers.synthesizer import (
    PhysicalQubit,
    LogicalQubit,
    line_gate_mapping,
    remove_all_non_swap_gates,
)
from platforms import Platform
from qiskit import QuantumCircuit, QuantumRegister, ClassicalRegister
from qiskit.circuit import Qubit
import operator
from mqt.qcec import verify, EquivalenceCriterion


class OutputChecker:
    @staticmethod
    def check(
        input_circuit: QuantumCircuit,
        output_circuit: QuantumCircuit,
        initial_mapping: dict[LogicalQubit, PhysicalQubit],
        platform: Platform,
    ) -> bool:
        """
        Returns True if the output circuit represents the input circuit faithfully
        and all binary gates are executed on connected qubits.
        Otherwise returns False.

        First splits the lists of output gates for each qubit whenever there is a
        binary gate in the list. Each list starts with a binary gate, except for
        (maybe) the first. Also does connectivity checks for binary gates in this
        stage.

        Then remakes the lists without SWAPs by iteratively processing the first list
        for each qubit and ensuring that binary gates are kept in sync. Unary gates are
        simply added to the correct list. For binary gates, checks whether the gate
        number has already been seen by another line (is on the waiting list for another
        line). If this is the case, adds the current gates to the correct list for this
        and the other qubit (minus the first gate, if it is a SWAP gate). Otherwise,
        puts the gate on the waiting list with the current line's number. Repeats until
        all gates have been put on their correct list.

        Finally compares the resulting lists to the lists for the input - they should
        be equal when looking at the correct qubits according to the initial mapping.
        """

        # Get the gates for each qubit (line) in the input and output
        # For the input, throw away gate numbers, since they are unnecessary
        input_line_gates: dict[LogicalQubit, list[str]] = {
            LogicalQubit(line): list(map(operator.itemgetter(1), gates))
            for line, gates in line_gate_mapping(input_circuit).items()
        }
        output_line_gates: dict[PhysicalQubit, list[tuple[int, str]]] = {
            PhysicalQubit(line): gates
            for line, gates in line_gate_mapping(output_circuit).items()
        }

        # split each list of gates whenever there is a binary gate
        output_line_gates_split: dict[PhysicalQubit, list[list[tuple[int, str]]]] = {
            line: [] for line in output_line_gates.keys()
        }
        for line, gates in output_line_gates.items():
            # current_list keeps track of the gates seen so far that have no conflicts
            # with each other - unary gates, and possibly one binary gate at the start
            current_list = []
            for gate_num, gate_name in gates:
                if gate_name.startswith("swap") or gate_name.startswith("cx"):
                    # do connectivity check
                    other_line = int(gate_name[4:])
                    if not (line.id, other_line) in platform.connectivity_graph:
                        print(
                            f"Connectivity check failed: ({line, other_line}) not in platform"
                        )
                        return False

                    # for binary gates, flush and reset the list if necessary
                    if current_list:
                        output_line_gates_split[line].append(current_list)
                        current_list = []
                    # then start a new list with the binary gate
                    if gate_name.startswith("swap"):
                        current_list = [(gate_num, gate_name[:4])]
                    else:
                        current_list = [(gate_num, gate_name[:3])]
                else:
                    # unary gate - just append to list
                    current_list.append((gate_num, gate_name))
            # flush the last list
            if current_list:
                output_line_gates_split[line].append(current_list)

        # now reconstruct the lists by respecting the SWAPs and taking binary gates together
        output_line_gates_no_swaps: dict[PhysicalQubit, list[tuple[int, str]]] = {
            line: [] for line in output_line_gates.keys()
        }
        # get the first list of non-conflicting qubits for each qubit
        first_lists: dict[PhysicalQubit, list[tuple[int, str]]] = {
            line: gate_lists[0]
            for line, gate_lists in output_line_gates_split.items()
            if len(gate_lists) > 0
        }
        # waiting list for binary qubits
        waiting: dict[int, PhysicalQubit] = {}
        while first_lists:
            for line in first_lists.keys():
                gate_list = first_lists[line]
                if gate_list:
                    first_gate_num, first_gate_name = gate_list[0]
                    # check whether the first gate is binary
                    if first_gate_name == "swap" or first_gate_name.startswith("cx"):
                        # check whether the other side of the gate is ready
                        if first_gate_num in waiting.keys():
                            other_line = waiting[first_gate_num]
                            if other_line != line:
                                # found someone else on the waiting list - proceed
                                waiting.pop(first_gate_num)
                                other_gate_list = first_lists[other_line]

                                if first_gate_name == "swap":
                                    # switch around the remaining gates
                                    tmp = output_line_gates_split[other_line]
                                    output_line_gates_split[other_line] = (
                                        output_line_gates_split[line]
                                    )
                                    output_line_gates_split[line] = tmp

                                    # append the gates (without the SWAP) to the correct lists
                                    # the correct lists are the opposite of where they came from
                                    output_line_gates_no_swaps[other_line].extend(
                                        gate_list[1:]
                                    )
                                    output_line_gates_no_swaps[line].extend(
                                        other_gate_list[1:]
                                    )
                                else:
                                    # first gate is not SWAP, so it is CX
                                    # append the gates to the correct lists
                                    # the correct lists are the same as where they came from
                                    output_line_gates_no_swaps[line].extend(gate_list)
                                    output_line_gates_no_swaps[other_line].extend(
                                        other_gate_list
                                    )

                                # then remove the gates from remaining
                                output_line_gates_split[line] = output_line_gates_split[
                                    line
                                ][1:]
                                output_line_gates_split[other_line] = (
                                    output_line_gates_split[other_line][1:]
                                )
                                # and remove from other first_list to avoid duplication
                                first_lists[other_line] = []
                            else:
                                # found itself on the waiting list - keep waiting
                                pass
                        else:
                            # put name on waiting list and do nothing
                            waiting[first_gate_num] = line
                    else:
                        # gate is unary
                        # add gates to correct line
                        output_line_gates_no_swaps[line].extend(gate_list)
                        # then remove the list from remaining
                        output_line_gates_split[line] = output_line_gates_split[line][
                            1:
                        ]
                else:
                    # this was a binary gate that someone else was waiting for - skip it
                    pass

            # update first_lists for next round
            first_lists: dict[PhysicalQubit, list[tuple[int, str]]] = {
                line: gate_lists[0]
                for line, gate_lists in output_line_gates_split.items()
                if len(gate_lists) > 0
            }

        # now check for equivalence with the input
        for line, gates in input_line_gates.items():
            # for a qubit in the input find the corresponding qubit in
            # the reconstructed output according to the initial mapping
            mapped_line = initial_mapping[line]
            mapped_line_gates = list(
                map(operator.itemgetter(1), output_line_gates_no_swaps[mapped_line])
            )

            # if the number of gates does not match something is wrong
            if len(mapped_line_gates) != len(gates):
                print("Wrong output gate found")
                print(f"These lists of gates should be identical:")
                print(f"Input line: {line}")
                print(gates)
                print(f"Output line: {mapped_line}")
                print(mapped_line_gates)
                return False

            # if the types of the gates do not match something is wrong
            for i, gate_name in enumerate(gates):
                output_gate_name = mapped_line_gates[i]
                success = True
                if gate_name.startswith("swap") and output_gate_name != "swap":
                    success = False
                elif gate_name.startswith("cx"):
                    if gate_name[:3] != output_gate_name:
                        success = False
                elif gate_name != output_gate_name:
                    success = False
                if not success:
                    print("Wrong output gate found")
                    print(
                        f"These lists of gates should be identical (problem encountered at gate {i}):"
                    )
                    print(f"Input line: {line}")
                    print(gates)
                    print(f"Output line: {mapped_line}")
                    print(mapped_line_gates)
                    return False

        # nothing wrong was found, so the circuits are equivalent
        return True

    @staticmethod
    def check_qcec(
        input_circuit: QuantumCircuit,
        output_circuit: QuantumCircuit,
        initial_mapping: dict[LogicalQubit, PhysicalQubit],
    ) -> bool:

        output_mapping = line_gate_mapping(output_circuit)

        register = QuantumRegister(input_circuit.num_qubits, "p")
        mapped_output = QuantumCircuit(register)
        output_circuit_data = output_circuit.data

        reverse_initial = {p.id: l.id for l, p in initial_mapping.items()}

        while not all(len(output_mapping[line]) == 0 for line in output_mapping.keys()):
            for line in output_mapping.keys():
                gates = output_mapping[line]

                for gate_num, gate_name in gates:
                    if gate_name.startswith("swap") or gate_name.startswith("cx"):
                        break
                    else:
                        instr = output_circuit_data[gate_num].replace(
                            qubits=[Qubit(register, reverse_initial[line])]
                        )
                        mapped_output.append(instr)
                        output_mapping[line] = output_mapping[line][1:]

            waiting = []
            matching_binary_gates = []
            for line in output_mapping.keys():
                gates = output_mapping[line]
                if gates:
                    binary_num, _ = gates[0]
                    if binary_num in waiting:
                        waiting.remove(binary_num)
                        matching_binary_gates.append(binary_num)
                    else:
                        waiting.append(binary_num)

            for line in output_mapping.keys():
                gates = output_mapping[line]
                if gates:
                    binary_num, binary_name = gates[0]
                    if binary_num in matching_binary_gates:
                        if binary_name.startswith("cx"):
                            other_line = int(binary_name[4:])
                            is_control = int(binary_name[2]) == 0

                            if is_control:
                                instr = output_circuit_data[gate_num].replace(
                                    qubits=[
                                        Qubit(register, reverse_initial[line]),
                                        Qubit(register, reverse_initial[other_line]),
                                    ]
                                )
                            else:
                                instr = output_circuit_data[gate_num].replace(
                                    qubits=[
                                        Qubit(register, reverse_initial[other_line]),
                                        Qubit(register, reverse_initial[line]),
                                    ]
                                )
                            mapped_output.append(instr)
                            output_mapping[line] = output_mapping[line][1:]
                            output_mapping[other_line] = output_mapping[other_line][1:]
                        else:
                            # SWAP
                            other_line = int(binary_name[4:])
                            output_mapping[line] = output_mapping[line][1:]
                            output_mapping[other_line] = output_mapping[other_line][1:]
                            tmp = reverse_initial[line]
                            reverse_initial[line] = reverse_initial[other_line]
                            reverse_initial[other_line] = tmp

        mapped_output.measure_all()
        input_circuit.measure_all()

        result = verify(input_circuit, mapped_output)

        if result.equivalence == EquivalenceCriterion.equivalent:
            return True
        else:
            return False
