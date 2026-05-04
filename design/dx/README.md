# Developer Experience (human users)

Design docs for how `agent-dashboard` should *feel* to a human user — the
person reading the source, writing their first builder, debugging a truncated
render.

## Concerns owned by this track

- API ergonomics: dataclass field naming, argument shape, defaults.
- Error legibility: does `render_screen()` say something useful when it
  truncates, or is it silent?
- Strictness vs. flexibility: when the library constrains something (e.g.
  `view_state` Literal), is the error message helpful?
- Documentation surface: what belongs in the README, in docstrings, in
  long-form guides, in examples.
- IDE / type-checker experience: does autocomplete reveal the right surface?
  Does mypy point at the right line?
- Discoverability: how does a new consumer find the builder pattern without
  reading femtobot source?

## Index

<!-- Add entries as docs land. -->

_No DX docs yet._

## Out of scope

Anything that primarily affects LLM agents as users belongs in
`../agent-dx/`. Anything that's a pure architectural decision belongs in
`../decisions/`. Use this folder for design *thinking* about
human-facing ergonomics.
