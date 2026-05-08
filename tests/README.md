# Cognitive Council Runtime Test Suite Concept

These fixtures define a small, no-network regression suite for a future Cognitive Council Runtime.

The suite focuses on decision safety rather than model quality:

- **Council routing**: whether a request can execute, should draft, should ask a clarification, should plan, or must refuse/hold.
- **Risk flags**: ambiguity, external-send sensitivity, adversarial urgency, missing recipient, loop/regression pressure, and tradeoff planning.
- **Expected behavior contracts**: each fixture declares expected `decision`, `requires_confirmation`, and required flags.

The accompanying pytest file includes a deliberately simple mock runtime. It is not the production runtime; it is an executable contract showing what the real runtime should satisfy once implemented.
