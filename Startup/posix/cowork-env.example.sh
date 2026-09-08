# ============================================================
#  Local environment for the POSIX bridge launchers.
#
#  Copy to cowork-env.sh and edit. The real file is gitignored,
#  which is what keeps your account name and folder layout out of
#  the repository - scripts/public_scan.py refuses a tree that
#  carries a real home directory path.
#
#      cp cowork-env.example.sh cowork-env.sh
#
#  Nothing here is required. Every launcher runs with sane
#  defaults when this file is absent; these settings exist
#  because the correct value differs per machine and cannot be
#  guessed by the repository.
# ============================================================

# ---- What Cowork itself loads -------------------------------
# Skills, copilot-instructions.md and cowork-memory. This becomes
# the filesystem bridge's third root, so the agent can write its
# own corpus directly instead of waiting on cloud replication.
#
# There is no portable default. Find yours and paste it in:
#
#   macOS, OneDrive for Business:
#     $HOME/Library/CloudStorage/OneDrive-<Org>/Documents/Cowork
#   macOS, personal OneDrive:
#     $HOME/OneDrive/Documents/Cowork
#   Linux or no cloud folder at all:
#     leave unset - the in-repo CoworkConfig/ is used instead
#
# export COWORK_CONFIG_ROOT="$HOME/Library/CloudStorage/OneDrive-Example/Documents/Cowork"

# ---- Playwright ---------------------------------------------
# chrome (default), msedge, chromium or webkit. The profile keeps
# your signed-in sessions; the bridge never sees a password. Use a
# test account until you have watched the approval flow work.
# export COWORK_PW_BROWSER="chrome"
# export COWORK_PW_PROFILE="$HOME/pw-sso-profile"

# ---- Tooling root -------------------------------------------
# Each launcher derives this from its own location, so it is
# already correct for a clone in any directory. Set it only if you
# are deliberately pointing the bridges at a different tree.
# export COWORK_ROOT="$HOME/Documents/COPILOT_COWORK"
