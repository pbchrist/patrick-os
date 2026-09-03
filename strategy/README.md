# strategy/

Rules about **what is worth pursuing**, as distinct from `voice/`, which is rules
about **how an output must read**.

They are separated because they are revised on different evidence. A voice rule
changes when Patrick edits a draft. A strategy rule changes when a *result*
comes back — money, a reply, silence, a refusal. Filing them together would put
"stop pursuing businesses with no identifiable buyer" next to a rule about
em-dashes, and neither would be auditable.

## Scopes

| Scope | Means |
|---|---|
| `global` | Holds across every opportunity, mechanism, and segment. |
| `mechanism:<name>` | Applies to one intervention type from `config/mechanisms.json`. |
| `segment:<name>` | Applies to one kind of buyer or market. |
| `project:<name>` | Applies to one project. |

## Evidence is mandatory

`patrick feedback strategy` refuses a lesson with no `--evidence`. A strategy
rule with no result behind it is a hunch, and an evidence-grounded system that
accumulates hunches has stopped being one.

This is stricter than `voice/`, deliberately. A wrong voice rule produces an
awkward sentence. A wrong strategy rule sends Patrick after the wrong buyers for
a quarter.

## Status

Nearly empty, and honestly so. Patrick OS has produced no commercial *results*
yet — no sends, no replies, no revenue — so there is almost nothing legitimate to
write here. The rules present come from the Site Factory teardown, which is a
result of a kind: it measured what the system was doing and found it did not
work.

Strategy rules are consumed by the mechanism-selection and qualification stages,
neither of which is built (`patrick pipeline`). This directory is currently a
destination with no reader. That is the correct order — the place lessons go
must exist before the lessons do, or they get written into voice/ where they do
not belong.
