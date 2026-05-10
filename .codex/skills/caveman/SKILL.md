---
name: caveman
description: Rewrite prose in terse, telegraphic, abbreviation-heavy style. Drops articles, connective filler, and verbose phrasing while preserving every fact, code block, path, URL, and CLI invocation.
triggers: ["caveman", "terse", "telegraphic", "compress prose", "shorten docs", "abbreviate"]
argument-hint: "[path-or-paste]"
---

# Caveman

Compress prose. Keep facts. Drop fluff.

Repo precedent: commit `a1c61ae "caveman README and DEVELOPER"` rewrote `README.md` and `DEVELOPER.md` in this style. Use that diff as the canonical reference when uncertain.

## When to activate

User says "caveman it", "make it terse", "shorten this", "compress", "telegraphic", or pastes prose and asks for the caveman version. Also when editing `README.md`, `DEVELOPER.md`, `CHANGELOG.md`, or other top-level docs in this repo to keep the established voice consistent.

Do NOT activate for code comments, commit messages governed by the Lore protocol, error messages, or user-facing CLI help text — those have their own contracts.

## The transformation rules

Apply in order. Stop as soon as the sentence is tight.

### 1. Strip articles where meaning survives

| Before | After |
|---|---|
| "the library" | "lib" |
| "a fast all-in-one Python package manager" | "fast all-in-one Python pkg manager" |
| "the workflow builds the package" | "workflow builds pkg" |

### 2. Replace prose connectives with symbols

| Before | After |
|---|---|
| "leads to", "results in", "so that" | `->` |
| "is", "equals", "means" (when defining) | `=` |
| "for example" / "e.g." inline | `e.g.` (keep) |
| "such as", "including" | `:` or parens |
| "and / or / plus" between short items | `+` or `/` |

### 3. Standard abbreviations

| Full | Caveman |
|---|---|
| library | lib |
| package | pkg |
| repository | repo |
| configuration | config |
| environment | env |
| documentation | docs |
| directory | dir |
| variable / variables | var / vars |
| dependency / dependencies | dep / deps |
| pull request | PR |
| application | app |
| database | DB |
| development | dev |
| production | prod |

### 4. Collapse multi-line prose

If two or three sentences describe one fact, merge them into one line with `,` `;` or `->`.

Before:
```
The .github/workflows/release.yml workflow triggers on any tag matching v*
and publishes to PyPI using OIDC trusted publishing — no stored API tokens
needed.
```

After:
```
.github/workflows/release.yml triggers on tags matching v*, publishes to PyPI via OIDC trusted publishing — no stored API tokens needed.
```

### 5. Drop hedges and pleasantries

Remove: "please", "you can", "you may want to", "it is recommended that", "in order to", "as needed", "if applicable", "kindly".

Keep imperative voice: "Run X", "Set Y", "Open Z".

### 6. Tables stay tables

Markdown tables, code fences, file paths, URLs, env-var names, CLI flags, and command invocations are **never** abbreviated or compressed. They are exact. Caveman the prose around them.

### 7. Punctuation tightening

- "→" → `->`  (ASCII arrow, matches repo convention)
- Smart quotes → straight quotes
- "—" stays as em-dash for asides
- Trailing periods on lone fragments may be dropped

## Things to NEVER touch

- Code blocks (```...```)
- Inline `code spans`
- File paths: `src/s3peek/cli.py`, `~/.config/s3peek/config.toml`
- URLs
- Env-var names: `FIREFLY_URL`, `AWS_ACCESS_KEY_ID`
- CLI flags / command invocations: `s3peek firefly --server ...`
- Numerical values, version constraints, semver
- Proper nouns: PyPI, IPAC, STScI, Homebrew, GitHub
- Error messages and exception class names

## Workflow

1. Read the target file (or accept pasted prose).
2. Identify which sections are pure prose vs. structured (tables, code, lists of paths).
3. Apply rules 1–7 to prose only.
4. Show a diff-style preview if the input is multi-paragraph; for short input just emit the rewrite.
5. Confirm the line count dropped meaningfully (typically 15–35% shorter) without losing facts.
6. Preserve trailing newline behavior of the original file.

## Examples

### Sentence-level

Before:
```
Copy `.env.example` to `.env` and fill in as needed. Variables are never required for the test suite (moto mocks AWS). They are only needed when pointing at a real S3 bucket or a live Firefly server.
```

After:
```
Copy `.env.example` to `.env`, fill as needed. Vars never required for tests (`moto` mocks AWS). Only needed for real S3 bucket or live Firefly server.
```

### Heading + paragraph

Before:
```
## Setup with uv (recommended)

[uv](https://github.com/astral-sh/uv) is a fast all-in-one Python package manager.
```

After:
```
## Setup with uv (recommended)

[uv](https://github.com/astral-sh/uv) = fast all-in-one Python pkg manager.
```

### List item

Before:
```
- **No local state** — no database, no cache file. All navigation state is in-memory for the session.
```

After:
```
- **No local state** — no DB, no cache file. All navigation state in-memory per session.
```

## Anti-patterns

Do not:

- Drop facts. "Variables are never required for the test suite (moto mocks AWS)" → "vars not required" loses the *why*. Keep `(moto mocks AWS)`.
- Caveman code comments. Comments need to be readable by future humans without a decoder ring.
- Caveman commit messages. Those follow the Lore Commit Protocol in `AGENTS.md`.
- Translate proper nouns. "GitHub Actions" stays "GitHub Actions", not "GH Actions".
- Compress error messages. UX requires explicit, complete error text.

## Verification

After rewriting, do a fact-pairing pass: every `noun, verb, qualifier` triple in the original must still appear (in some compressed form) in the output. If you cannot find a fact in the rewrite, you compressed too far — restore it.

## Related

- `/note` — informal, ephemeral notes (this skill is for durable docs)
- Lore Commit Protocol (`AGENTS.md`) — owns commit-message style; do not caveman commits
