# Synthetic Lesson

The entry below is in the exact format the lessons corpus uses, so the real
verification harness can read it. Nothing in it describes a real process.

### A complete-looking workpaper was built from incomplete inputs
- **Pattern-Key:** workpaper-required-segment-missing
- **Date:** 2026-09-01
- **Trigger:** failure
- **Rule:** Validate the required input manifest before processing. If any required segment is absent, stop and list the missing segment; never produce a success-shaped partial output.
- **Delivered-to:** synthetic-workpaper-skill
- **Failed:** Continued with available input and relied on the final output's structure as evidence of completeness.
- **Why:** Output formatting and calculation success do not establish input completeness.
- **Worked:** A deterministic manifest check (`validate_manifest.py`) runs before calculation and returns a non-zero result when a required segment is absent.
- **Evidence:** measured - `validate_manifest.py inputs/incomplete` exits 3 and names Segment D; `inputs/complete` exits 0
- **Hits:** 1
