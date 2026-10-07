from qiskit import QuantumCircuit


def prepare_qubit(bit, basis):
    """
    Prepare one BB84 qubit.

    bit  : 0 or 1
    basis: '+' or '×'
    """

    qc = QuantumCircuit(1, 1)

    # Rectilinear basis (+)
    if basis == '+':
        if bit == 1:
            qc.x(0)

    # Diagonal basis (×)
    elif basis == 'x':
        if bit == 0:
            qc.h(0)
        else:
            qc.x(0)
            qc.h(0)

    return qc


def prepare_qubits(bits, bases):
    """
    Prepare a list of BB84 qubits.
    """

    qubits = []

    for bit, basis in zip(bits, bases):
        qubit = prepare_qubit(bit, basis)
        qubits.append(qubit)

    return qubits