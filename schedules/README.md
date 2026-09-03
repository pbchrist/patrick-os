# schedules/

Definitions for recurring and condition-based work. A schedule names a skill, its
inputs, and when it should run. **A schedule contains no logic.** If a schedule
needs a rule, the rule belongs in the skill.

Schedules are declarative on purpose: nothing here executes them yet. They are
read by whatever runner Patrick points at them — `hermes cron`, `launchd`, a
Claude Code `/loop`, cron itself. Patrick OS states the intent; the host schedules
it. That is the same boundary the router draws around providers.

Every schedule runs its skill in dry-run mode unless `execute` is explicitly
true, and no schedule in this repository sets it.

## Fields

- `skill` — the slug to invoke. Must exist in `skills/`.
- `when` — `cron` expression, or `on:<condition>` for condition-based work.
- `inputs` — bound at invocation, validated against the skill's declared inputs.
- `execute` — false everywhere in v1.
- `output_to` — where the artifact lands for a human to read.
- `escalate_if` — the condition that makes this a person's problem instead.
