import matplotlib.pyplot as plt
from qiskit import QuantumCircuit


def create_alice_circuit(bit, basis):

    qc = QuantumCircuit(1)

    # =====================================
    # Alice's BB84 STATE PREPARATION
    # =====================================

    if basis == "+":

        # Computational basis
        #
        # bit = 0 → |0>
        # bit = 1 → |1>

        if bit == 1:
            qc.x(0)

    elif basis == "x":

        # Diagonal basis
        #
        # bit = 0 → |+>
        # bit = 1 → |->

        if bit == 0:
            qc.h(0)

        else:
            qc.x(0)
            qc.h(0)

    return qc


def visualize_qubit(bit, basis, qubit_number):

    qc = create_alice_circuit(bit, basis)

    print()
    print("=" * 50)
    print(f"QUBIT {qubit_number}")
    print("=" * 50)

    print("Alice Bit   :", bit)
    print("Alice Basis :", basis)

    # State description
    if basis == "+" and bit == 0:
        state = "|0>"

    elif basis == "+" and bit == 1:
        state = "|1>"

    elif basis == "x" and bit == 0:
        state = "|+>"

    else:
        state = "|->"

    print("Quantum State:", state)

    print()
    print("Circuit:")
    circuit_text = str(qc.draw())
    print(circuit_text.encode("ascii", errors="replace").decode("ascii"))

    # =====================================
    # GRAPHICAL CIRCUIT
    # =====================================

    fig = qc.draw(output="mpl")

    fig.suptitle(
        f"Alice - Qubit {qubit_number}\n"
        f"Bit = {bit}, Basis = {basis}, State = {state}"
    )

    plt.show(block=True)