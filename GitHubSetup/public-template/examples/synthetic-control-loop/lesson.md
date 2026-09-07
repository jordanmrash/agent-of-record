# Synthetic Lesson

**Pattern-Key:** `workpaper-required-segment-missing`
**Trigger:** failure
**Rule:** Validate the required input manifest before processing. If any required segment is absent, stop and list the missing segment; never produce a success-shaped partial output.
**Failed:** Continued with available input and relied on the final output's structure as evidence of completeness.
**Why:** Output formatting and calculation success do not establish input completeness.
**Worked:** A deterministic manifest check runs before calculation and returns a non-zero result when a required segment is absent.
**Evidence:** A negative test removes Segment D and confirms that the process stops before producing the workpaper.
