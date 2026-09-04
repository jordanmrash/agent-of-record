# This folder is read-only

This is your durable user folder (cross-session). It is READ-ONLY to the agent — direct writes will fail. To create or edit a file here:

- Build/scratch in `working/` (writable), then use the **CopyArtifact** tool with surface='user' to promote it here.
- To edit an existing file in place, use **EditArtifact** with surface='user' — JSON delta ops, Markdown/txt CRDT updates, or Office OOXML patches. Batch every change for a file into ONE call.

The runtime applies changes to durable storage and streams the patches to the user for live concurrent editing.
