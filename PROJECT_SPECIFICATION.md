# ALMS: Autonomous Learning Memory System
## Project Specification: The Recursive Intelligence Engine (v2)

### 1. Vision & Core Philosophy

ALMS is a self-correcting intelligence engine based on the principles of **Parsimony** and **Self-Consistency**. It replaces overreliance on stochastic machine learning with a live symbolic memory framework for reasoning, retrieval, and compression.

* **Intelligence as Compression**: The system learns by minimizing its coding rate—reducing complex experience clusters into simple, verified Axioms.
* **Zero Hallucination**: Every logical claim must be traced back to an instructor-verified Axiom.
* **Contracting Map**: The engine functions as a contracting map that ignores incompressible noise and converges on the low-dimensional manifold of truth.
* **Live Memory Reasoning**: The system reasons in real time by searching, comparing, and composing stored memory rather than relying primarily on external retraining.

---

### 2. The Axiom Genome (Memory Architecture)

Memory is structured into layers of increasing compression and stability:

* **Layer 0: Raw Experience**: Individual notes, traces, and research findings.
* **Layer 1: Hypotheses (`HYP-xxxx`)**: Student proposals synthesized from clusters of Layer 0 data, awaiting Instructor review.
* **Layer 2: Axioms (`AXIOM-xxxx`)**: Stabilized, instructor-verified first principles. These are fixed neurons that do not decay.
* **Layer 3: The Genome**: The collection of all Layer 2 Axioms that define the system's belief system.
* **Layer 4: Live Reasoning Network**: The active retrieval and composition layer that searches memory at runtime to answer new problems.

---

### 3. Core Components

#### A. The Heartbeat (`engine/pulse.py`)

A background daemon providing liveness.

- **Vault Watcher**: Monitors the Obsidian Vault for new data.
- **Hebbian Drift**: Strengthens co-firing synapses and prunes weak noise.
- **Instructor Scan**: Periodically checks for `[[APPROVE]]` or `[[CORRECT]]` cues in the manifold.

#### B. The Instructor Manifold (`logic/instructor_manifold.py`)

The bridge between human expertise and system logic.

- **Genome Adjustment**: When the Instructor corrects an axiom, the system re-synthesizes its DNA.
- **Deductive Realignment**: Triggers the Refactorer to maintain internal consistency.

#### C. The Empirical Crystallizer (`logic/crystallizer.py`)

The operator of structural compression.

- **Cluster Detection**: Identifies high-density manifolds in the synaptic field.
- **AutoResearch Integration**: Mandates empirical experimentation for every new axiom hypothesis.
- **Self-Consistency Audit**: Performs reconstruction tests (Theory → Evidence).

#### D. The Recursive Refactorer (`engine/refactorer.py`)

The engine of logical consistency.

- **Dependency Mapping**: Tracks which `TRACE-xxxx` nodes rely on which `AXIOM-xxxx`.
- **Refactoring**: When an Axiom changes, it rethinks all dependent reasoning paths to ensure the entire manifold realigns.

#### E. The Memory Search Layer (`logic/memory_search.py`)

The runtime retrieval engine for live symbolic reasoning.

- **Query Routing**: Maps incoming tasks to the most relevant memory regions.
- **Symbolic Retrieval**: Fetches axioms, traces, hypotheses, and failure patterns.
- **Memory Composition**: Combines retrieved memory into a reasoning scaffold.
- **Confidence Gating**: Prefers high-confidence memory and marks uncertain outputs.

---

### 4. Operational Pipeline (The Reasoning Pass)

1. **S0: Governance**: Load Persona and Instructor Policies.
2. **S1: Axiomatic Search**: Extract seeds from the prompt, prioritized by the Axiom Genome.
3. **S2-S5: Synthesis**: Identify clusters, retrieve notes, and analyze knowledge gaps.
4. **S6: AutoResearch**: Run concurrent experiments to fill gaps empirically.
5. **S7: Axiomatic Deduction**: Assemble a reasoning scaffold where every claim must cite a verified Axiom.
6. **S8: Live Memory Reasoning**: Retrieve and compose symbolic memory in real time to answer the current task.
7. **S9: Persistence**: Generate the response and write a `TRACE-xxxx` to the vault.

---

### 5. Instructor Commands (The Control Manifold)

The Instructor guides the system using explicit Markdown cues:

- **`[[APPROVE]]`**: Stabilize a hypothesis into a permanent Axiom.
- **`[[CORRECT]]`**: Provide a logical correction to trigger Genome Mutation.
- **`[[REJECT]]`**: Prune a logical path from the genome.
- **`[[REFRESH]]`**: Force a refactoring of all reasoning traces.

---

### 6. The Goal: Compounding Network Growth

As the ALMS accumulates more verified Axioms, its coding rate decreases while its reasoning depth increases. The result is a **Compounding Intelligence** that becomes faster, more accurate, and more parsimonious over time, with live memory reasoning replacing overuse of heavyweight retraining wherever possible.
