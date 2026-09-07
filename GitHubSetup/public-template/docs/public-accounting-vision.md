# Public Accounting Needs an Agent Foundation

## The problem is larger than task automation

Public accounting is adopting generative AI quickly. Most early adoption begins with individual productivity: drafting, summarizing, research assistance, spreadsheet help, or a prototype that answers questions from a document library.

Those uses are valuable, but they do not establish an operating model for repeated professional work.

The profession needs to answer a harder set of questions before agents can safely participate in tax, accounting, attest-supporting, advisory, and internal operational processes:

- What evidence may the agent rely on?
- Which calculations must remain deterministic?
- When must the process stop rather than infer a missing fact?
- What may the agent remember across periods and engagements?
- How is an incorrect memory corrected?
- What actions require approval?
- What evidence proves the control operated?
- Who owns the workflow after the original builder moves on?
- How is the process changed, tested, released, and rolled back?

An isolated prompt cannot answer these questions. A collection of prompts cannot answer them either.

## The proposed foundation

This repository treats an accounting agent as a controlled operating system with six foundational layers.

### 1. Evidence and provenance

Professional conclusions should be traceable to the source documents, inputs, rules, and calculations that support them. Persistence does not make a stored statement true; memory needs provenance, confidence, correction, and retirement.

### 2. Deterministic boundaries

Models are useful where ambiguity and judgment exist. Invariants, arithmetic, reconciliations, schema validation, completeness tests, and control totals belong in code.

The boundary is not “AI versus automation.” It is ambiguity versus invariance.

### 3. Human-approved execution

Human-in-the-loop is meaningful only when the person sees the proposed action at the point where it can occur. A general policy saying that a person remains responsible is not an execution control.

### 4. Durable operational learning

A failed attempt should not disappear with the session. The system records what failed, what worked, why, and what evidence supports the conclusion. Recurring lessons are delivered into the skills and tools that own the failure.

### 5. Behavioral verification

A rule is not effective merely because it appears in a prompt or a skill. The system tests three different tasks with the rule present and compares them with a control where the rule is withheld. An intervention that the model would have followed anyway is measured as inert, not celebrated.

### 6. Audit and change management

The working configuration is versioned. Publication is built from a clean tree. Changes are attributable, reviewable, testable, and reversible. Production environments are classified explicitly rather than guessed from their names.

## The role of professional judgment

This foundation does not automate professional responsibility away.

Professional judgment remains human-owned when a person:

- Defines the acceptable result.
- Approves sensitive actions.
- Resolves contradictory evidence.
- Decides whether a stored lesson is valid.
- Determines whether a workflow may move into production.
- Signs or otherwise assumes responsibility for the final work.

The agent can organize evidence, execute approved mechanics, identify discrepancies, and preserve institutional knowledge. It cannot become the accountable professional.

## How applied skills fit

Applied public-accounting skills sit above the foundation:

```text
Foundation
├── Evidence and provenance
├── Memory and correction
├── Deterministic calculations
├── Approval boundaries
├── Behavioral verification
└── Audit and change management

Applied skills
├── Tax provision
├── State apportionment
├── Journal entries and footnotes
├── Workpaper intake and review
├── Reconciliation and close
├── Research and citation
└── Professional communication
```

An applied skill should not be treated as complete until it defines:

1. Intended user and professional purpose.
2. Required inputs and their validation.
3. Evidence and provenance requirements.
4. Deterministic calculations and tie-outs.
5. Conditions that cause a hard stop.
6. Review and approval points.
7. Output contract and audit record.
8. Normal, boundary, failure, and sensitive-data tests.
9. Owner, status, version, and maintenance plan.

## Adoption model for firms

### Stage 1: Exploration

Use low-risk prototypes to expose undocumented processes, missing policies, inconsistent terminology, and weak data contracts.

### Stage 2: Governed workflow

Decompose the process, enforce input contracts, move calculations into code, add failure protocols, preserve evidence, and establish human review.

### Stage 3: Controlled agent

Add identity, environment segregation, production policy, action approval, audit logging, monitoring, release management, and formal ownership.

### Stage 4: Portfolio operating model

Standardize the foundation so individual skills share common controls, evidence formats, test patterns, deployment practices, and governance.

## The intended contribution

The goal of this project is not to claim that every accounting process should become an agent.

It is to provide a practical, measurable foundation for deciding which processes should, what controls they require, and how a firm can learn from operating them without losing accountability.
