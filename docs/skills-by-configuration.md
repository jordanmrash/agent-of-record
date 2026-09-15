# Skills and bridges by configuration

The repository ships every skill to every product. A skill that duplicates something the
host already does in one configuration is kept and marked, not deleted: the person disables
it in the host and re-enables it when the configuration changes. This page is the matrix.
Each affected skill also carries a "When this skill is redundant" section.

Three configurations matter:

| Configuration | What the host provides on its own |
|---|---|
| **Copilot Cowork** (Windows, hosted route) | M365 tools. No files, no browser, no memory, no skill list, no shell on the machine. Everything else comes from this repository through the four bridges. |
| **Claude Cowork, signed in to an Anthropic account** | Connected folders, a browser (built-in or Claude in Chrome), account memory shared with chat, a plugin installer and a skill list under Customize, a sandboxed session shell that is not the machine. |
| **Claude Cowork under third-party inference** (a gateway such as Bedrock, Vertex, OpenRouter, or a local model through Ollama or LM Studio) | The same harness, folders, browser, plugins and MCP servers. The session is signed out of the Anthropic account, so **account memory should be assumed absent until tested**. Weaker models follow delivered rules less reliably; the enforced controls do not depend on the model. |

## Skills

| Skill | Copilot Cowork | Claude, Anthropic account | Claude, third-party inference |
|---|---|---|---|
| command-bridge | needed | needed | needed |
| self-improvement | needed | needed | needed - lean on it; enforced gates matter more with a weaker model |
| dream-cycle | needed | needed | needed |
| gamma-tango | needed | needed | needed |
| not-a-robot | needed | needed | needed |
| persistent-memory | needed (no host memory) | redundant (account memory) | **keep enabled until account memory is confirmed present** |
| local-file-bridge | needed | redundant (connected folders) | redundant unless built-in file tools were removed by policy |
| playwright-skill | needed | redundant (built-in browser) | redundant unless the built-in browser was removed by policy |
| git-bridge | needed | redundant (git through the executor) | redundant, same reason |
| skill-menu | needed | redundant (Customize lists skills) | redundant (same panel) |

How to disable: under Claude Cowork, Customize lists the plugin and its skills; turn a skill
off there, or the whole plugin. Under Copilot Cowork the skills load from the config root's
`skills` folder; move a skill out of that folder to disable it. Nothing in the repository
needs to change in either case.

## Bridges

| Bridge | Copilot Cowork | Claude Cowork (either model) |
|---|---|---|
| Approved command executor | yes - `run_batch_file` | yes - `aor-batch-exec`, the only server the route registers; the session shell is a sandboxed VM, so this is the only path to the machine |
| Filesystem | yes | not registered - connected folders cover it, and a second permission model over the same files is an audit hole |
| Browser | yes | not registered - the host drives its own |
| Power Automate | yes, Windows only | no - it authenticates against a tenant, which is a data-boundary decision, not a configuration |

If an administrator removes the host's built-in file or browser tools (third-party
inference exposes that control), the Windows launchers `Startup/fs-server.cmd` and
`Startup/pw-server.cmd` still exist; the POSIX launchers were retired in `4ab0051` and can be
restored from `6cfc77c`. Register only what the host then lacks.

## The model behind the session

Third-party inference changes the model, not the host, so the route above is unchanged.
Three things to do differently:

1. **Test memory before retiring `persistent-memory`.** Signed out of the Anthropic
   account, account memory may be absent. Record the result in `docs/evidence/`.
2. **Expect less from delivered rules.** The digest, the `SKILL-LESSONS` blocks and the
   executor's operating-rules block are read by the model; the executor's schema and
   refusals, `job_lint`, `lesson_gate` and `release_check` are not. Keep the tool surface small.
3. **The data boundary moves.** A local model keeps data on the machine; an approved
   enterprise gateway keeps it inside that provider. The remaining question on a managed
   device is software approval, not data flow.

Windows is expected to reach parity with macOS on the gateway integrations; the pages are
written on that assumption, and every claim still needs one real call before it is marked
operated.
