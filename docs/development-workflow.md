# RouteLens AI — Development Workflow

## 1. Purpose

This document defines **how RouteLens AI should be developed**.

It does not define:

- what the product is;
- how the system is architected;
- or the order of implementation phases.

Those responsibilities belong to:

```text
docs/prd.md
docs/technical-design.md
docs/implementation-plan.md
```

This document instead defines:

- the role of the planning agent;
- the role of Codex CLI;
- the role of the human developer;
- how implementation phases are prepared;
- how Codex should operate;
- how testing and verification should be performed;
- when Codex should stop and escalate;
- how discoveries should be routed back into project documentation;
- how a phase progresses from planning to human-controlled Git commit.

RouteLens uses a **lightweight spec-driven development workflow** designed for rapid iteration without sacrificing architectural control or behavioral verification.

---

# 2. Development Model

RouteLens uses three layers of project artifacts.

## 2.1 Planning Layer

Located primarily in:

```text
docs/
├── prd.md
├── technical-design.md
├── implementation-plan.md
└── development-workflow.md
```

These files contain durable project knowledge.

They are primarily used by:

- the human developer;
- the planning agent;
- and Codex when broader context is specifically required.

---

## 2.2 Codex SDD Harness

Located at the project root:

```text
AGENTS.md
APP_SPEC.md
BUILD_PLAN.md
PROJECT_STATE.md
```

These files provide Codex with concise operational context.

They should be derived from the planning-layer documents rather than replacing them.

---

## 2.3 Phase Prompt

Before each implementation phase, the planning agent produces a **bounded Codex prompt**.

The phase prompt provides only the context required for the current task.

Conceptually:

```text
durable planning docs
        +
SDD harness
        +
current project state
        ↓
planning agent
        ↓
bounded phase prompt
        ↓
Codex CLI
```

---

# 3. Roles

RouteLens development has three primary actors:

```text
Planning Agent
Human Developer
Codex CLI
```

Each has a distinct responsibility.

---

# 4. Planning Agent Role

The planning agent is ChatGPT used through the web interface.

The planning agent owns **planning and meta-prompting**, not direct repository implementation.

Its responsibilities include:

- helping define and refine product requirements;
- maintaining architectural coherence;
- creating and refining the implementation roadmap;
- resolving higher-level design questions;
- interpreting implementation discoveries;
- determining whether discoveries require plan or design changes;
- preparing bounded Codex implementation prompts;
- defining acceptance criteria;
- defining verification expectations;
- preventing accidental scope expansion.

For each phase, the planning agent may consult:

```text
docs/prd.md
docs/technical-design.md
docs/implementation-plan.md
docs/development-workflow.md

AGENTS.md
APP_SPEC.md
BUILD_PLAN.md
PROJECT_STATE.md
```

Not every file must be injected wholesale into every Codex prompt.

The planning agent should extract only the context relevant to the current phase.

---

# 5. Human Developer Role

The human remains the owner of:

- product intent;
- architecture;
- major implementation tradeoffs;
- scope;
- dependency approval;
- behavioral quality;
- visual quality;
- phase acceptance;
- Git history.

The human decides whether a completed phase is acceptable.

The human also determines whether an implementation discovery requires:

- a small local adjustment;
- a technical-design change;
- a product change;
- a roadmap change;
- or a future backlog item.

---

# 6. Codex CLI Role

Codex is the primary implementation agent.

Codex is responsible for:

- inspecting existing repository state;
- reading the SDD harness;
- implementing the current bounded task;
- writing or updating tests;
- running required verification;
- fixing failures within phase scope;
- updating `PROJECT_STATE.md` when appropriate;
- reporting exactly what changed.

Codex is **not** responsible for independently redesigning RouteLens.

---

# 7. Required Codex Context

Before beginning a phase, Codex should always read:

```text
AGENTS.md
APP_SPEC.md
BUILD_PLAN.md
PROJECT_STATE.md
```

These files form the default execution context.

Codex should consult files under:

```text
docs/
```

only when the current task requires broader product, architectural, roadmap, or workflow context.

This keeps the implementation context bounded.

---

# 8. Purpose of the SDD Harness

## AGENTS.md

Defines global coding-agent rules.

Examples include:

- inspect existing code before modifying it;
- remain within current phase scope;
- preserve documented architecture;
- run verification;
- avoid unrelated cleanup;
- do not commit or push;
- stop and report significant blockers.

---

## APP_SPEC.md

Provides the condensed Codex-facing system specification.

It should capture relevant truths from:

```text
docs/prd.md
docs/technical-design.md
```

without repeating unnecessary planning discussion.

It should focus on:

- product invariants;
- architecture;
- model boundaries;
- system responsibilities;
- important constraints;
- major non-goals.

---

## BUILD_PLAN.md

Contains the **current executable phase**.

It should normally include:

- current phase;
- objective;
- relevant context;
- expected scope;
- likely affected areas;
- non-goals;
- acceptance criteria;
- verification requirements;
- stop conditions.

It may include a short reference to the next planned phase, but should remain focused on current work.

---

## PROJECT_STATE.md

Records the current reality of the repository.

It should track:

- completed phases;
- current phase;
- functionality that actually exists;
- important implementation decisions;
- known issues;
- deferred work;
- discovered source behavior;
- relevant verification results;
- current blockers;
- next recommended action.

---

# 9. Vertical-Slice Development

Implementation should proceed through narrow end-to-end slices.

Avoid:

```text
build all backend
→ build all database logic
→ build all APIs
→ build all frontend
→ integrate at the end
```

Prefer:

```text
one capability
      ↓
required backend
      ↓
required model
      ↓
required API
      ↓
required frontend
      ↓
tests
      ↓
observable working behavior
```

Example:

```text
Road Ahead
→ adapter
→ CityEvent normalization
→ Shapely relevance
→ API
→ MapLibre marker
→ route panel
→ tests
```

Each phase should make RouteLens visibly more functional.

---

# 10. Phase Preparation

Before Codex begins a phase:

1. identify the corresponding section of `docs/implementation-plan.md`;
2. review current `PROJECT_STATE.md`;
3. confirm relevant technical-design constraints;
4. update or generate the current `BUILD_PLAN.md`;
5. have the planning agent produce a bounded Codex prompt.

The prompt should not contain the entire project history.

---

# 11. Bounded Codex Prompt Structure

A typical Codex prompt should contain:

## Objective

What capability should exist when the task is complete?

## Relevant Context

Only information required to perform the task correctly.

## Expected Scope

Likely files, modules, or directories involved.

This is guidance rather than an absolute filesystem allowlist.

Codex may create a necessary:

- helper;
- fixture;
- test;
- small supporting module

when it clearly belongs to the current task.

## Non-Goals

Explicitly identify work that should not be performed.

## Architecture Constraints

Relevant requirements from `APP_SPEC.md` or `technical-design.md`.

## Acceptance Criteria

Observable conditions required for completion.

## Verification

Tests, builds, linting, and manual/live checks expected.

## Stop Conditions

Conditions where Codex should report rather than improvise.

---

# 12. Codex Local Implementation Discretion

Codex may independently decide routine local implementation details.

Examples:

- helper-function names;
- internal variable names;
- small component decomposition;
- minor utility extraction;
- test organization;
- straightforward error-handling implementation;
- internal code arrangement.

Codex does **not** need human approval for every minor implementation choice.

However, Codex must stop and report when a decision could materially affect:

- architecture;
- product behavior;
- phase scope;
- application data contracts;
- external interfaces;
- runtime dependencies;
- persistence design;
- major UX behavior.

---

# 13. Scope Discipline

Codex should implement only what is necessary for the current phase.

Avoid:

- speculative future features;
- unrelated refactors;
- dependency upgrades;
- formatting sweeps;
- architecture cleanup unrelated to the task;
- broad renaming;
- “while I’m here” improvements;
- implementation of later phases.

If unrelated issues are discovered, record/report them rather than fixing them automatically unless they directly block the current task.

---

# 14. Dependency Policy

New runtime dependencies should not be introduced casually.

Codex must stop/report before adding a significant new runtime dependency unless that dependency is already explicitly part of the approved plan.

Obvious development or test dependencies may be added only when clearly required by the current phase.

Dependencies should remain minimal.

Before adding one, consider whether the existing stack already provides the required capability.

---

# 15. External API Development Pattern

For external integrations, use:

```text
inspect live source
        ↓
understand actual response
        ↓
save representative fixture
        ↓
implement parser/adapter
        ↓
test deterministically against fixture
        ↓
integrate into application
        ↓
verify live again
```

Automated tests should not depend on the live service being available.

---

# 16. Live Integration Checks

Codex may perform live API checks when:

- network access is available;
- required credentials are present;
- the operation is safe;
- the current phase calls for integration verification.

Live checks supplement tests.

They do not replace fixture-based automated testing.

A live upstream API being temporarily unavailable should not cause the automated suite to fail.

---

# 17. Testing Responsibility

Testing is part of the implementation phase.

Codex should not treat tests as a separate future phase.

When adding deterministic behavior, Codex should add/update relevant tests during the same task.

Typical candidates include:

- source parsing;
- normalization;
- validation;
- geospatial relevance;
- cache behavior;
- API contracts;
- structured AI output parsing;
- failure isolation.

---

# 18. Selective TDD

Use test-driven development when it clearly improves implementation quality.

Good candidates include:

- source adapters;
- validation;
- geospatial calculations;
- relevance logic;
- cache-expiry logic;
- structured-output parsing;
- deterministic business rules.

TDD is not mandatory for:

- exploratory UI styling;
- map aesthetics;
- animations;
- uncertain LLM prompt behavior;
- early visual prototypes.

The goal is useful feedback, not procedural purity.

---

# 19. Verification Loop

Codex should continuously use available feedback loops while implementing.

If verification fails:

```text
implement
   ↓
run verification
   ↓
failure
   ↓
diagnose
   ↓
fix
   ↓
run verification again
```

Codex should continue this loop while:

- the work remains within phase scope;
- the acceptance criteria remain valid;
- no escalation condition has been reached.

Codex should not immediately stop after the first ordinary test failure.

---

# 20. Default Phase Verification

Unless explicitly adjusted, every meaningful phase should include:

## Backend

- relevant pytest tests;
- Ruff.

## Frontend

If frontend code changed:

- production build succeeds.

Typically:

```text
npm run build
```

## Behavioral Verification

Manually verify the capability behaves as intended.

## External Integration

Where appropriate:

- manually/live verify the relevant source.

## Git

Confirm no Git commit was made by Codex.

---

# 21. Browser Verification

When browser-based verification tools are available, Codex should use them where useful.

Examples:

- page loads;
- route appears;
- markers render;
- panel interaction works;
- camera image loads;
- obvious error state displays correctly.

Browser automation does not replace human visual QA.

The human remains responsible for judging:

- visual polish;
- readability;
- hierarchy;
- interaction quality;
- whether the application feels presentation-ready.

---

# 22. RouteLens Human Review Policy

RouteLens deliberately uses a lighter human-review model than the user's security-focused projects.

Human review should focus carefully on:

- architecture;
- external source adapters;
- normalized models;
- geospatial logic;
- AI contracts;
- prompts that materially affect structured behavior;
- persistence;
- caching;
- dependency additions;
- API key handling;
- important error handling;
- source-failure behavior.

Review may be lighter for:

- ordinary React layout code;
- Tailwind styling;
- simple presentational components;
- trivial utilities;
- straightforward generated helpers.

For those areas, behavioral verification may be more valuable than line-by-line inspection.

---

# 23. Fresh-Context Review

A separate fresh-context AI review is optional rather than required after every phase.

Use it when:

- a milestone completes;
- architectural complexity increases;
- the implementation feels uncertain;
- several phases have accumulated;
- a major AI/data pipeline has just been completed;
- final integration approaches completion.

Useful milestone checkpoints include approximately:

```text
after first complete telemetry slice
after camera + multimodal AI pipeline
after full journey analysis integration
```

These are recommendations, not mandatory gates.

---

# 24. Codex Escalation Conditions

Codex must stop and report rather than improvise when it encounters:

- conflicting requirements;
- architectural contradiction;
- missing credentials or required access;
- requirement for a significant new dependency;
- destructive operation not explicitly approved;
- upstream API/schema reality that materially invalidates the planned design;
- inability to meet acceptance criteria without expanding phase scope;
- a required product decision;
- a data-contract change that affects other major components.

Codex should explain:

- what was discovered;
- why it matters;
- what part of the plan is affected;
- possible options if obvious.

The planning agent and human then decide how to proceed.

---

# 25. Small Implementation Adaptations

Not every surprise requires escalation.

Codex may adapt locally when the discovery:

- does not alter product behavior;
- does not change architecture;
- does not add significant dependencies;
- does not alter public contracts;
- remains clearly inside the current phase.

Example:

```text
Expected upstream field:
updated_at

Actual field:
last_updated
```

If the adapter can simply normalize the actual field into the existing RouteLens model, Codex may continue.

---

# 26. Artifact Routing Rule

When implementation reveals new information, update the artifact that owns that kind of truth.

## Repository Reality

Examples:

- phase completed;
- endpoint now exists;
- known issue;
- actual API behavior;
- implementation limitation.

Route to:

```text
PROJECT_STATE.md
```

Codex may update this file as part of a phase.

---

## Codex-Facing Application Contract

If a change affects the condensed implementation rules Codex should follow:

```text
APP_SPEC.md
```

Update deliberately.

Do not allow this file to silently drift away from the planning documents.

---

## Product Behavior / Scope

Examples:

- supported workflow changes;
- MVP scope changes;
- product requirement removed or added;
- explicit non-goal changes.

Route to:

```text
docs/prd.md
```

Codex must not modify this file unless explicitly instructed.

---

## Architecture / Technical Decisions

Examples:

- different integration strategy;
- changed persistence architecture;
- new model boundary;
- changed API design;
- different caching strategy.

Route to:

```text
docs/technical-design.md
```

Codex must not modify this file unless explicitly instructed.

---

## Implementation Roadmap

Examples:

- phases reordered;
- new phase required;
- planned slice split or merged;
- later work deferred.

Route to:

```text
docs/implementation-plan.md
```

Codex must not modify this file unless explicitly instructed.

---

## Current Executable Task

Changes to what Codex should implement right now belong in:

```text
BUILD_PLAN.md
```

---

# 27. Higher-Level Documentation Protection

Codex may update:

```text
PROJECT_STATE.md
```

when the current phase requires it.

Codex should not modify:

```text
docs/prd.md
docs/technical-design.md
docs/implementation-plan.md
docs/development-workflow.md
```

unless the planning agent/human explicitly instructs it to do so.

This prevents implementation discoveries from silently rewriting project intent or architecture.

---

# 28. BUILD_PLAN.md Lifecycle

`BUILD_PLAN.md` should primarily describe the current phase.

Preferred structure:

```text
CURRENT PHASE
Objective
Relevant Context
Scope
Non-Goals
Requirements
Acceptance Criteria
Verification
Stop Conditions

NEXT
short reference only
```

After a phase is accepted, the planning agent can replace/update the file for the next phase.

Do not allow `BUILD_PLAN.md` to grow into a duplicate of the full implementation roadmap.

---

# 29. PROJECT_STATE.md Lifecycle

`PROJECT_STATE.md` should evolve continuously.

At the end of a phase, it should reflect:

- what was actually built;
- what tests pass;
- what was learned;
- known limitations;
- deviations from plan;
- current phase status;
- next expected phase.

This document represents **reality**, not intent.

---

# 30. Standard Codex Completion Report

At the end of a phase, Codex should produce a concise structured report.

It should contain:

## Files Changed

Which files were created or modified.

## Behavior Added

What now works that did not work before.

## Verification Performed

Examples:

```text
pytest ...
ruff check ...
npm run build
live API check
browser verification
```

## Results

Whether the required checks passed.

## Known Limitations

Anything intentionally incomplete or currently constrained.

## Deviations

Anything implemented differently from the original phase plan.

If there were no meaningful deviations, state that clearly.

## Project State

Confirm whether `PROJECT_STATE.md` was updated.

## Git Status

Explicitly confirm:

> No commit or push was performed.

---

# 31. Human Phase Review

After Codex completes the phase:

1. review the completion report;
2. inspect important diffs;
3. run or confirm relevant behavior;
4. visually inspect frontend behavior if applicable;
5. evaluate any limitations/deviations;
6. request fixes if needed;
7. verify project state;
8. manually create the Git commit when satisfied.

A phase is accepted only after human review.

---

# 32. Git Policy

Git history is human-controlled.

Codex may:

- inspect `git status`;
- inspect diffs;
- inspect previous commits when useful;
- report changed files.

Codex must not:

- commit;
- amend;
- push;
- force-push;
- merge;
- rebase;
- create tags;
- rewrite history.

The human creates each accepted phase checkpoint.

---

# 33. Normal Codex Permissions

RouteLens does not require a restricted-agent containment architecture.

Codex may normally:

- read repository files;
- modify project files;
- create appropriate files;
- run tests;
- run linters;
- run builds;
- start local development commands when useful;
- install already-approved dependencies;
- make relevant safe network calls where environment permits.

This project does not require:

- sandbox-policy engineering;
- adversarial agent containment;
- filesystem denial testing;
- network-denial testing;
- restricted privilege design.

Normal development safeguards are sufficient.

---

# 34. Secrets and Credentials

Codex must preserve basic credential hygiene.

Rules:

- secrets belong in `.env`;
- `.env` must remain Git-ignored;
- secrets must not be hardcoded;
- secrets must not be copied into fixtures;
- secrets must not appear in logs or completion reports;
- `.env.example` should contain variable names/placeholders only.

If required credentials are absent, Codex should report the missing dependency rather than inventing values.

---

# 35. Destructive Operations

Codex should not perform destructive operations without explicit approval.

Examples include:

- deleting large data sets;
- deleting substantial project directories;
- resetting Git state;
- replacing major architecture wholesale;
- destructive database migrations;
- removing existing functionality unrelated to the current phase.

If such an operation appears necessary, stop and report.

---

# 36. Implementation Discoveries

Development will reveal facts that planning could not predict.

Examples:

- upstream API differs from documentation;
- camera timestamps are inconsistent;
- routing alternatives are limited;
- a weather interval is less granular than expected;
- transit relevance requires different heuristics.

These discoveries should be classified rather than silently patched into higher-level design.

The question is:

> Does this change implementation detail, architecture, roadmap, or product behavior?

Then route the information according to the artifact ownership rules in this document.

---

# 37. Planning Feedback Loop

The development process is iterative.

```text
Plan phase
   ↓
Codex implements
   ↓
tests + real behavior
   ↓
new information
   ↓
classify discovery
   ↓
update correct artifact if necessary
   ↓
prepare next phase
```

The implementation plan is stable guidance, not immutable scripture.

Changes should be evidence-driven.

---

# 38. Avoiding Context Bloat

Do not rely on one enormous Codex session for the whole project.

Prefer:

- bounded phases;
- durable repo documentation;
- fresh task prompts;
- current `PROJECT_STATE.md`;
- human Git checkpoints.

The conversation history should not be required for Codex to understand the repository.

---

# 39. Planning-Agent Meta-Prompting

For each phase, the planning agent should use the durable artifacts to generate a focused prompt.

The prompt should emphasize:

- what Codex needs to know;
- what it must preserve;
- what it must implement;
- what it must not implement;
- how success is verified;
- when it must stop.

The planning agent should not use each phase as an excuse to redesign the whole project.

---

# 40. Phase Execution Loop

The standard RouteLens development loop is:

```text
1. Human + planning agent review current state

2. Select next phase from implementation-plan.md

3. Prepare/update BUILD_PLAN.md

4. Planning agent creates bounded Codex prompt

5. Codex reads:
   AGENTS.md
   APP_SPEC.md
   BUILD_PLAN.md
   PROJECT_STATE.md

6. Codex implements

7. Codex writes/updates tests

8. Codex runs verification

9. Codex iterates on ordinary failures

10. Codex updates PROJECT_STATE.md where appropriate

11. Codex produces completion report

12. Human reviews behavior + important code

13. Fix loop if required

14. Human manually commits

15. Begin next phase
```

---

# 41. Review Philosophy

RouteLens is designed to demonstrate effective AI-assisted software engineering rather than maximum manual code scrutiny.

The goal is not:

> Human manually verifies every generated line.

The goal is:

> Human retains control of product, architecture, important implementation decisions, and quality while using automated feedback and behavioral verification to safely increase implementation throughput.

This is intentionally different from a security-control project where line-level and adversarial review may be much heavier.

---

# 42. Development Priorities

When tradeoffs arise, prioritize:

1. correct product behavior;
2. working end-to-end slices;
3. architecture consistency;
4. deterministic verification;
5. graceful failure;
6. clear UI behavior;
7. presentation quality;
8. internal elegance.

Do not sacrifice working user-visible functionality for speculative abstraction.

---

# 43. No Premature Perfection

Initial implementations may be scaffolds.

A component may begin simple if it:

- satisfies current requirements;
- exposes useful real-world behavior;
- can be tested;
- does not create obvious architectural debt.

Refinement should be driven by observed need.

Preferred pattern:

```text
scaffold
→ run
→ observe
→ learn
→ refine
```

rather than attempting perfect infrastructure before the first real workflow exists.

---

# 44. Final Development Principle

RouteLens development should preserve the strengths of the user's existing spec-driven workflow while adding clearer durable planning artifacts and stronger vertical-slice execution.

The overall model is:

```text
PLAN CLEARLY
        ↓
DOCUMENT DURABLY
        ↓
TRANSLATE INTO BOUNDED AGENT CONTEXT
        ↓
IMPLEMENT A REAL VERTICAL SLICE
        ↓
VERIFY OBJECTIVELY
        ↓
REVIEW IMPORTANT DECISIONS
        ↓
HUMAN COMMITS
        ↓
FEED REALITY BACK INTO THE PLAN
        ↓
REPEAT
```

The planning agent owns planning clarity.

Codex owns bounded implementation.

The human owns final judgment and project direction.
