# Agent-DX (LLM agent users)

Design docs for how `agent-dashboard` should *feel* to an LLM agent using
it — introspection clarity, error legibility, schema guessability.

## Concerns owned by this track

- Schema clarity: are type names and field names self-explanatory to an agent
  reading them cold?
- Error legibility: if `render_screen()` is called incorrectly, does the
  error carry enough context for the agent to self-correct?
- Guessability: can an agent infer the correct call pattern from the types
  alone, without additional documentation?
- `metadata` semantics: how should agents interpret the untyped
  `DashboardActionRef.metadata` field? What conventions prevent it from
  becoming an opaque blob?

## Index

<!-- Add entries as docs land. -->

_No agent-DX docs yet._

## Out of scope

Human ergonomics belong in `../dx/`. Architectural decisions belong in
`../decisions/`. Use this folder for design *thinking* about agent-facing
clarity and introspectability.
