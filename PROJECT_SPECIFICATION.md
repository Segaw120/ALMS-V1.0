# ALMS: Autonomous Learning Memory System
## Project Specification: The Recursive Intelligence Engine (v2)

### 1. Vision & Core Philosophy
The ALMS is a self-correcting intelligence engine based on the principles of **Parsimony** (Simplicity) and **Self-Consistency**. It replaces stochastic machine learning with a deductive, compression-based reasoning framework.

*   **Intelligence as Compression**: The system learns by minimizing its "coding rate"—reducing complex experience clusters into simple, verified Axioms.
*   **Zero Hallucination**: Every logical claim must be traced back to an instructor-verified Axiom.
*   **Contracting Map**: The engine functions as a contracting map that ignores incompressible noise and converges on the "Low-Dimensional Manifold" of truth.

---

### 2. The Axiom Genome (Memory Architecture)
Memory is structured into layers of increasing compression and stability:

*   **Layer 0: Raw Experience**: Individual notes and research findings.
*   **Layer 1: Hypotheses (`HYP-xxxx`)**: Student proposals synthesized from clusters of Layer 0 data, awaiting Instructor review.
*   **Layer 2: Axioms (`AXIOM-xxxx`)**: Stabilized, instructor-verified "First Principles." These are **Fixed Neurons** that never decay.
*   **Layer 3: The Genome**: The collection of all Layer 2 Axioms that define the system's "belief system."

---

### 3. Core Components

#### A. The Heartbeat (`engine/pulse.py`)
A background daemon providing "liveness."
- **Vault Watcher**: Monitors the Obsidian Vault for new data.
- **Hebbian Drift**: Strengthens co-firing synapses and prunes weak noise.
- **Instructor Scan**: Periodically checks for `[[APPROVE]]` or `[[CORRECT]]` cues in the manifold.

#### B. The Instructor Manifold (`logic/instructor_manifold.py`)
The bridge between Human expertise and System logic.
- **Genome Adjustment**: When the Instructor corrects an axiom, the system re-synthesizes its "DNA."
- **Deductive Realignment**: Triggers the Refactorer to maintain internal consistency.

#### C. The Empirical Crystallizer (`logic/crystallizer.py`)
The operator of structural compression.
- **Cluster Detection**: Identifies high-density manifolds in the synaptic field.
- **AutoResearch Integration**: Mandates empirical experimentation for every new axiom hypothesis.
- **Self-Consistency Audit**: Performs reconstruction tests (Theory → Evidence).

#### D. The Recursive Refactorer (`engine/refactorer.py`)
The engine of logical consistency.
- **Dependency Mapping**: Tracks which `TRACE-xxxx` nodes rely on which `AXIOM-xxxx`.
- **Refactoring**: When an Axiom changes, it "re-thinks" all dependent reasoning paths to ensure the entire manifold realigns.

---

### 4. Operational Pipeline (The Reasoning Pass)

1.  **S0: Governance**: Load Persona and Instructor Policies.
2.  **S1: Axiomatic Search**: Extract seeds from the prompt, prioritized by the Axiom Genome.
3.  **S2-S5: Synthesis**: Identify clusters, retrieve notes, and analyze knowledge gaps.
4.  **S6: AutoResearch**: Run concurrent experiments to fill gaps empirically.
5.  **S7: Axiomatic Deduction**: Assemble a reasoning scaffold where every claim must cite a verified Axiom.
6.  **S8-S9: Persistence**: Generate the response and write a `TRACE-xxxx` (Iteration 1) to the vault.

---

### 5. Instructor Commands (The Control Manifold)
The Instructor guides the system using explicit Markdown cues:
- **`[[APPROVE]]`**: Stabilize a hypothesis into a permanent Axiom.
- **`[[CORRECT]]`**: Provide a logical correction to trigger Genome Mutation.
- **`[[REJECT]]`**: Prune a logical path from the genome.
- **`[[REFRESH]]`**: Force a refactoring of all reasoning traces.

---

### 6. The Goal: Compounding Network Growth
As the ALMS accumulates more verified Axioms, its coding rate decreases while its reasoning depth increases. The result is a **Compounding Intelligence** that becomes faster, more accurate, and more parsimonious over time, eventually replacing the need for traditional ML training with a living, deductible proof of its own knowledge.
