@echo off
REM ============================================================
REM  Cowork Power Automate Bridge -- raw stdio MCP server (port 8934)
REM
REM  Exposes flow lifecycle tools:
REM      list_flows, get_flow, create_flow, update_flow,
REM      delete_flow, set_flow_state, bridge_status
REM
REM  Built because the Power Platform CLI cannot reach flows:
REM  no `pac flow` group, and `pac auth token` mints only the
REM  api.powerplatform.com audience, which 401s against both the
REM  Dataverse workflow table and api.flow.microsoft.com.
REM  Measured 2026-09-02, see Outputs\2026-09-02 - Flow CRUD Interface Probe.
REM
REM  SAFETY: the server refuses by default. No environment is
REM  allowlisted, read_only is true, allow_delete is false, and
REM  auth_strategy is "none" - so every flow tool returns a clear
REM  NOT_CONFIGURED or REFUSED message until deliberately widened
REM  in FlowBridge\flow-bridge.config.json.
REM
REM  Implementation: Startup\FlowBridge\flow-mcp-server.js
REM
REM  Uses the already-installed Node runtime. No npx. No installs.
REM  No package dependencies.
REM
REM  Supergateway is invoked by tasks.json, which points --stdio at
REM  this file - matching the pattern used by fs-server.cmd (8932)
REM  and exec-server.cmd (8933).
REM ============================================================

cd /d "C:\Users\YOURUSER\Documents\COPILOT_COWORK\Startup\FlowBridge"

node "C:\Users\YOURUSER\Documents\COPILOT_COWORK\Startup\FlowBridge\flow-mcp-server.js"
