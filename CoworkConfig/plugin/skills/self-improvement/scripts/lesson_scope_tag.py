#!/usr/bin/env python3
"""Propose Routes/Platforms scope for untagged lesson entries.

    python3 lesson_scope_tag.py            # dry run: counts and the entries to review
    python3 lesson_scope_tag.py --apply    # write the fields into cowork-lessons.md

ASSISTIVE, NOT AUTHORITATIVE. It tags by pattern, and the first version of it was
wrong in a way worth keeping in mind: it scoped `bridge-8933-arg-name` to Windows
because the entry's `Failed:` block cited a `.bat`, when the rule -- call the tool
with `file=`, not `path=` -- is universal. Scope is decided on what the RULE says,
so this reads the Pattern-Key and the Rule and ignores the rest, and it prints the
entries whose body mentions route machinery while their rule stayed universal so a
person can check them.

It never removes a field, never retags an entry that already carries one, and never
touches an entry with no Pattern-Key. Absent means everywhere, so its failure mode is
leaving a rule un-narrowed, not deleting it.
"""
import re, sys, pathlib, collections
p = pathlib.Path("CoworkConfig/cowork-memory/cowork-lessons.md")
text = p.read_text()
apply_changes = "--apply" in sys.argv

# The RULE line is what the bridge serves into a job result, so the rule decides the
# scope. Evidence, Failed and Why often cite a .bat example for a universal rule; those
# must not narrow it. Route machinery is structural, so the Pattern-Key and the Rule
# together decide that.
COPILOT_MACHINERY = re.compile(
    r"devtunnel|dev tunnel|supergateway|ports? panel|set .{0,12}PUBLIC|tunnel hop"
    r"|(?<![\w-])893[124](?![\w-])|playwright bridge|filesystem bridge|fs-server|pw-server"
    r"|power automate|flow-server|flowbridge"
    r"|watchdog|tasks\.json|KnownGood|schtask"
    r"|onedrive|sharepoint|graph api|user surface|jordan-local-|jordan-approved-"
    r"|VS ?Code|listening state|holds the port|the Ports|bridge listener|restart(?:ing)? (?:the )?bridge", re.I)
WINDOWS_SHAPE = re.compile(
    r"\.bat\b|\.cmd\b|cmd\.exe|reg query|CRLF|C:\\\\Users|powershell|fsutil|Get-PSDrive"
    r"|cd /d|%USERPROFILE%|HKCU", re.I)

out, counts, flagged = [], collections.Counter(), []
parts = re.split(r"(?m)^(### .+)$", text)
out.append(parts[0])
for i in range(1, len(parts), 2):
    head, body = parts[i], parts[i + 1]
    if "**Routes:**" in body or "**Platforms:**" in body:
        counts["already tagged"] += 1; out.append(head); out.append(body); continue
    key  = (re.search(r"(?m)^- \*\*Pattern-Key:\*\* (\S+)", body) or [None, ""])[1]
    rule = (re.search(r"(?m)^- \*\*Rule:\*\* (.+)$", body) or [None, ""])[1]
    scope_text = f"{key} {rule}"

    fields = []
    if COPILOT_MACHINERY.search(scope_text):
        fields.append("- **Routes:** copilot"); counts["Routes: copilot"] += 1
    elif WINDOWS_SHAPE.search(rule):
        fields.append("- **Platforms:** windows"); counts["Platforms: windows"] += 1
    else:
        counts["unscoped (both)"] += 1
        # An entry whose BODY is route machinery but whose RULE is not: worth a human look.
        if rule and COPILOT_MACHINERY.search(body):
            flagged.append((key, rule[:78]))
        out.append(head); out.append(body); continue

    m = re.search(r"(?m)^- \*\*Pattern-Key:\*\* .+$", body)
    if not m:
        counts["no Pattern-Key - left alone"] += 1; out.append(head); out.append(body); continue
    body = body[:m.end()] + "\n" + "\n".join(fields) + body[m.end():]
    out.append(head); out.append(body)

for k, v in counts.most_common(): print(f"  {v:3d}  {k}")
if flagged:
    print(f"\n  {len(flagged)} unscoped entries whose body mentions route machinery (rule kept universal):")
    for k, r in flagged[:12]: print(f"     {k}: {r}")
if apply_changes:
    p.write_text("".join(out)); print("\nwritten")
else:
    print("\n(dry run)")
