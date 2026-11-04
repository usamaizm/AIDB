# AIDB Compatibility and Forks

AIDB is intentionally in flux.

The project should evolve quickly without requiring every implementation, fork, or agent to move in lockstep. The durable center is the contract: shared data semantics, identity, provenance, history, portability, and interoperability rules.

## Forks are first-class

An independent implementation may change the storage engine, language, runtime model, transport, schema extensions, or internal architecture.

A fork does not need to remain source-compatible with the AIDB reference implementation to participate in the ecosystem.

For example, an implementation such as **AIDBFlux** may experiment with a more flexible architecture while still identifying the AIDB contract and advertising its own capabilities.

The network should care about:
- which contract/version an implementation supports
- what capabilities it provides
- which extensions it adds
- what representations and transports it accepts
- what interoperability guarantees it makes

It should not require one canonical codebase.

## Three identities

A compatible node should distinguish:
1. **Node identity** — the durable identity of a particular running/home instance.
2. **Implementation identity** — the software implementation and version operating that node.
3. **Protocol/contract identity** — the interoperable semantics the node claims to implement.

This prevents a fork from being mistaken for the original implementation while still allowing it to participate as an AIDB node.

## Extensions

Extensions are expected. An implementation may publish namespaced capabilities or resource types without waiting for the reference implementation to adopt them. Extensions should be explicitly named, versioned where behavior can change, discoverable through the node specification, ignorable when not required, and marked required only when compatibility genuinely depends on them.

An extension must not silently redefine a canonical AIDB semantic.

## Compatibility negotiation

A consumer should discover a node, inspect its protocol/contract versions and implementation identity, then determine the intersection of required capabilities.

Conceptually: `compatible = shared_contract && required_capabilities ⊆ advertised_capabilities`

Compatibility is a property of a particular interaction, not a permanent label attached to a repository.

## Portability across implementations

Portable export/import is a critical anti-fragmentation mechanism.

A knowledge record created by one implementation should remain useful when moved to another implementation, subject to declared contract/version and extension requirements. Provenance must survive the move rather than being rewritten as if the receiving implementation created the original knowledge.

When an extension cannot be represented natively, the receiving implementation should preserve the original data or declare the loss explicitly rather than silently discarding meaning.

## Evolving without freezing

AIDB should prefer additive evolution where possible:
- add capabilities before requiring them
- version incompatible contract changes
- preserve old specifications as history
- keep unknown optional fields/extensions ignorable
- document experimental behavior
- let forks prove alternatives in practice
- promote successful experiments into shared semantics only after evidence

The objective is not one perfect architecture. The objective is a living interoperability substrate that can survive architectural change.

## Fork rule

> Fork freely. Experiment aggressively. Preserve the contract where interoperability matters. Publish what changed.

AIDBFlux, future forks, and independent implementations should be able to become peers in the network rather than permanent fragments of it.
