from qiskit.primitives import StatevectorSampler


def measure_qubits(qubits, bob_bases):

    sampler = StatevectorSampler()

    measured_bits = []

    for circuit, basis in zip(qubits, bob_bases):

        # Make a copy of the received qubit
        working_circuit = circuit.copy()

        # Bob uses the diagonal measurement basis
        if basis == 'x':
            working_circuit.h(0)

        # Measure
        working_circuit.measure(0, 0)

        # Run measurement
        job = sampler.run([working_circuit], shots=1)
        result = job.result()

        # Get measurement result
        counts = result[0].data.c.get_counts()

        bit = int(list(counts.keys())[0])

        measured_bits.append(bit)

    return measured_bits