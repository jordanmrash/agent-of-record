# Synthetic Incident

**Process:** Fictional month-end workpaper preparation
**Input:** Four required source segments
**Observed input:** Segment D absent
**Failed behavior:** The workflow processed segments A through C and produced a complete-looking output without identifying the omission.
**Detected by:** Human review against the input manifest
**Risk:** An incomplete workpaper could be relied upon because the output shape appeared complete.
**Required change:** Validate the complete segment manifest before any calculation; missing required segments must stop execution and identify the missing item.
