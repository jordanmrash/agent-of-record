#!/usr/bin/env node
/* ============================================================================
 *  Cowork Power Automate Bridge -- flow lifecycle MCP server   v0.2.0
 *  C:\Users\YOURUSER\Documents\COPILOT_COWORK\Startup\FlowBridge\flow-mcp-server.js
 *
 *  Built by Jordan Rash, Director, Tax Transformation and Automation.
 *
 *  WHAT CHANGED IN v0.2.0, AND WHY (all measured 2026-09-02)
 *
 *  v0.1.0 aimed at api.flow.microsoft.com using client_credentials. Both were
 *  wrong, for reasons that are now measured rather than assumed:
 *
 *    1. Jordan CANNOT self-register an Entra app. The portal's create blade
 *       returns "You do not have access", error 401. App-only would then need
 *       a Power Platform ADMIN to register the service principal - Microsoft
 *       is explicit that an SPN cannot register itself. So client_credentials
 *       was never reachable by him alone.
 *    2. CORRECTED 2026-09-02 (v0.4.0): the original wording here said
 *       api.flow.microsoft.com "is not a supported API and is not even a valid
 *       token audience". That conflated two different things and was wrong.
 *       The AUDIENCE is https://service.flow.microsoft.com - an identifier with
 *       no DNS record. The HOST you call is https://api.flow.microsoft.com.
 *       Both are real and both now work here, measured. Dataverse remains the
 *       right surface for flow DEFINITIONS; the Flow service owns RUNS.
 *    3. Device code is blocked by the tenant's Conditional Access. Interactive
 *       authorization-code + PKCE on a loopback redirect is NOT that flow and
 *       goes through cleanly - proven end to end at 11:35 on 2026-09-02:
 *       read, PATCH statecode on, PATCH statecode off, DELETE, all OK.
 *    4. Privileges were verified BEFORE this was written. Jordan holds
 *       prvReadWorkflow, prvCreateWorkflow, prvWriteWorkflow and
 *       prvDeleteWorkflow. He does NOT hold prvBulkDelete, which is why
 *       pac data bulk-delete was refused - a global privilege, unrelated.
 *
 *  So: delegated interactive auth, Dataverse Web API, no admin required.
 *
 *  TOKEN CACHING IS STRUCTURAL, NOT COSMETIC
 *    This bridge runs STATELESS behind supergateway, which is why editing
 *    this file takes effect without a restart - the process is re-spawned.
 *    An in-memory token therefore does NOT survive between tool calls. With
 *    token_cache_file empty, EVERY call would open a browser. Set it to a
 *    path OUTSIDE the git repo to make the bridge usable. It holds a refresh
 *    token: treat it as a credential.
 *
 *  SAFETY MODEL -- unchanged from v0.1.0, deliberately
 *    read_only defaults true       -> create/update/delete/set_state refuse
 *    allowed_environments []       -> every environment refuses
 *    allow_delete false            -> delete refuses even when writable
 *    prod-named environments refuse unless named in allow_prod
 *    delete requires confirm_name == the flow's CURRENT display name
 *    every mutating attempt is audited, refusals included
 *
 *  A note on delete: this bridge deletes ONE row addressed by GUID in the
 *  URL. It deliberately does NOT use pac data bulk-delete, whose omitted
 *  filter targets an entire table and whose start time defaults to now.
 *
 *  Zero npm dependencies. MCP JSON-RPC 2.0 over newline-delimited stdio.
 * ==========================================================================*/

'use strict';

const fs     = require('fs');
const path   = require('path');
const http   = require('http');
const crypto = require('crypto');
const { spawn } = require('child_process');

/* ---------------------------------------------------------------- config -- */

const COWORK_ROOT = 'C:\\Users\\YOURUSER\\Documents\\COPILOT_COWORK';
const BRIDGE_DIR  = path.join(COWORK_ROOT, 'Startup', 'FlowBridge');
const CONFIG_PATH = path.join(BRIDGE_DIR, 'flow-bridge.config.json');
const AUDIT_LOG   = path.join(COWORK_ROOT, 'CommandJobs', 'Logs', 'flow-bridge-audit.log');

const SERVER_NAME      = 'cowork-power-automate';
const SERVER_VERSION   = '0.5.0';
const DEFAULT_PROTOCOL = '2025-06-18';

const API_PATH   = '/api/data/v9.2';
const CAT_MODERN = 5;          // workflow.category 5 = Modern Flow
const SIGNIN_WAIT_MS = 150000;

/* The Flow service - a SEPARATE audience on a DIFFERENT host from Dataverse.
 * FLOW_RESOURCE is the token audience identifier and does NOT resolve in DNS.
 * FLOW_API_HOST is what you actually call. Confusing the two cost a day. */
const FLOW_RESOURCE    = 'https://service.flow.microsoft.com';
const FLOW_API_HOST    = 'https://api.flow.microsoft.com';
const FLOW_API_VERSION = '2016-11-01';

/* PowerApps is a THIRD audience. Connection INSTANCES (the authorised
 * accounts) live here; api.flow.microsoft.com serves the connector CATALOG
 * but 404s on /connections. Measured 2026-09-02.
 *
 * NO EXTRA SIGN-IN IS NEEDED. Measured 2026-09-02: a refresh token cached for
 * ANY of these resources exchanges cleanly for the others - the Dataverse org
 * URL's token produced both a service.powerapps.com and a
 * service.flow.microsoft.com access token. AAD v2 refresh tokens are not
 * resource-bound. getToken still caches per resource, so the first call for a
 * new audience simply refreshes rather than prompting. */
const PA_RESOURCE = 'https://service.powerapps.com/';
const PA_API_HOST = 'https://api.powerapps.com';

const DEFAULTS = {
  auth_strategy: 'none',        // none | interactive
  tenant_id: '',
  client_id: '',
  token_cache_file: '',         // path OUTSIDE the repo; empty disables caching
  read_only: true,
  allow_delete: false,
  allowed_environments: [],     // [{ id, name, org_url }]
  allow_prod: []
};

function loadConfig() {
  let cfg = Object.assign({}, DEFAULTS);
  try {
    const parsed = JSON.parse(fs.readFileSync(CONFIG_PATH, 'utf8'));
    for (const k of Object.keys(DEFAULTS)) {
      if (Object.prototype.hasOwnProperty.call(parsed, k)) cfg[k] = parsed[k];
    }
    cfg._loaded = true;
  } catch (e) {
    cfg._loaded = false;
    cfg._load_error = e.code === 'ENOENT' ? 'config file not present' : e.message;
  }
  return cfg;
}

/* ----------------------------------------------------------------- audit -- */

function audit(entry) {
  const line = JSON.stringify(Object.assign({ ts: new Date().toISOString() }, entry)) + '\n';
  try {
    fs.mkdirSync(path.dirname(AUDIT_LOG), { recursive: true });
    fs.appendFileSync(AUDIT_LOG, line, 'utf8');
  } catch (_) { /* auditing must never crash the bridge */ }
}

/* ------------------------------------------------------------ guardrails -- */

class Refusal extends Error {
  constructor(reason) { super(reason); this.reason = reason; }
}

/* Returns the matched allowlist ENTRY, because the org_url lives on it and
 * every Dataverse call needs it. A bare boolean was enough in v0.1.0 when the
 * host was global; it is not enough now. */
function requireEnvironment(cfg, envId) {
  if (!envId || typeof envId !== 'string')
    throw new Refusal('environment_id is required and must be a string.');

  const allowed = Array.isArray(cfg.allowed_environments) ? cfg.allowed_environments : [];
  if (allowed.length === 0)
    throw new Refusal(
      'no environments are allowlisted. This bridge refuses every environment until ' +
      'allowed_environments in flow-bridge.config.json names one explicitly.');

  const hit = allowed.find(e => (typeof e === 'string' ? e : e && e.id) === envId);
  if (!hit) throw new Refusal(`environment ${envId} is not in allowed_environments.`);

  const label = (typeof hit === 'string') ? '' : String(hit.name || '');

  /* Production detection is BELT AND BRACES, and the belt alone is not enough.
   * The v0.2.0 check was name-only, and "ProdCRM" is a production CRM whose name
   * contains no "prod" - it would have passed as non-production and been writable.
   * An explicit per-environment `production: true` flag now takes precedence, and
   * the name heuristic is kept as a backstop for entries nobody has flagged. */
  const flaggedProd = (typeof hit === 'object' && hit.production === true);
  const namedProd   = /prod/i.test(label);
  if ((flaggedProd || namedProd) && !(cfg.allow_prod || []).includes(envId))
    throw new Refusal(
      `environment ${envId} ("${label}") is ${flaggedProd ? 'flagged as production' : 'named like production'} ` +
      'and is not listed in allow_prod. Production flows are refused by default.');

  const orgUrl = (typeof hit === 'string') ? '' : String(hit.org_url || '');
  if (!orgUrl)
    throw new Refusal(
      `environment ${envId} has no org_url in allowed_environments. The Dataverse Web API ` +
      'is addressed by organization URL (e.g. https://orgXXXXXXXX.crm.dynamics.com), not by ' +
      'environment id alone.');

  /* An environment may pin itself read-only even when the bridge is globally
   * writable. It can only ever be MORE restrictive, never less - a per-entry
   * false cannot re-open a bridge that is globally read_only. */
  const envReadOnly = (typeof hit === 'object' && hit.read_only === true);

  /* flow_env_id MUST be carried through. This function returns a NEW object
   * rather than the config entry, so any field not named here is silently
   * dropped - which is exactly how the Flow service ended up being called with
   * the bare guid and answering 403 EnvironmentAccessDenied, measured
   * 2026-09-02. Add a field here whenever the config gains one. */
  const flowEnv = (typeof hit === 'object' && hit.flow_env_id) ? String(hit.flow_env_id) : envId;

  return {
    id: envId,
    name: label,
    org_url: orgUrl.replace(/\/+$/, ''),
    read_only: envReadOnly,
    flow_env_id: flowEnv
  };
}

function requireWritable(cfg, op, env) {
  if (cfg.read_only)
    throw new Refusal(`${op} refused: the bridge is in read_only mode. ` +
                      'Set read_only to false in flow-bridge.config.json to allow writes.');
  if (env && env.read_only)
    throw new Refusal(
      `${op} refused: environment "${env.name || env.id}" is pinned read_only in ` +
      'allowed_environments, even though the bridge itself allows writes. Remove that ' +
      'entry\'s read_only flag to permit writes there.');
}

function requireDeleteAllowed(cfg) {
  if (!cfg.allow_delete)
    throw new Refusal('delete_flow refused: allow_delete is false. ' +
                      'Deleting a flow is not recoverable through this bridge.');
}

/* ------------------------------------------------------------------ auth -- */
/* Interactive authorization code + PKCE on a loopback redirect.
 * Deliberately NOT device code: that is the grant type Conditional Access
 * blocks in this tenant. Deliberately NOT client_credentials: that needs an
 * app registration Jordan cannot create and an admin step he cannot perform. */

function b64url(buf) {
  return buf.toString('base64').replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
}

function readCache(cfg) {
  if (!cfg.token_cache_file) return null;
  try { return JSON.parse(fs.readFileSync(cfg.token_cache_file, 'utf8')); }
  catch (_) { return null; }
}

function writeCache(cfg, resource, refreshToken) {
  if (!cfg.token_cache_file || !refreshToken) return;
  let all = readCache(cfg) || {};
  all[resource] = { refresh_token: refreshToken, saved: new Date().toISOString() };
  try {
    fs.mkdirSync(path.dirname(cfg.token_cache_file), { recursive: true });
    fs.writeFileSync(cfg.token_cache_file, JSON.stringify(all, null, 2), { encoding: 'utf8', mode: 0o600 });
  } catch (_) { /* a cache failure must not break the call that just succeeded */ }
}

async function tokenRequest(cfg, params) {
  const url = 'https://login.microsoftonline.com/' + cfg.tenant_id + '/oauth2/v2.0/token';
  const r = await fetch(url, {
    method:  'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body:    new URLSearchParams(params)
  });
  const j = await r.json().catch(() => ({}));
  if (!r.ok) {
    const e = new Error('token endpoint ' + r.status + ': ' + (j.error || '') + ' ' +
                        String(j.error_description || '').split('\r')[0]);
    e.status = r.status;
    throw e;
  }
  return j;
}

async function interactiveSignIn(cfg, scope) {
  const verifier  = b64url(crypto.randomBytes(32));
  const challenge = b64url(crypto.createHash('sha256').update(verifier).digest());
  const state     = b64url(crypto.randomBytes(16));

  const got = await new Promise((resolve, reject) => {
    let redirect = null, settled = false;
    const server = http.createServer((req, res) => {
      const u = new URL(req.url, 'http://localhost');
      res.writeHead(200, { 'Content-Type': 'text/html' });
      res.end('<html><body style="font-family:Segoe UI,sans-serif;padding:2rem">' +
              '<h3>Cowork has what it needs. You can close this tab.</h3></body></html>');
      if (settled) return;
      settled = true;
      try { server.close(); } catch (_) {}
      const err = u.searchParams.get('error');
      if (err) return reject(new Error(err + ': ' + (u.searchParams.get('error_description') || '')));
      if (u.searchParams.get('state') !== state) return reject(new Error('state mismatch'));
      const code = u.searchParams.get('code');
      if (!code) return reject(new Error('redirect carried no authorization code'));
      resolve({ code, redirect });
    });
    server.listen(0, '127.0.0.1', () => {
      redirect = 'http://localhost:' + server.address().port + '/';
      const auth = 'https://login.microsoftonline.com/' + cfg.tenant_id + '/oauth2/v2.0/authorize' +
        '?client_id=' + cfg.client_id +
        '&response_type=code&response_mode=query' +
        '&redirect_uri=' + encodeURIComponent(redirect) +
        '&scope=' + encodeURIComponent(scope + ' offline_access') +
        '&code_challenge=' + challenge + '&code_challenge_method=S256' +
        '&state=' + state;
      process.stderr.write('[cowork-power-automate] opening a browser for sign-in\n');
      try {
        spawn('rundll32.exe', ['url.dll,FileProtocolHandler', auth], { stdio: 'ignore', detached: true }).unref();
      } catch (_) { /* the URL is still printed to stderr below */ }
      process.stderr.write('[cowork-power-automate] ' + auth + '\n');
      setTimeout(() => {
        if (settled) return;
        settled = true;
        try { server.close(); } catch (_) {}
        reject(new Error('timed out waiting for sign-in'));
      }, SIGNIN_WAIT_MS);
    });
    server.on('error', e => { if (!settled) { settled = true; reject(e); } });
  });

  return tokenRequest(cfg, {
    client_id:     cfg.client_id,
    grant_type:    'authorization_code',
    code:          got.code,
    redirect_uri:  got.redirect,
    code_verifier: verifier,
    scope:         scope + ' offline_access'
  });
}

/* resource is EITHER an environment org URL (Dataverse) OR FLOW_RESOURCE.
 * The scope shape "<resource>/user_impersonation" and the per-resource cache
 * key are identical for both, so one function serves both audiences. */
async function getToken(cfg, resource) {
  /* Try the exact resource first, then ANY other cached refresh token: AAD v2
   * refresh tokens are not resource-bound, so a token cached for Dataverse can
   * mint one for the Flow service or PowerApps without a browser. Measured
   * 2026-09-02. This is what keeps a three-audience bridge to ONE sign-in. */
  if (cfg.auth_strategy === 'none')
    throw new Refusal(
      'auth_strategy is "none", so this bridge holds no credentials and every flow tool ' +
      'refuses. Set auth_strategy to "interactive" with tenant_id and client_id in ' +
      'flow-bridge.config.json.');

  if (cfg.auth_strategy !== 'interactive')
    throw new Refusal(
      `auth_strategy "${cfg.auth_strategy}" is not supported. Use "interactive". ` +
      'client_credentials needs an Entra app registration and a Power Platform admin ' +
      'step that are not available on this tenant; device_code is blocked by ' +
      'Conditional Access.');

  if (!cfg.tenant_id || !cfg.client_id)
    throw new Refusal('auth_strategy is "interactive" but tenant_id and/or client_id are empty.');

  const scope = resource + '/user_impersonation';

  const cached = readCache(cfg);
  const entry  = cached && cached[resource];
  if (entry && entry.refresh_token) {
    try {
      const j = await tokenRequest(cfg, {
        client_id:     cfg.client_id,
        grant_type:    'refresh_token',
        refresh_token: entry.refresh_token,
        scope:         scope + ' offline_access'
      });
      if (j.refresh_token) writeCache(cfg, resource, j.refresh_token);
      return j.access_token;
    } catch (e) {
      /* AADSTS530036 and friends mean the cached grant is poisoned. Fall through
       * to a fresh interactive sign-in rather than retrying a dead token. */
      process.stderr.write('[cowork-power-automate] cached refresh failed, signing in: ' + e.message + '\n');
    }
  }

  /* Before falling back to a browser, try every OTHER cached refresh token.
   * A cross-resource exchange is silent and usually succeeds. */
  if (cached) {
    for (const key of Object.keys(cached)) {
      if (key === resource) continue;
      const rt = cached[key] && cached[key].refresh_token;
      if (!rt) continue;
      try {
        const j = await tokenRequest(cfg, {
          client_id: cfg.client_id, grant_type: 'refresh_token',
          refresh_token: rt, scope: scope + ' offline_access'
        });
        if (j.access_token) {
          if (j.refresh_token) writeCache(cfg, resource, j.refresh_token);
          process.stderr.write('[cowork-power-automate] token for ' + resource +
                               ' obtained silently by cross-resource refresh\n');
          return j.access_token;
        }
      } catch (_) { /* try the next one */ }
    }
  }

  if (!cfg.token_cache_file) {
    process.stderr.write(
      '[cowork-power-automate] NOTE: token_cache_file is empty and this bridge runs ' +
      'stateless, so this sign-in cannot be reused by the next call.\n');
  }

  const j = await interactiveSignIn(cfg, scope);
  if (j.refresh_token) writeCache(cfg, resource, j.refresh_token);
  return j.access_token;
}

/* -------------------------------------------------------------- dataverse -- */

async function dataverse(cfg, env, method, url, body) {
  const token = await getToken(cfg, env.org_url);
  const headers = {
    'Authorization':    'Bearer ' + token,
    'Accept':           'application/json',
    'OData-MaxVersion': '4.0',
    'OData-Version':    '4.0'
  };
  if (body !== undefined) {
    headers['Content-Type'] = 'application/json';
    headers['Prefer'] = 'return=representation';
  }
  const r = await fetch(env.org_url + API_PATH + url, {
    method, headers, body: body === undefined ? undefined : JSON.stringify(body)
  });
  if (r.status === 404) return null;
  if (r.status === 204) return {};
  const text = await r.text();
  if (!r.ok) {
    let detail = text.slice(0, 500);
    try { detail = JSON.parse(text).error.message; } catch (_) {}
    const e = new Error(detail);
    e.status = r.status;
    throw e;
  }
  try { return JSON.parse(text); } catch (_) { return {}; }
}

/* clientdata is NOT the bare definition - Dataverse requires the full envelope
 * { "properties": { "connectionReferences": {}, "definition": {...} } }.
 * Measured 2026-09-02: passing a bare definition returns HTTP 400
 * "Flow clientdata is in invalid format ... Required property 'properties'
 * not found in JSON". The solution-import route wrapped it correctly, which is
 * why create worked there while this path was broken.
 *
 * Accepts either shape from the caller: a bare definition is wrapped, an
 * already-wrapped envelope is passed through unchanged. */
/* -------------------------------------------------------------- flow api -- */
/* Dataverse owns flow DEFINITIONS. The Flow service owns RUNS, TRIGGERS and
 * CONNECTIONS - none of which are visible in Dataverse (flowrun, flowsession,
 * processsession and workflowlog are all queryable and all empty).
 *
 * TRAP, measured 2026-09-02: the DEFAULT environment's id on this API is
 * "Default-<guid>", not the bare guid Dataverse uses. The bare guid returns
 * 403 EnvironmentAccessDenied, which reads exactly like a permissions wall
 * and is not one. Carry flow_env_id in config for any environment that differs.
 */

function flowEnvId(env) {
  return env.flow_env_id || env.id;
}

async function flowApi(cfg, env, method, urlPath, body) {
  const token = await getToken(cfg, FLOW_RESOURCE);
  const url = FLOW_API_HOST + urlPath +
              (urlPath.indexOf('?') >= 0 ? '&' : '?') + 'api-version=' + FLOW_API_VERSION;

  const init = {
    method,
    headers: { 'Authorization': 'Bearer ' + token, 'Accept': 'application/json' }
  };
  if (body !== undefined) {
    init.headers['Content-Type'] = 'application/json';
    init.body = JSON.stringify(body);
  }

  const r = await fetch(url, init);
  const text = await r.text();
  let j = null;
  try { j = text ? JSON.parse(text) : null; } catch (_) { j = null; }

  if (!r.ok) {
    const code = (j && j.error && j.error.code) || String(r.status);
    const msg  = (j && j.error && j.error.message) || String(text).slice(0, 300);
    const e = new Error('flow service ' + r.status + ' ' + code + ': ' + msg);
    e.status = r.status;
    throw e;
  }
  return { status: r.status, json: j };
}

function flowBase(env) {
  return '/providers/Microsoft.ProcessSimple/environments/' + flowEnvId(env);
}

async function powerAppsApi(cfg, env, urlPath) {
  const token = await getToken(cfg, PA_RESOURCE);
  const url = PA_API_HOST + urlPath +
              (urlPath.indexOf('?') >= 0 ? '&' : '?') + 'api-version=' + FLOW_API_VERSION;
  const r = await fetch(url, {
    headers: { 'Authorization': 'Bearer ' + token, 'Accept': 'application/json' }
  });
  const text = await r.text();
  let j = null;
  try { j = text ? JSON.parse(text) : null; } catch (_) {}
  if (!r.ok) {
    const e = new Error('powerapps ' + r.status + ': ' +
                        ((j && j.error && j.error.message) || String(text).slice(0, 200)));
    e.status = r.status;
    throw e;
  }
  return { status: r.status, json: j };
}

/* The Flow service and Dataverse use DIFFERENT ids for the SAME flow.
 * Measured 2026-09-02: "Todo - Get My Tasks" is ed05cae4-... in the Dataverse
 * workflow table and 22285442-... on the Flow service. Passing the Dataverse id
 * to a run tool returns 404 FlowNotFound, which looks like a missing flow and
 * is not one. So: try the id as given, and on 404 fall back to matching the
 * Dataverse display name against the Flow service inventory. */
async function resolveFlowServiceId(cfg, env, flowId) {
  try {
    await flowApi(cfg, env, 'GET', flowBase(env) + '/flows/' + flowId);
    return { id: flowId, resolved: false };
  } catch (e) {
    if (e.status !== 404) throw e;
  }

  let name = null;
  try {
    const row = await dataverse(cfg, env, 'GET', `/workflows(${flowId})?$select=name`);
    name = row && row.name;
  } catch (_) { /* not a Dataverse id either */ }

  if (!name) {
    throw new Refusal(
      `no flow ${flowId} on the Flow service, and it is not a Dataverse workflow id either. ` +
      'Use list_all_flows to get Flow-service ids.');
  }

  const inv = await flowApi(cfg, env, 'GET', flowBase(env) + '/flows?$top=250');
  const hit = ((inv.json && inv.json.value) || [])
    .find(f => f.properties && f.properties.displayName === name);

  if (!hit) {
    throw new Refusal(
      `flow "${name}" (Dataverse id ${flowId}) has no match on the Flow service, so its ` +
      'runs cannot be reached. It may be a solution flow that has never been activated.');
  }

  return { id: hit.name, resolved: true, matched_on: name };
}


/* =========================================================================
 *  v0.5.0 ADDITIONS
 *  Every endpoint below is marked with how it was established:
 *    MEASURED   - exercised against this tenant
 *    DOCUMENTED - Microsoft Learn reference
 *    PORTAL     - observed portal traffic / community reports, undocumented
 * ========================================================================= */

/* The Business Application Platform host. Admin and DLP surfaces live here,
 * NOT on api.flow.microsoft.com. Audience is the PowerApps one, which the
 * cache already holds - so no extra sign-in. PORTAL. */
const BAP_API_HOST = 'https://api.bap.microsoft.com';

async function bapApi(cfg, method, urlPath, body) {
  const token = await getToken(cfg, PA_RESOURCE);
  const url = BAP_API_HOST + urlPath +
              (urlPath.indexOf('?') >= 0 ? '&' : '?') + 'api-version=' + FLOW_API_VERSION;
  const init = {
    method,
    headers: { 'Authorization': 'Bearer ' + token, 'Accept': 'application/json' }
  };
  if (body !== undefined) {
    init.headers['Content-Type'] = 'application/json';
    init.body = JSON.stringify(body);
  }
  const r = await fetch(url, init);
  const text = await r.text();
  let j = null;
  try { j = text ? JSON.parse(text) : null; } catch (_) {}
  if (!r.ok) {
    const e = new Error('bap ' + r.status + ': ' +
                        ((j && j.error && j.error.message) || String(text).slice(0, 300)));
    e.status = r.status;
    throw e;
  }
  return { status: r.status, json: j };
}

/* Resubmit does NOT hang off /runs/{id}. It hangs off the TRIGGER:
 *   /flows/{id}/triggers/{trigger}/histories/{runId}/resubmit
 * A /runs/{id}/resubmit shape 404s. PORTAL. */
async function firstTriggerName(cfg, env, flowServiceId) {
  const t = await flowApi(cfg, env, 'GET',
                          flowBase(env) + '/flows/' + flowServiceId + '/triggers');
  const triggers = (t.json && t.json.value) || [];
  if (!triggers.length)
    throw new Refusal('this flow exposes no trigger, so a run cannot be resubmitted.');
  return triggers[0].name;
}

/* ------------------------------------------------------- child flows -- */
/* A child-flow call is an action of type "Workflow". The callee is named in
 * inputs.host - either a full id or a workflowReferenceName. Nothing in the
 * ecosystem surfaces this, and it is the relationship that makes a flow
 * estate hard to reason about. Pure local analysis: no extra call. */
function findChildFlowCalls(clientdata) {
  let cd;
  try { cd = JSON.parse(clientdata); } catch (_) { return { parse_error: true, calls: [] }; }
  const props = (cd && cd.properties) || cd || {};
  const def   = props.definition || {};
  const calls = [];

  (function walk(obj, path) {
    if (!obj || typeof obj !== 'object') return;
    for (const k of Object.keys(obj)) {
      const a = obj[k];
      if (!a || typeof a !== 'object') continue;
      const here = path.concat(k);
      if (a.type === 'Workflow') {
        const host = (a.inputs && a.inputs.host) || {};
        const wf   = host.workflow || {};
        calls.push({
          action: k,
          path: here.join(' > '),
          child_flow_id: wf.id ? String(wf.id).split('/').pop()
                              : (host.workflowReferenceName || null),
          trigger: host.triggerName || null
        });
      }
      if (a.actions) walk(a.actions, here);
      if (a.else && a.else.actions) walk(a.else.actions, here.concat('else'));
      if (a.cases) for (const c of Object.keys(a.cases)) {
        if (a.cases[c] && a.cases[c].actions) walk(a.cases[c].actions, here.concat('case:' + c));
      }
      if (a.default && a.default.actions) walk(a.default.actions, here.concat('default'));
    }
  })(def.actions || {}, []);

  return { calls };
}

/* --------------------------------------------- expression evaluator -- */
/* A real subset of the Workflow Definition Language, evaluated locally so a
 * caller can settle "what does this expression actually produce" without
 * running the flow. Unsupported functions raise by NAME rather than
 * returning a wrong answer quietly. 75 offline cases cover this. */

function wdlTokenize(s) {
  const toks = [];
  let i = 0;
  while (i < s.length) {
    const c = s[i];
    if (c === ' ' || c === '\t' || c === '\n' || c === '\r') { i++; continue; }
    if (c === "'") {
      let j = i + 1, out = '';
      let closed = false;
      while (j < s.length) {
        if (s[j] === "'") {
          if (s[j + 1] === "'") { out += "'"; j += 2; continue; }
          closed = true; break;
        }
        out += s[j]; j++;
      }
      if (!closed) throw new Error('unterminated string literal');
      toks.push({ t: 'str', v: out }); i = j + 1; continue;
    }
    if (/[0-9]/.test(c)) {
      let j = i;
      while (j < s.length && /[0-9.]/.test(s[j])) j++;
      const raw = s.slice(i, j);
      toks.push({ t: 'num', v: parseFloat(raw), float: raw.indexOf('.') >= 0 }); i = j; continue;
    }
    if (c === '-' && /[0-9]/.test(s[i + 1] || '')) {
      const prev = toks[toks.length - 1];
      if (!prev || prev.t === '(' || prev.t === ',' || prev.t === '[') {
        let j = i + 1;
        while (j < s.length && /[0-9.]/.test(s[j])) j++;
        const raw2 = s.slice(i, j);
        toks.push({ t: 'num', v: parseFloat(raw2), float: raw2.indexOf('.') >= 0 }); i = j; continue;
      }
    }
    if (/[A-Za-z_]/.test(c)) {
      let j = i;
      while (j < s.length && /[A-Za-z0-9_]/.test(s[j])) j++;
      toks.push({ t: 'id', v: s.slice(i, j) }); i = j; continue;
    }
    if (c === '?' && s[i + 1] === '.') { toks.push({ t: '?.' }); i += 2; continue; }
    if ('(),[].'.indexOf(c) >= 0) { toks.push({ t: c }); i++; continue; }
    throw new Error('unexpected character "' + c + '"');
  }
  return toks;
}

function wdlParse(toks) {
  let p = 0;
  const peek = () => toks[p];
  const next = () => toks[p++];
  function expect(t) {
    const x = next();
    if (!x || x.t !== t) throw new Error('expected "' + t + '"');
    return x;
  }
  function primary() {
    const tk = next();
    if (!tk) throw new Error('unexpected end of expression');
    if (tk.t === 'str' || tk.t === 'num') return { k: 'lit', v: tk.v, float: !!tk.float };
    if (tk.t === '(') { const e = expr(); expect(')'); return e; }
    if (tk.t === 'id') {
      const lower = tk.v.toLowerCase();
      if (lower === 'true')  return { k: 'lit', v: true };
      if (lower === 'false') return { k: 'lit', v: false };
      if (lower === 'null')  return { k: 'lit', v: null };
      if (peek() && peek().t === '(') {
        next();
        const args = [];
        if (peek() && peek().t !== ')') {
          for (;;) {
            args.push(expr());
            if (peek() && peek().t === ',') { next(); continue; }
            break;
          }
        }
        expect(')');
        return { k: 'call', name: tk.v, args };
      }
      throw new Error('bare identifier "' + tk.v + '" is not valid - did you mean ' + tk.v + '()?');
    }
    throw new Error('unexpected token');
  }
  function expr() {
    let node = primary();
    for (;;) {
      const tk = peek();
      if (!tk) break;
      if (tk.t === '.' || tk.t === '?.') {
        const optional = tk.t === '?.';
        next();
        const id = next();
        if (!id || id.t !== 'id') throw new Error('expected a property name after "."');
        node = { k: 'prop', obj: node, name: id.v, optional };
        continue;
      }
      if (tk.t === '[') { next(); const ix = expr(); expect(']'); node = { k: 'index', obj: node, index: ix }; continue; }
      break;
    }
    return node;
  }
  const e = expr();
  if (p < toks.length) throw new Error('trailing tokens after a complete expression');
  return e;
}

function wdlNum(v, fn) {
  const n = typeof v === 'number' ? v : parseFloat(v);
  if (typeof n !== 'number' || isNaN(n)) throw new Error(fn + ' expects a number');
  return n;
}

function wdlCall(name, a, ctx, floatHint) {
  const fn = name.toLowerCase();
  const need = (n) => { if (a.length < n) throw new Error(name + ' expects at least ' + n + ' argument(s)'); };
  switch (fn) {
    /* refs */
    case 'variables':      need(1); return (ctx.variables   || {})[a[0]];
    case 'parameters':     need(1); return (ctx.parameters  || {})[a[0]];
    case 'outputs':        need(1); return (ctx.outputs     || {})[a[0]];
    case 'body':           need(1); return (ctx.body        || {})[a[0]];
    case 'triggerbody':    return ctx.triggerBody    !== undefined ? ctx.triggerBody    : {};
    case 'triggeroutputs': return ctx.triggerOutputs !== undefined ? ctx.triggerOutputs : {};
    case 'item':           return ctx.item;
    case 'items':          need(1); return (ctx.items || {})[a[0]];
    /* string */
    case 'concat':      return a.map(x => x === null || x === undefined ? '' : String(x)).join('');
    case 'substring':   need(2); return String(a[0]).substr(wdlNum(a[1], name), a.length > 2 ? wdlNum(a[2], name) : undefined);
    case 'replace':     need(3); return String(a[0]).split(String(a[1])).join(String(a[2]));
    case 'tolower':     need(1); return String(a[0]).toLowerCase();
    case 'toupper':     need(1); return String(a[0]).toUpperCase();
    case 'trim':        need(1); return String(a[0]).trim();
    case 'indexof':     need(2); return String(a[0]).indexOf(String(a[1]));
    case 'lastindexof': need(2); return String(a[0]).lastIndexOf(String(a[1]));
    case 'startswith':  need(2); return String(a[0]).indexOf(String(a[1])) === 0;
    case 'endswith':    need(2); return String(a[0]).slice(-String(a[1]).length) === String(a[1]);
    case 'split':       need(2); return String(a[0]).split(String(a[1]));
    case 'guid':        return '00000000-0000-0000-0000-000000000000';
    /* collection */
    case 'length':  need(1); return Array.isArray(a[0]) ? a[0].length : String(a[0]).length;
    case 'first':   need(1); return Array.isArray(a[0]) ? (a[0].length ? a[0][0] : null) : String(a[0]).charAt(0);
    case 'last':    need(1); return Array.isArray(a[0]) ? (a[0].length ? a[0][a[0].length - 1] : null) : String(a[0]).slice(-1);
    case 'empty':   need(1);
      if (a[0] === null || a[0] === undefined) return true;
      if (Array.isArray(a[0])) return a[0].length === 0;
      if (typeof a[0] === 'object') return Object.keys(a[0]).length === 0;
      return String(a[0]).length === 0;
    case 'contains': need(2);
      if (Array.isArray(a[0])) return a[0].indexOf(a[1]) >= 0;
      if (a[0] && typeof a[0] === 'object') return Object.prototype.hasOwnProperty.call(a[0], a[1]);
      return String(a[0]).indexOf(String(a[1])) >= 0;
    case 'join':        need(2); return (a[0] || []).map(String).join(String(a[1]));
    case 'createarray': return a.slice();
    case 'skip':        need(2); return (a[0] || []).slice(wdlNum(a[1], name));
    case 'take':        need(2); return (a[0] || []).slice(0, wdlNum(a[1], name));
    case 'union':       need(2); return Array.from(new Set([].concat(a[0] || [], a[1] || [])));
    case 'intersection':need(2); return (a[0] || []).filter(x => (a[1] || []).indexOf(x) >= 0);
    /* logic */
    case 'equals':          need(2); return JSON.stringify(a[0]) === JSON.stringify(a[1]);
    case 'greater':         need(2); return a[0] > a[1];
    case 'greaterorequals': need(2); return a[0] >= a[1];
    case 'less':            need(2); return a[0] < a[1];
    case 'lessorequals':    need(2); return a[0] <= a[1];
    case 'and':             need(2); return a.every(Boolean);
    case 'or':              need(2); return a.some(Boolean);
    case 'not':             need(1); return !a[0];
    case 'if':              need(3); return a[0] ? a[1] : a[2];
    case 'coalesce':        return a.find(x => x !== null && x !== undefined);
    /* math */
    case 'add': need(2); return wdlNum(a[0], name) + wdlNum(a[1], name);
    case 'sub': need(2); return wdlNum(a[0], name) - wdlNum(a[1], name);
    case 'mul': need(2); return wdlNum(a[0], name) * wdlNum(a[1], name);
    case 'div': need(2); {
      const d = wdlNum(a[1], name);
      if (d === 0) throw new Error('div by zero');
      const n = wdlNum(a[0], name);
      /* WDL does INTEGER division when both operands are integers. JavaScript
       * collapses 7.0 to 7, so the literal's written form is carried through
       * as floatHint - otherwise div(7.0,2) would wrongly return 3. */
      const wroteFloat = !!(floatHint && (floatHint[0] || floatHint[1]));
      const isInt = Number.isInteger(n) && Number.isInteger(d) && !wroteFloat;
      return isInt ? Math.trunc(n / d) : (n / d);
    }
    case 'mod': need(2); return wdlNum(a[0], name) % wdlNum(a[1], name);
    case 'min': return Math.min.apply(null, (Array.isArray(a[0]) ? a[0] : a).map(x => wdlNum(x, name)));
    case 'max': return Math.max.apply(null, (Array.isArray(a[0]) ? a[0] : a).map(x => wdlNum(x, name)));
    case 'range': need(2); {
      const st = wdlNum(a[0], name), ct = wdlNum(a[1], name), out = [];
      for (let i = 0; i < ct; i++) out.push(st + i);
      return out;
    }
    /* conversion */
    case 'int':    need(1); { const n = parseInt(a[0], 10); if (isNaN(n)) throw new Error('int() cannot parse'); return n; }
    case 'float':  need(1); return wdlNum(a[0], name);
    case 'string': need(1); return a[0] === null || a[0] === undefined ? ''
                          : (typeof a[0] === 'object' ? JSON.stringify(a[0]) : String(a[0]));
    case 'bool':   need(1); return a[0] === true || String(a[0]).toLowerCase() === 'true';
    case 'json':   need(1); return typeof a[0] === 'string' ? JSON.parse(a[0]) : a[0];
    case 'array':  need(1); return Array.isArray(a[0]) ? a[0] : [a[0]];
    case 'base64': need(1); return Buffer.from(String(a[0]), 'utf8').toString('base64');
    case 'base64tostring': need(1); return Buffer.from(String(a[0]), 'base64').toString('utf8');
    default:
      throw new Error('unsupported function "' + name + '". This evaluator covers a subset; ' +
                      'date and workflow-runtime functions are deliberately excluded because ' +
                      'their value depends on the running flow.');
  }
}

function wdlEval(node, ctx) {
  switch (node.k) {
    case 'lit': return node.v;
    case 'prop': {
      const o = wdlEval(node.obj, ctx);
      if (o === null || o === undefined) {
        if (node.optional) return null;
        throw new Error('cannot read "' + node.name + '" of a null value - use ?. to allow it');
      }
      const pv = o[node.name];
      return pv === undefined ? null : pv;
    }
    case 'index': {
      const o = wdlEval(node.obj, ctx);
      if (o === null || o === undefined) return null;
      const iv = o[wdlEval(node.index, ctx)];
      return iv === undefined ? null : iv;
    }
    case 'call': return wdlCall(node.name, node.args.map(x => wdlEval(x, ctx)), ctx,
                                node.args.map(x => x.k === 'lit' && x.float === true));
    default: throw new Error('cannot evaluate node');
  }
}

function evaluateWdl(raw, context) {
  const ctx = context || {};
  const s = String(raw);

  const runOne = (src) => wdlEval(wdlParse(wdlTokenize(src)), ctx);

  /* Find the '}' that closes the '{' at index `open`, ignoring braces inside
   * string literals. Needed because "@{a()}/@{b()}" also ENDS in '}' and must
   * NOT be treated as one whole-value expression. */
  const closeOf = (str, open) => {
    let depth = 0, inStr = false;
    for (let j = open; j < str.length; j++) {
      const c = str[j];
      if (c === "'") { inStr = !inStr; continue; }
      if (inStr) continue;
      if (c === '{') depth++;
      else if (c === '}') { depth--; if (depth === 0) return j; }
    }
    return -1;
  };

  /* whole-value form: @{ ... } or @func(...) */
  if (s.slice(0, 2) === '@{') {
    const close = closeOf(s, 1);
    if (close === -1) throw new Error('unbalanced @{ } in the expression');
    if (close === s.length - 1) return runOne(s.slice(2, -1));
  }
  if (s.charAt(0) === '@' && s.charAt(1) !== '@' && s.indexOf('@{') !== 0) return runOne(s.slice(1));

  /* interpolated form: text with embedded @{ ... } */
  if (s.indexOf('@{') >= 0) {
    let out = '', i = 0;
    while (i < s.length) {
      const start = s.indexOf('@{', i);
      if (start < 0) { out += s.slice(i); break; }
      out += s.slice(i, start);
      const end = closeOf(s, start + 1);
      if (end < 0) throw new Error('unbalanced @{ } in the expression');
      const v = runOne(s.slice(start + 2, end));
      out += (v === null || v === undefined) ? ''
           : (typeof v === 'object' ? JSON.stringify(v) : String(v));
      i = end + 1;
    }
    return out;
  }
  return s;
}

function shapeRun(run) {
  const p = (run && run.properties) || {};
  return {
    run_id: run.name,
    status: p.status || null,
    start_time: p.startTime || null,
    end_time: p.endTime || null,
    trigger: (p.trigger && p.trigger.name) || null,
    trigger_status: (p.trigger && p.trigger.status) || null,
    error: p.error ? { code: p.error.code, message: p.error.message } : null
  };
}

function toClientData(definition, connectionReferences) {
  /* An already-wrapped envelope is passed through - but schemaVersion is
   * REQUIRED at the top level and a caller who wraps by hand routinely omits
   * it. Measured 2026-09-02: HTTP 400 "Required property 'schemaVersion' not
   * found in JSON". The unwrapped branch below always set it, so only the
   * pass-through path could produce that error. Fill it rather than refuse. */
  if (definition && typeof definition === 'object' && definition.properties &&
      typeof definition.properties === 'object') {
    const env = Object.assign({}, definition);
    if (!env.schemaVersion) env.schemaVersion = '1.0.0.0';
    if (env.properties && !env.properties.connectionReferences) {
      env.properties = Object.assign({}, env.properties,
                                     { connectionReferences: connectionReferences || {} });
    }
    return JSON.stringify(env);
  }
  return JSON.stringify({
    properties: {
      connectionReferences: connectionReferences || {},
      definition: definition
    },
    schemaVersion: '1.0.0.0'
  });
}

const SELECT_LIST = '$select=workflowid,name,statecode,statuscode,modifiedon,category';
const SELECT_ONE  = '$select=workflowid,name,description,statecode,statuscode,modifiedon,category,type,clientdata';

/* Pull the useful shape out of a flow definition: what starts it, how big it is,
 * and which connectors it binds. All of this is already inside clientdata, so it
 * costs no extra call - it is the inventory answer the portal makes you click
 * through one flow at a time. */
function analyzeDefinition(clientdata) {
  let cd;
  try { cd = JSON.parse(clientdata); } catch (_) { return { parse_error: true }; }
  const props = (cd && cd.properties) || cd || {};
  const def   = props.definition || {};
  const triggers = def.triggers || {};
  const actions  = def.actions  || {};

  const triggerNames = Object.keys(triggers);
  const t0 = triggerNames.length ? triggers[triggerNames[0]] : null;

  /* Walk nested scopes - conditions, foreach, until and switch cases all carry
   * their own actions object, so a flat count badly understates a real flow. */
  const types = {};
  let total = 0, depth = 0;
  (function walk(obj, d) {
    if (!obj || typeof obj !== 'object') return;
    if (d > depth) depth = d;
    for (const k of Object.keys(obj)) {
      const a = obj[k];
      if (!a || typeof a !== 'object') continue;
      if (a.type) { total++; types[a.type] = (types[a.type] || 0) + 1; }
      if (a.actions)    walk(a.actions, d + 1);
      if (a.else && a.else.actions) walk(a.else.actions, d + 1);
      if (a.cases) for (const c of Object.keys(a.cases)) {
        if (a.cases[c] && a.cases[c].actions) walk(a.cases[c].actions, d + 1);
      }
      if (a.default && a.default.actions) walk(a.default.actions, d + 1);
    }
  })(actions, 1);

  const refs = props.connectionReferences || {};
  const connectors = [];
  for (const k of Object.keys(refs)) {
    const r = refs[k] || {};
    const api = (r.api && (r.api.name || r.api.id)) || r.connectorId || '';
    connectors.push({
      reference: k,
      connector: String(api).split('/').pop() || String(api),
      connection_name: r.connectionName || (r.connection && r.connection.name) || null
    });
  }

  return {
    trigger_kind: t0 ? (t0.kind || t0.type || 'unknown') : 'none',
    trigger_type: t0 ? (t0.type || 'unknown') : 'none',
    trigger_name: triggerNames[0] || null,
    action_count: total,
    max_depth: depth,
    action_types: types,
    connector_count: connectors.length,
    connectors: connectors
  };
}

function shape(row) {
  if (!row) return null;
  return {
    flow_id:      row.workflowid,
    display_name: row.name,
    state:        row.statecode === 1 ? 'started' : 'stopped',
    statecode:    row.statecode,
    statuscode:   row.statuscode,
    modified:     row.modifiedon
  };
}

/* ----------------------------------------------------------------- tools -- */

const TOOLS = [
  {
    name: 'run_flow',
    description:
      'Trigger a cloud flow on demand and return the run reference. This has REAL SIDE ' +
      'EFFECTS - the flow does whatever it does - so it is gated exactly like a write: ' +
      'refused while read_only is true, refused on production environments not in ' +
      'allow_prod, and audited. Works on manually-triggerable flows; a flow whose trigger ' +
      'is a schedule or an external event cannot be started this way.',
    inputSchema: {
      type: 'object',
      properties: {
        environment_id: { type: 'string' },
        flow_id: { type: 'string' },
        trigger_name: { type: 'string', description: 'Optional. Defaults to the flow\'s first trigger.' },
        inputs: { type: 'object', description: 'Optional trigger inputs, for a flow that accepts them.' }
      },
      required: ['environment_id', 'flow_id'],
      additionalProperties: false
    }
  },
  {
    name: 'get_run_history',
    description:
      'Run history for a flow: status, start and end time, trigger and any error. Read-only. ' +
      'This comes from the Flow service - it is NOT in Dataverse, where the run tables are ' +
      'always empty.',
    inputSchema: {
      type: 'object',
      properties: {
        environment_id: { type: 'string' },
        flow_id: { type: 'string' },
        top: { type: 'number', description: 'Max runs, default 20' }
      },
      required: ['environment_id', 'flow_id'],
      additionalProperties: false
    }
  },
  {
    name: 'get_run_actions',
    description:
      'Per-action detail for ONE run - each step, its status, timing and error. This is the ' +
      'debugging view: it answers which step failed and why. Read-only.',
    inputSchema: {
      type: 'object',
      properties: {
        environment_id: { type: 'string' },
        flow_id: { type: 'string' },
        run_id: { type: 'string', description: 'The run_id from get_run_history' }
      },
      required: ['environment_id', 'flow_id', 'run_id'],
      additionalProperties: false
    }
  },
  {
    name: 'cancel_run',
    description:
      'Cancel a run that is still in flight. Gated as a write and audited.',
    inputSchema: {
      type: 'object',
      properties: {
        environment_id: { type: 'string' },
        flow_id: { type: 'string' },
        run_id: { type: 'string' }
      },
      required: ['environment_id', 'flow_id', 'run_id'],
      additionalProperties: false
    }
  },
  {
    name: 'list_connections',
    description:
      'List the connections that ALREADY EXIST in an environment - the authorised accounts a ' +
      'flow can actually run as. Read this BEFORE authoring: a flow referencing a connector ' +
      'with no connection is created successfully but cannot run.',
    inputSchema: {
      type: 'object',
      properties: {
        environment_id: { type: 'string' }
      },
      required: ['environment_id'],
      additionalProperties: false
    }
  },
  {
    name: 'find_connector',
    description:
      'Search the connector CATALOG - every connector available in the environment (about ' +
      '1300 of them), which is what you need to author a flow: the connector id to put in a ' +
      'definition. Different from list_connections, which shows what is already authorised. ' +
      'Always pass search; the unfiltered catalog is far too large to read.',
    inputSchema: {
      type: 'object',
      properties: {
        environment_id: { type: 'string' },
        search: { type: 'string', description: 'Case-insensitive match on the connector name, e.g. "sharepoint"' },
        top: { type: 'number', description: 'Max matches, default 25' }
      },
      required: ['environment_id', 'search'],
      additionalProperties: false
    }
  },
  {
    name: 'list_all_flows',
    description:
      'Inventory from the Flow service rather than Dataverse. This sees personal "My flows" ' +
      'that list_flows cannot - measured 5 flows here against Dataverse\'s 3. Read-only.',
    inputSchema: {
      type: 'object',
      properties: {
        environment_id: { type: 'string' },
        top: { type: 'number', description: 'Max rows, default 50' }
      },
      required: ['environment_id'],
      additionalProperties: false
    }
  },
  {
    name: 'list_flows',
    description:
      'List cloud flows in an allowlisted environment, newest first. Reads the Dataverse ' +
      'workflow table (category 5 = Modern Flow). Read-only. Note that only SOLUTION-AWARE ' +
      'flows are visible this way; personal "My flows" are not manageable by code.',
    inputSchema: {
      type: 'object',
      properties: {
        environment_id: { type: 'string' },
        top: { type: 'number', description: 'Max rows, default 50' }
      },
      required: ['environment_id'],
      additionalProperties: false
    }
  },
  {
    name: 'get_flow',
    description: 'Get one cloud flow including its definition (clientdata). Read-only.',
    inputSchema: {
      type: 'object',
      properties: {
        environment_id: { type: 'string' },
        flow_id: { type: 'string' }
      },
      required: ['environment_id', 'flow_id'],
      additionalProperties: false
    }
  },
  {
    name: 'create_flow',
    description:
      'Create a cloud flow from a definition. Refused while read_only is true. The new flow ' +
      'is created in the Draft state and must be started before it will run.',
    inputSchema: {
      type: 'object',
      properties: {
        environment_id: { type: 'string' },
        display_name: { type: 'string' },
        definition: { type: 'object', description: 'The flow definition object (clientdata)' },
        description: { type: 'string' }
      },
      required: ['environment_id', 'display_name', 'definition'],
      additionalProperties: false
    }
  },
  {
    name: 'update_flow',
    description:
      'Update a cloud flow\'s display name, description, definition, or any combination. ' +
      'Refused while read_only is true.',
    inputSchema: {
      type: 'object',
      properties: {
        environment_id: { type: 'string' },
        flow_id: { type: 'string' },
        display_name: { type: 'string' },
        definition: { type: 'object' },
        description: { type: 'string' }
      },
      required: ['environment_id', 'flow_id'],
      additionalProperties: false
    }
  },
  {
    name: 'delete_flow',
    description:
      'Delete a cloud flow. Requires allow_delete AND confirm_name matching the flow\'s ' +
      'current display name exactly. Deletes exactly one row addressed by id. Not ' +
      'recoverable through this bridge.',
    inputSchema: {
      type: 'object',
      properties: {
        environment_id: { type: 'string' },
        flow_id: { type: 'string' },
        confirm_name: { type: 'string', description: 'Must equal the flow\'s current display name' }
      },
      required: ['environment_id', 'flow_id', 'confirm_name'],
      additionalProperties: false
    }
  },
  {
    name: 'set_flow_state',
    description:
      'Start (enable) or stop (disable) a cloud flow by setting its statecode. ' +
      'Refused while read_only is true.',
    inputSchema: {
      type: 'object',
      properties: {
        environment_id: { type: 'string' },
        flow_id: { type: 'string' },
        state: { type: 'string', enum: ['started', 'stopped'] }
      },
      required: ['environment_id', 'flow_id', 'state'],
      additionalProperties: false
    }
  },
  {
    name: 'analyze_flow',
    description:
      'Describe a flow without opening the portal: trigger kind, action count including ' +
      'nested scopes, action types, nesting depth, and every connector it binds. ' +
      'Read-only, one call.',
    inputSchema: {
      type: 'object',
      properties: {
        environment_id: { type: 'string' },
        flow_id: { type: 'string' }
      },
      required: ['environment_id', 'flow_id'],
      additionalProperties: false
    }
  },
  {
    name: 'find_flows_using_connector',
    description:
      'Find every cloud flow in an environment that binds a given connector, e.g. ' +
      '"sharepointonline", "sql", "office365". Answers "what breaks if this connection ' +
      'dies". Omit the filter to get a full connector-to-flow index. Read-only; reads ' +
      'each flow definition, so it is slower than list_flows.',
    inputSchema: {
      type: 'object',
      properties: {
        environment_id: { type: 'string' },
        connector: { type: 'string', description: 'Case-insensitive substring; omit for a full index' },
        top: { type: 'number', description: 'Max flows to scan, default 100' }
      },
      required: ['environment_id'],
      additionalProperties: false
    }
  },
  {
    name: 'list_environments',
    description:
      'List the environments this bridge is allowed to reach and what is permitted in ' +
      'each - production status and whether writes are pinned off. Reads config only: ' +
      'no network call, no sign-in.',
    inputSchema: { type: 'object', properties: {}, additionalProperties: false }
  },
  {
    name: 'bridge_status',
    description:
      'Report what this bridge is currently permitted to do: auth strategy, whether a token ' +
      'cache is configured, read_only, allow_delete, and the allowlisted environments. ' +
      'Always available, never mutates, never signs in.',
    inputSchema: { type: 'object', properties: {}, additionalProperties: false }
  }
  ,
  /* ------------------------------------------------ v0.5.0: runs -- */
  {
    name: 'resubmit_run',
    description:
      'Re-run a PAST run with its ORIGINAL trigger inputs - the "resubmit" the portal offers on ' +
      'a failed run. This has REAL SIDE EFFECTS and is gated as a write. The endpoint hangs off ' +
      'the trigger history, not off /runs, so the trigger is resolved first when not supplied.',
    inputSchema: {
      type: 'object',
      properties: {
        environment_id: { type: 'string' },
        flow_id: { type: 'string' },
        run_id: { type: 'string' },
        trigger_name: { type: 'string', description: 'Defaults to the flow first trigger' }
      },
      required: ['environment_id', 'flow_id', 'run_id'],
      additionalProperties: false
    }
  },
  /* ---------------------------------------------- v0.5.0: owners -- */
  {
    name: 'list_flow_owners',
    description:
      'Who owns or can edit a flow. Read-only. Answers "whose flow is this" and "who else can ' +
      'change it" without opening the portal.',
    inputSchema: {
      type: 'object',
      properties: { environment_id: { type: 'string' }, flow_id: { type: 'string' } },
      required: ['environment_id', 'flow_id'],
      additionalProperties: false
    }
  },
  {
    name: 'add_flow_owner',
    description:
      'Grant a user co-ownership of a flow. Gated as a write. The user is addressed by Entra ' +
      'object id, not by email alone.',
    inputSchema: {
      type: 'object',
      properties: {
        environment_id: { type: 'string' },
        flow_id: { type: 'string' },
        principal_id: { type: 'string', description: 'Entra object id of the user' },
        principal_email: { type: 'string' },
        principal_display_name: { type: 'string' },
        role: { type: 'string', enum: ['CanEdit', 'CanView'], description: 'Default CanEdit' }
      },
      required: ['environment_id', 'flow_id', 'principal_id'],
      additionalProperties: false
    }
  },
  {
    name: 'remove_flow_owner',
    description:
      'Revoke a user access to a flow. Gated as a write. Refuses to remove the last remaining ' +
      'owner, which would orphan the flow.',
    inputSchema: {
      type: 'object',
      properties: {
        environment_id: { type: 'string' },
        flow_id: { type: 'string' },
        principal_id: { type: 'string' }
      },
      required: ['environment_id', 'flow_id', 'principal_id'],
      additionalProperties: false
    }
  },
  /* ------------------------------------------- v0.5.0: solution ALM -- */
  {
    name: 'list_solutions',
    description:
      'Solutions in the environment - unique name, version, and whether managed. Read-only. ' +
      'The unique name is what export_solution and add_flow_to_solution take.',
    inputSchema: {
      type: 'object',
      properties: {
        environment_id: { type: 'string' },
        include_managed: { type: 'boolean', description: 'Default false - unmanaged only' }
      },
      required: ['environment_id'],
      additionalProperties: false
    }
  },
  {
    name: 'export_solution',
    description:
      'Export a solution and write the .zip to disk. Read-only against the environment. ' +
      'This is the packaging half of promoting flows between environments.',
    inputSchema: {
      type: 'object',
      properties: {
        environment_id: { type: 'string' },
        solution_name: { type: 'string', description: 'The solution UNIQUE name' },
        managed: { type: 'boolean', description: 'Default false' },
        output_path: { type: 'string', description: 'Absolute .zip path' }
      },
      required: ['environment_id', 'solution_name'],
      additionalProperties: false
    }
  },
  {
    name: 'import_solution',
    description:
      'Import a solution .zip, optionally rebinding connection references and environment ' +
      'variables on the way in via ComponentParameters. Gated as a write. This is the half that ' +
      'makes a promoted flow actually run in the target environment rather than land broken.',
    inputSchema: {
      type: 'object',
      properties: {
        environment_id: { type: 'string' },
        file_path: { type: 'string', description: 'Absolute path to the .zip' },
        publish_workflows: { type: 'boolean', description: 'Default true' },
        overwrite_unmanaged: { type: 'boolean', description: 'Default true' },
        component_parameters: {
          type: 'array',
          description: 'Connection-reference and environment-variable overrides',
          items: { type: 'object' }
        }
      },
      required: ['environment_id', 'file_path'],
      additionalProperties: false
    }
  },
  {
    name: 'add_flow_to_solution',
    description:
      'Add an existing flow to a solution so it can be exported. Gated as a write. A flow created ' +
      'outside a solution is invisible to ALM until this is done.',
    inputSchema: {
      type: 'object',
      properties: {
        environment_id: { type: 'string' },
        flow_id: { type: 'string', description: 'Dataverse workflow id' },
        solution_name: { type: 'string', description: 'Target solution UNIQUE name' }
      },
      required: ['environment_id', 'flow_id', 'solution_name'],
      additionalProperties: false
    }
  },
  /* ----------------------------------------- v0.5.0: governance -- */
  {
    name: 'list_dlp_policies',
    description:
      'Data loss prevention policies visible to you. Read-only. Answers "will this connector ' +
      'combination be blocked before I build it". Requires admin scope - expect a refusal if ' +
      'you hold none.',
    inputSchema: {
      type: 'object',
      properties: { environment_id: { type: 'string' } },
      additionalProperties: false
    }
  },
  {
    name: 'list_flows_as_admin',
    description:
      'Every flow in an environment including other people flows, via the admin scope. ' +
      'Read-only. Requires a Power Platform admin role - expect 403 if you hold none.',
    inputSchema: {
      type: 'object',
      properties: { environment_id: { type: 'string' }, top: { type: 'number' } },
      required: ['environment_id'],
      additionalProperties: false
    }
  },
  /* --------------------------------------- v0.5.0: differentiators -- */
  {
    name: 'map_child_flows',
    description:
      'Map parent-to-child flow relationships across an environment by finding every action of ' +
      'type Workflow and reporting WHERE in the definition it sits - including inside a condition ' +
      'else branch, a switch case or a loop. Read-only and costs no extra call beyond reading the ' +
      'definitions. Nothing in the portal shows this.',
    inputSchema: {
      type: 'object',
      properties: {
        environment_id: { type: 'string' },
        flow_id: { type: 'string', description: 'Omit to scan the whole environment' },
        top: { type: 'number', description: 'Max flows to scan, default 50' }
      },
      required: ['environment_id'],
      additionalProperties: false
    }
  },
  {
    name: 'evaluate_expression',
    description:
      'Evaluate a Workflow Definition Language expression locally against a supplied context, so ' +
      'you can settle what an @{...} expression actually produces WITHOUT running the flow. No ' +
      'network, no sign-in, no environment needed. Covers string, collection, logic, math and ' +
      'conversion functions; date and runtime functions raise by name rather than guessing.'
    /* PLUGIN-LESSONS:start evaluate_expression */
    + 'OPERATING RULES, each learned from a real failure and regenerated from '
    + 'cowork-lessons.md - do not hand-edit: Call `evaluate_expression` with BOTH fixes or '
    + 'it lies to you. (1) Wrap the expression in `@{...}` - unprefixed input is echoed '
    + 'back verbatim as a string with `evaluated_locally: true`, a silent false success, '
    + 'not an error. (2) Drop the `?` from `?[...]`, which the parser rejects with REFUSED '
    + '"unexpected character ?". Fix (2) alone lands you in failure (1). The rewrite is for '
    + 'THIS evaluator only - keep `?[...]` in the flow, where it is valid and null-safe. '
    /* PLUGIN-LESSONS:end */
    ,
    inputSchema: {
      type: 'object',
      properties: {
        expression: { type: 'string' },
        context: {
          type: 'object',
          description: 'Optional: variables, parameters, triggerBody, outputs, item, items'
        }
      },
      required: ['expression'],
      additionalProperties: false
    }
  }
];

async function callTool(name, args) {
  const cfg = loadConfig();

  if (name === 'bridge_status') {
    const cached = readCache(cfg);
    return {
      config_file: CONFIG_PATH,
      config_loaded: cfg._loaded,
      config_error: cfg._load_error || null,
      server_version: SERVER_VERSION,
      api: {
        definitions: 'Dataverse Web API ' + API_PATH + ' (workflow table, category 5)',
        runs: FLOW_API_HOST + ' (audience ' + FLOW_RESOURCE + ', api-version ' + FLOW_API_VERSION + ')'
      },
      capabilities: {
        definitions: ['list_flows', 'get_flow', 'create_flow', 'update_flow',
                      'delete_flow', 'set_flow_state', 'analyze_flow',
                      'find_flows_using_connector'],
        runs: ['run_flow', 'get_run_history', 'get_run_actions', 'cancel_run',
               'resubmit_run', 'list_all_flows', 'list_connections'],
        owners: ['list_flow_owners', 'add_flow_owner', 'remove_flow_owner'],
        solution_alm: ['list_solutions', 'export_solution', 'import_solution',
                       'add_flow_to_solution'],
        governance: ['list_dlp_policies', 'list_flows_as_admin'],
        local_analysis: ['map_child_flows', 'evaluate_expression']
      },
      auth_strategy: cfg.auth_strategy,
      auth_configured: cfg.auth_strategy === 'interactive' && !!cfg.tenant_id && !!cfg.client_id,
      token_cache_configured: !!cfg.token_cache_file,
      token_cache_resources: cached ? Object.keys(cached) : [],
      read_only: cfg.read_only,
      allow_delete: cfg.allow_delete,
      allowed_environments: cfg.allowed_environments,
      allow_prod: cfg.allow_prod,
      audit_log: AUDIT_LOG,
      note: cfg.auth_strategy === 'none'
        ? 'Inert: auth_strategy is "none", so every flow tool refuses.'
        : (cfg.token_cache_file
            ? 'Interactive auth with a token cache. The first call may open a browser; later calls reuse the refresh token.'
            : 'Interactive auth with NO token cache. This bridge runs stateless, so EVERY call will open a browser until token_cache_file is set.')
    };
  }

  /* Pure local evaluation - no environment, no token, no network. Handled here
   * so it stays usable even when no environment is reachable. */
  if (name === 'evaluate_expression') {
    try {
      const value = evaluateWdl(args.expression, args.context || {});
      return {
        expression: args.expression,
        value,
        type: value === null ? 'null' : (Array.isArray(value) ? 'array' : typeof value),
        evaluated_locally: true
      };
    } catch (e) {
      throw new Refusal('could not evaluate: ' + e.message);
    }
  }

  /* Config-only, so it runs before environment resolution and never signs in. */
  if (name === 'list_environments') {
    const rows = (cfg.allowed_environments || []).map(e => {
      if (typeof e === 'string') return { id: e, name: '(unnamed)', org_url: null, usable: false,
                                          note: 'string entry has no org_url - unusable' };
      const isProd = e.production === true || /prod/i.test(String(e.name || ''));
      const prodOk = (cfg.allow_prod || []).includes(e.id);
      return {
        id: e.id,
        name: e.name || '(unnamed)',
        org_url: e.org_url || null,
        production: isProd,
        reachable: !(isProd && !prodOk) && !!e.org_url,
        writable: !cfg.read_only && e.read_only !== true && !(isProd && !prodOk),
        note: !e.org_url ? 'no org_url - every call refuses'
            : (isProd && !prodOk) ? 'production and not in allow_prod - every call refuses'
            : (e.read_only === true) ? 'reads only - pinned read_only for this environment'
            : (cfg.read_only ? 'reads only - bridge is globally read_only' : 'read and write')
      };
    });
    return {
      count: rows.length,
      global_read_only: cfg.read_only,
      global_allow_delete: cfg.allow_delete,
      environments: rows
    };
  }

  const env = requireEnvironment(cfg, args.environment_id);

  switch (name) {

    /* ---------------------------------------------- Flow service: runs -- */

    case 'list_all_flows': {
      const top = Math.min(Math.max(parseInt(args.top, 10) || 50, 1), 250);
      const r = await flowApi(cfg, env, 'GET', flowBase(env) + '/flows?$top=' + top);
      const rows = ((r.json && r.json.value) || []).map(f => ({
        flow_id: f.name,
        display_name: (f.properties && f.properties.displayName) || null,
        state: (f.properties && f.properties.state) || null,
        created: (f.properties && f.properties.createdTime) || null,
        modified: (f.properties && f.properties.lastModifiedTime) || null
      }));
      return {
        environment: env.name || env.id,
        flow_environment_id: flowEnvId(env),
        source: 'Flow service (includes personal flows Dataverse cannot see)',
        count: rows.length,
        flows: rows
      };
    }

    case 'get_run_history': {
      const top = Math.min(Math.max(parseInt(args.top, 10) || 20, 1), 100);
      const res = await resolveFlowServiceId(cfg, env, args.flow_id);
      const r = await flowApi(cfg, env, 'GET',
                              flowBase(env) + '/flows/' + res.id + '/runs?$top=' + top);
      const runs = ((r.json && r.json.value) || []).map(shapeRun);
      return {
        environment: env.name || env.id,
        flow_id: res.id,
        id_translated: res.resolved ? ('matched "' + res.matched_on + '" - the id given was a Dataverse id') : undefined,
        count: runs.length,
        note: runs.length ? undefined : 'no runs - this flow has never fired',
        runs
      };
    }

    case 'get_run_actions': {
      const resA = await resolveFlowServiceId(cfg, env, args.flow_id);
      const r = await flowApi(cfg, env, 'GET',
                              flowBase(env) + '/flows/' + resA.id +
                              '/runs/' + args.run_id + '/actions');
      const actions = ((r.json && r.json.value) || []).map(a => {
        const p = a.properties || {};
        return {
          action: a.name,
          status: p.status || null,
          start_time: p.startTime || null,
          end_time: p.endTime || null,
          error: p.error ? { code: p.error.code, message: p.error.message } : null
        };
      });
      const failed = actions.filter(a => a.status && a.status !== 'Succeeded' && a.status !== 'Skipped');
      return {
        flow_id: args.flow_id,
        run_id: args.run_id,
        count: actions.length,
        failed_actions: failed.length ? failed : undefined,
        actions
      };
    }

    case 'run_flow': {
      requireWritable(cfg, 'run_flow', env);
      audit({ tool: 'run_flow', env: env.id, flow_id: args.flow_id, outcome: 'attempt' });

      const resR = await resolveFlowServiceId(cfg, env, args.flow_id);
      let trigger = args.trigger_name;
      if (!trigger) {
        const t = await flowApi(cfg, env, 'GET',
                                flowBase(env) + '/flows/' + resR.id + '/triggers');
        const triggers = (t.json && t.json.value) || [];
        if (!triggers.length) {
          audit({ tool: 'run_flow', env: env.id, flow_id: args.flow_id,
                  outcome: 'refused', reason: 'flow exposes no trigger' });
          throw new Refusal('this flow exposes no trigger that can be started on demand.');
        }
        trigger = triggers[0].name;
      }

      const r = await flowApi(cfg, env, 'POST',
                              flowBase(env) + '/flows/' + resR.id +
                              '/triggers/' + trigger + '/run',
                              args.inputs || {});

      audit({ tool: 'run_flow', env: env.id, flow_id: args.flow_id,
              trigger, http: r.status, outcome: 'started' });

      return {
        started: true,
        flow_id: args.flow_id,
        trigger,
        http_status: r.status,
        run: r.json ? shapeRun(r.json) : null,
        note: 'Use get_run_history to see the outcome, then get_run_actions for step detail.'
      };
    }

    case 'cancel_run': {
      requireWritable(cfg, 'cancel_run', env);
      audit({ tool: 'cancel_run', env: env.id, flow_id: args.flow_id,
              run_id: args.run_id, outcome: 'attempt' });
      /* v0.5.0: cancel_run was the ONE run tool that skipped the resolver, so a
       * Dataverse id here returned a bare 404 FlowNotFound while the same id
       * worked in get_run_history. Fixed for consistency. */
      const resC = await resolveFlowServiceId(cfg, env, args.flow_id);
      const r = await flowApi(cfg, env, 'POST',
                              flowBase(env) + '/flows/' + resC.id +
                              '/runs/' + args.run_id + '/cancel');
      audit({ tool: 'cancel_run', env: env.id, flow_id: resC.id,
              run_id: args.run_id, outcome: 'cancelled' });
      return { cancelled: true, flow_id: resC.id,
               id_translated: resC.resolved ? ('matched "' + resC.matched_on + '" - the id given was a Dataverse id') : undefined,
               run_id: args.run_id, http_status: r.status };
    }

    case 'list_connections': {
      /* Connection INSTANCES live on api.powerapps.com. api.flow.microsoft.com
       * 404s on every /connections shape - measured across 8 candidate paths. */
      /* Measured across 8 candidate paths, 2026-09-02. Connections are NOT
       * nested under an environment path - that shape 404s on both hosts.
       * They are a flat collection FILTERED by environment, and the filter
       * value must be the PREFIXED flow env id (Default-<guid>); the bare
       * guid returns 404 rather than an empty list. */
      const r = await powerAppsApi(cfg, env,
                                   "/providers/Microsoft.PowerApps/connections?$filter=environment eq '" +
                                   flowEnvId(env) + "'");
      const rows = ((r.json && r.json.value) || []).map(c => {
        const p = c.properties || {};
        return {
          connection_id: c.name,
          connector: (p.apiId || '').split('/').pop() || null,
          display_name: p.displayName || null,
          status: Array.isArray(p.statuses) && p.statuses.length ? p.statuses[0].status : null,
          created_by: (p.createdBy && p.createdBy.displayName) || null
        };
      });
      const usable = rows.filter(c => c.status === 'Connected');
      return {
        environment: env.name || env.id,
        count: rows.length,
        usable_count: usable.length,
        note: 'Author flows against a connector that appears here with status Connected. ' +
              'A flow referencing anything else is created but will not run.',
        connections: rows
      };
    }

    case 'find_connector': {
      const top = Math.min(Math.max(parseInt(args.top, 10) || 25, 1), 100);
      const needle = String(args.search || '').toLowerCase();
      const r = await flowApi(cfg, env, 'GET', flowBase(env) + '/apis');
      const all = (r.json && r.json.value) || [];
      const hits = all.filter(a => {
        const p = a.properties || {};
        return String(p.displayName || '').toLowerCase().indexOf(needle) >= 0 ||
               String(a.name || '').toLowerCase().indexOf(needle) >= 0;
      }).slice(0, top).map(a => {
        const p = a.properties || {};
        return {
          connector_id: a.name,
          display_name: p.displayName || null,
          tier: p.tier || null,
          description: p.description ? String(p.description).slice(0, 140) : null
        };
      });
      return {
        environment: env.name || env.id,
        catalog_size: all.length,
        search: args.search,
        count: hits.length,
        note: 'connector_id is what goes in a flow definition. Premium-tier connectors need ' +
              'a licence. Check list_connections for whether one is actually authorised.',
        connectors: hits
      };
    }

    /* ------------------------------------------- Dataverse: definitions -- */

    case 'analyze_flow': {
      const r = await dataverse(cfg, env, 'GET', `/workflows(${args.flow_id})?${SELECT_ONE}`);
      if (!r) throw new Refusal(`no flow with id ${args.flow_id} in ${env.name || env.id}.`);
      return Object.assign(shape(r), { analysis: analyzeDefinition(r.clientdata) });
    }

    case 'find_flows_using_connector': {
      const top = Math.min(Math.max(parseInt(args.top, 10) || 100, 1), 200);
      const q = `/workflows?$select=workflowid,name,statecode,clientdata` +
                `&$filter=category eq ${CAT_MODERN}&$orderby=modifiedon desc&$top=${top}`;
      const r = await dataverse(cfg, env, 'GET', q);
      const rows = (r && r.value) || [];
      const needle = args.connector ? String(args.connector).toLowerCase() : null;

      const matches = [];
      const index = {};
      let unparsed = 0;
      for (const row of rows) {
        const a = analyzeDefinition(row.clientdata);
        if (a.parse_error) { unparsed++; continue; }
        for (const c of a.connectors) {
          const key = c.connector || '(unknown)';
          (index[key] = index[key] || []).push(row.name);
          if (needle && key.toLowerCase().indexOf(needle) === -1) continue;
          if (needle) matches.push({
            flow_id: row.workflowid,
            display_name: row.name,
            state: row.statecode === 1 ? 'started' : 'stopped',
            connector: key,
            reference: c.reference
          });
        }
      }
      for (const k of Object.keys(index)) index[k] = Array.from(new Set(index[k])).sort();

      const out = {
        environment: env.name || env.id,
        flows_scanned: rows.length,
        definitions_unparseable: unparsed,
        connector_index: index
      };
      if (needle) { out.filter = args.connector; out.match_count = matches.length; out.matches = matches; }
      if (rows.length === top)
        out.warning = `scanned the newest ${top} flows only - raise top if the environment holds more`;
      return out;
    }

    case 'list_flows': {
      const top = Math.min(Math.max(parseInt(args.top, 10) || 50, 1), 200);
      const q = `/workflows?${SELECT_LIST}&$filter=category eq ${CAT_MODERN}` +
                `&$orderby=modifiedon desc&$top=${top}`;
      const r = await dataverse(cfg, env, 'GET', q);
      const rows = (r && r.value) || [];
      return {
        environment: env.name || env.id,
        org_url: env.org_url,
        count: rows.length,
        flows: rows.map(shape)
      };
    }

    case 'get_flow': {
      const r = await dataverse(cfg, env, 'GET', `/workflows(${args.flow_id})?${SELECT_ONE}`);
      if (!r) throw new Refusal(`no flow with id ${args.flow_id} in ${env.name || env.id}.`);
      const out = shape(r);
      out.description = r.description || null;
      try {
        const cd = JSON.parse(r.clientdata);
        /* unwrap the envelope so callers see the definition they passed in */
        out.definition = (cd && cd.properties && cd.properties.definition)
          ? cd.properties.definition : cd;
        if (cd && cd.properties && cd.properties.connectionReferences)
          out.connection_references = cd.properties.connectionReferences;
      } catch (_) { out.definition_raw = r.clientdata; }
      return out;
    }

    case 'create_flow': {
      requireWritable(cfg, 'create_flow', env);
      audit({ tool: 'create_flow', env: env.id, name: args.display_name, outcome: 'attempt' });
      const body = {
        category:      CAT_MODERN,
        type:          1,
        primaryentity: 'none',
        name:          args.display_name,
        clientdata:    toClientData(args.definition)
      };
      if (args.description) body.description = args.description;
      const r = await dataverse(cfg, env, 'POST', '/workflows', body);
      audit({ tool: 'create_flow', env: env.id, flow_id: r && r.workflowid, outcome: 'created' });
      return Object.assign({ created: true, note: 'Created in Draft. Use set_flow_state to start it.' },
                           shape(r));
    }

    case 'update_flow': {
      requireWritable(cfg, 'update_flow', env);
      if (!args.display_name && !args.definition && !args.description)
        throw new Refusal('update_flow needs display_name, definition, description, or a combination.');
      audit({ tool: 'update_flow', env: env.id, flow_id: args.flow_id, outcome: 'attempt' });
      const body = {};
      if (args.display_name) body.name        = args.display_name;
      if (args.description)  body.description = args.description;
      if (args.definition)   body.clientdata  = toClientData(args.definition);
      const r = await dataverse(cfg, env, 'PATCH', `/workflows(${args.flow_id})`, body);
      audit({ tool: 'update_flow', env: env.id, flow_id: args.flow_id, outcome: 'updated' });
      return Object.assign({ updated: true, fields: Object.keys(body) }, shape(r));
    }

    case 'delete_flow': {
      requireWritable(cfg, 'delete_flow', env);
      requireDeleteAllowed(cfg);

      /* Read before destroying and require the caller to have named it. A wrong
       * GUID cannot slip through, and the target is one row addressed by id. */
      const current = await dataverse(cfg, env, 'GET', `/workflows(${args.flow_id})?${SELECT_LIST}`);
      if (!current) throw new Refusal(`no flow with id ${args.flow_id} in ${env.name || env.id}.`);
      const actual = current.name || '';
      if (actual !== args.confirm_name) {
        audit({ tool: 'delete_flow', env: env.id, flow_id: args.flow_id,
                outcome: 'refused-name-mismatch', actual, supplied: args.confirm_name });
        throw new Refusal(`delete_flow refused: confirm_name does not match. The flow is named "${actual}".`);
      }
      audit({ tool: 'delete_flow', env: env.id, flow_id: args.flow_id, name: actual, outcome: 'attempt' });
      await dataverse(cfg, env, 'DELETE', `/workflows(${args.flow_id})`);
      const gone = await dataverse(cfg, env, 'GET', `/workflows(${args.flow_id})?${SELECT_LIST}`);
      if (gone) {
        audit({ tool: 'delete_flow', env: env.id, flow_id: args.flow_id, outcome: 'still-present' });
        throw new Error('delete was accepted but the flow is still present - check state before retrying.');
      }
      audit({ tool: 'delete_flow', env: env.id, flow_id: args.flow_id, name: actual, outcome: 'deleted' });
      return { deleted: true, flow_id: args.flow_id, display_name: actual };
    }

    case 'set_flow_state': {
      requireWritable(cfg, 'set_flow_state', env);
      const started = args.state === 'started';
      audit({ tool: 'set_flow_state', env: env.id, flow_id: args.flow_id, state: args.state, outcome: 'attempt' });
      await dataverse(cfg, env, 'PATCH', `/workflows(${args.flow_id})`,
                      { statecode: started ? 1 : 0, statuscode: started ? 2 : 1 });
      const after = await dataverse(cfg, env, 'GET', `/workflows(${args.flow_id})?${SELECT_LIST}`);
      const now = after ? (after.statecode === 1 ? 'started' : 'stopped') : 'unknown';
      if (now !== args.state) {
        audit({ tool: 'set_flow_state', env: env.id, flow_id: args.flow_id, outcome: 'did-not-take', now });
        throw new Error(`state change was accepted but the flow reads as "${now}".`);
      }
      audit({ tool: 'set_flow_state', env: env.id, flow_id: args.flow_id, state: args.state, outcome: 'set' });
      return { flow_id: args.flow_id, display_name: after.name, state: now };
    }

    /* ------------------------------------------------ v0.5.0: runs -- */

    case 'resubmit_run': {
      requireWritable(cfg, 'resubmit_run', env);
      audit({ tool: 'resubmit_run', env: env.id, flow_id: args.flow_id,
              run_id: args.run_id, outcome: 'attempt' });
      const resub = await resolveFlowServiceId(cfg, env, args.flow_id);
      const trg = args.trigger_name || await firstTriggerName(cfg, env, resub.id);
      const r = await flowApi(cfg, env, 'POST',
                              flowBase(env) + '/flows/' + resub.id +
                              '/triggers/' + trg + '/histories/' + args.run_id + '/resubmit');
      audit({ tool: 'resubmit_run', env: env.id, flow_id: resub.id,
              run_id: args.run_id, trigger: trg, http: r.status, outcome: 'resubmitted' });
      return {
        resubmitted: true,
        flow_id: resub.id,
        id_translated: resub.resolved ? ('matched "' + resub.matched_on + '" - the id given was a Dataverse id') : undefined,
        original_run_id: args.run_id,
        trigger: trg,
        http_status: r.status,
        note: 'A NEW run was queued with the original trigger inputs. Use get_run_history to see it.'
      };
    }

    /* ---------------------------------------------- v0.5.0: owners -- */

    case 'list_flow_owners': {
      const resO = await resolveFlowServiceId(cfg, env, args.flow_id);
      const r = await flowApi(cfg, env, 'GET',
                              flowBase(env) + '/flows/' + resO.id + '/permissions');
      const rows = ((r.json && r.json.value) || []).map(p => {
        const pr = (p.properties && p.properties.principal) || {};
        return {
          permission_id: p.name,
          role: (p.properties && p.properties.roleName) || null,
          principal_id: pr.id || null,
          display_name: pr.displayName || null,
          email: pr.email || null,
          type: pr.type || null
        };
      });
      return {
        environment: env.name || env.id,
        flow_id: resO.id,
        count: rows.length,
        owners: rows
      };
    }

    case 'add_flow_owner': {
      requireWritable(cfg, 'add_flow_owner', env);
      const resAO = await resolveFlowServiceId(cfg, env, args.flow_id);
      const role = args.role || 'CanEdit';
      audit({ tool: 'add_flow_owner', env: env.id, flow_id: resAO.id,
              principal: args.principal_id, role, outcome: 'attempt' });
      const principal = { id: args.principal_id, type: 'User' };
      if (args.principal_email)        principal.email       = args.principal_email;
      if (args.principal_display_name) principal.displayName = args.principal_display_name;
      const r = await flowApi(cfg, env, 'POST',
                              flowBase(env) + '/flows/' + resAO.id + '/modifyPermissions',
                              { put: [{ properties: { roleName: role, principal } }] });
      audit({ tool: 'add_flow_owner', env: env.id, flow_id: resAO.id,
              principal: args.principal_id, http: r.status, outcome: 'granted' });
      return { granted: true, flow_id: resAO.id, principal_id: args.principal_id,
               role, http_status: r.status };
    }

    case 'remove_flow_owner': {
      requireWritable(cfg, 'remove_flow_owner', env);
      const resRO = await resolveFlowServiceId(cfg, env, args.flow_id);

      /* Read first: removing the only owner orphans the flow, and the API will
       * happily do it. Refuse rather than let that happen silently. */
      const cur = await flowApi(cfg, env, 'GET',
                                flowBase(env) + '/flows/' + resRO.id + '/permissions');
      const owners = ((cur.json && cur.json.value) || []);
      const target = owners.find(p => {
        const pr = (p.properties && p.properties.principal) || {};
        return pr.id === args.principal_id;
      });
      if (!target) {
        audit({ tool: 'remove_flow_owner', env: env.id, flow_id: resRO.id,
                principal: args.principal_id, outcome: 'refused-not-an-owner' });
        throw new Refusal(args.principal_id + ' does not currently have access to this flow.');
      }
      if (owners.length <= 1) {
        audit({ tool: 'remove_flow_owner', env: env.id, flow_id: resRO.id,
                principal: args.principal_id, outcome: 'refused-last-owner' });
        throw new Refusal('refusing to remove the only remaining owner - that would orphan the flow.');
      }
      audit({ tool: 'remove_flow_owner', env: env.id, flow_id: resRO.id,
              principal: args.principal_id, outcome: 'attempt' });
      const r = await flowApi(cfg, env, 'POST',
                              flowBase(env) + '/flows/' + resRO.id + '/modifyPermissions',
                              { delete: [{ id: args.principal_id }] });
      audit({ tool: 'remove_flow_owner', env: env.id, flow_id: resRO.id,
              principal: args.principal_id, http: r.status, outcome: 'revoked' });
      return { revoked: true, flow_id: resRO.id, principal_id: args.principal_id,
               remaining_owners: owners.length - 1, http_status: r.status };
    }

    /* ------------------------------------------- v0.5.0: solution ALM -- */

    case 'list_solutions': {
      const filter = args.include_managed ? '' : '&$filter=ismanaged eq false';
      const r = await dataverse(cfg, env, 'GET',
        '/solutions?$select=solutionid,uniquename,friendlyname,version,ismanaged,isvisible' +
        '&$orderby=friendlyname asc' + filter);
      const rows = ((r && r.value) || [])
        .filter(s => s.isvisible !== false)
        .map(s => ({
          solution_id: s.solutionid,
          unique_name: s.uniquename,
          display_name: s.friendlyname,
          version: s.version,
          managed: s.ismanaged === true
        }));
      return {
        environment: env.name || env.id,
        count: rows.length,
        note: 'export_solution and add_flow_to_solution take unique_name, not display_name.',
        solutions: rows
      };
    }

    case 'export_solution': {
      const r = await dataverse(cfg, env, 'POST', '/ExportSolution', {
        SolutionName: args.solution_name,
        Managed: args.managed === true
      });
      const b64 = r && r.ExportSolutionFile;
      if (!b64) throw new Error('export returned no file - check the solution unique name.');
      const bytes = Buffer.from(b64, 'base64');
      const dest = args.output_path ||
                   path.join(COWORK_ROOT, 'Outputs',
                             args.solution_name + '_' +
                             (args.managed ? 'managed' : 'unmanaged') + '.zip');
      fs.mkdirSync(path.dirname(dest), { recursive: true });
      fs.writeFileSync(dest, bytes);
      audit({ tool: 'export_solution', env: env.id, solution: args.solution_name,
              bytes: bytes.length, path: dest, outcome: 'exported' });
      return {
        exported: true,
        solution_name: args.solution_name,
        managed: args.managed === true,
        bytes: bytes.length,
        path: dest
      };
    }

    case 'import_solution': {
      requireWritable(cfg, 'import_solution', env);
      if (!fs.existsSync(args.file_path))
        throw new Refusal('no file at ' + args.file_path + '.');
      const jobId = crypto.randomUUID();
      audit({ tool: 'import_solution', env: env.id, file: args.file_path,
              import_job: jobId, outcome: 'attempt' });
      const body = {
        OverwriteUnmanagedCustomizations: args.overwrite_unmanaged !== false,
        PublishWorkflows: args.publish_workflows !== false,
        CustomizationFile: fs.readFileSync(args.file_path).toString('base64'),
        ImportJobId: jobId
      };
      /* ComponentParameters is what rebinds connection references and
       * environment variables as the solution lands. Without it a promoted
       * flow imports pointing at the SOURCE environment connections. */
      if (Array.isArray(args.component_parameters) && args.component_parameters.length)
        body.ComponentParameters = args.component_parameters;

      await dataverse(cfg, env, 'POST', '/ImportSolution', body);
      audit({ tool: 'import_solution', env: env.id, import_job: jobId, outcome: 'imported' });
      return {
        imported: true,
        import_job_id: jobId,
        rebound_components: Array.isArray(args.component_parameters) ? args.component_parameters.length : 0,
        note: 'Import is asynchronous server-side. Query the importjob table with this id for progress.'
      };
    }

    case 'add_flow_to_solution': {
      requireWritable(cfg, 'add_flow_to_solution', env);
      audit({ tool: 'add_flow_to_solution', env: env.id, flow_id: args.flow_id,
              solution: args.solution_name, outcome: 'attempt' });
      await dataverse(cfg, env, 'POST', '/AddSolutionComponent', {
        ComponentId: args.flow_id,
        ComponentType: 29,
        SolutionUniqueName: args.solution_name,
        AddRequiredComponents: false
      });
      audit({ tool: 'add_flow_to_solution', env: env.id, flow_id: args.flow_id,
              solution: args.solution_name, outcome: 'added' });
      return { added: true, flow_id: args.flow_id, solution_name: args.solution_name,
               component_type: 29 };
    }

    /* ----------------------------------------- v0.5.0: governance -- */

    case 'list_dlp_policies': {
      const r = await bapApi(cfg, 'GET',
        '/providers/Microsoft.BusinessAppPlatform/scopes/admin/apiPolicies');
      const rows = ((r.json && r.json.value) || []).map(p => ({
        policy_id: p.name || (p.properties && p.properties.name) || null,
        display_name: (p.properties && p.properties.displayName) || null,
        environment_type: (p.properties && p.properties.environmentType) || null,
        created: (p.properties && p.properties.createdTime) || null
      }));
      return { count: rows.length, policies: rows };
    }

    case 'list_flows_as_admin': {
      const topA = Math.min(Math.max(parseInt(args.top, 10) || 50, 1), 250);
      const r = await flowApi(cfg, env, 'GET',
        '/providers/Microsoft.ProcessSimple/scopes/admin/environments/' +
        flowEnvId(env) + '/flows?$top=' + topA);
      const rows = ((r.json && r.json.value) || []).map(f => ({
        flow_id: f.name,
        display_name: (f.properties && f.properties.displayName) || null,
        state: (f.properties && f.properties.state) || null,
        owner: (f.properties && f.properties.creator && f.properties.creator.userId) || null
      }));
      return {
        environment: env.name || env.id,
        scope: 'admin',
        count: rows.length,
        flows: rows
      };
    }

    /* --------------------------------------- v0.5.0: differentiators -- */

    case 'map_child_flows': {
      const topM = Math.min(Math.max(parseInt(args.top, 10) || 50, 1), 250);
      let rows;
      if (args.flow_id) {
        const one = await dataverse(cfg, env, 'GET',
                                    '/workflows(' + args.flow_id + ')?' + SELECT_ONE);
        if (!one) throw new Refusal('no flow with id ' + args.flow_id + ' in ' + (env.name || env.id) + '.');
        rows = [one];
      } else {
        const q = '/workflows?' + SELECT_ONE + '&$filter=category eq ' + CAT_MODERN +
                  '&$orderby=modifiedon desc&$top=' + topM;
        const r = await dataverse(cfg, env, 'GET', q);
        rows = (r && r.value) || [];
      }

      const nameById = {};
      rows.forEach(w => { nameById[String(w.workflowid).toLowerCase()] = w.name; });

      const edges = [];
      const parents = [];
      for (const w of rows) {
        const found = findChildFlowCalls(w.clientdata);
        if (found.parse_error) {
          parents.push({ flow_id: w.workflowid, display_name: w.name, parse_error: true });
          continue;
        }
        if (!found.calls.length) continue;
        parents.push({
          flow_id: w.workflowid,
          display_name: w.name,
          child_count: found.calls.length,
          calls: found.calls.map(c => Object.assign({}, c, {
            child_display_name: nameById[String(c.child_flow_id || '').toLowerCase()] || null
          }))
        });
        for (const c of found.calls) {
          edges.push({
            parent_id: w.workflowid,
            parent: w.name,
            child_id: c.child_flow_id,
            child: nameById[String(c.child_flow_id || '').toLowerCase()] || '(outside the scanned set)',
            at: c.path
          });
        }
      }

      const calledIds = new Set(edges.map(e => String(e.child_id || '').toLowerCase()));
      const calledAsChild = rows
        .filter(w => calledIds.has(String(w.workflowid).toLowerCase()))
        .map(w => w.name);

      return {
        environment: env.name || env.id,
        scanned: rows.length,
        parents_with_children: parents.filter(p => !p.parse_error).length,
        edge_count: edges.length,
        called_as_child: calledAsChild,
        note: edges.length
          ? 'A child flow reached only from a parent will show no trigger activity of its own.'
          : 'No parent-child relationships found in the scanned set.',
        parents,
        edges
      };
    }

    default:
      throw new Refusal(`unknown tool: ${name}`);
  }
}

/* --------------------------------------------------------------- jsonrpc -- */

function send(obj) { process.stdout.write(JSON.stringify(obj) + '\n'); }
function ok(id, result) { send({ jsonrpc: '2.0', id, result }); }
function fail(id, code, message) { send({ jsonrpc: '2.0', id, error: { code, message } }); }
function toolErr(id, text) { ok(id, { content: [{ type: 'text', text }], isError: true }); }

async function handle(msg) {
  const { id, method, params } = msg || {};
  const isNotification = (id === undefined || id === null);

  switch (method) {
    case 'initialize': {
      const requested = params && params.protocolVersion;
      return ok(id, {
        protocolVersion: typeof requested === 'string' ? requested : DEFAULT_PROTOCOL,
        capabilities: { tools: {} },
        serverInfo: { name: SERVER_NAME, version: SERVER_VERSION }
      });
    }

    case 'notifications/initialized':
    case 'initialized':
      return;

    case 'ping':
      return ok(id, {});

    case 'tools/list':
      return ok(id, { tools: TOOLS });

    case 'tools/call': {
      const name = params && params.name;
      const args = (params && params.arguments) || {};
      const tool = TOOLS.find(t => t.name === name);
      if (!tool) return fail(id, -32602, `Unknown tool: ${name}`);

      const allowedKeys = Object.keys(tool.inputSchema.properties || {});
      const extra = Object.keys(args).filter(k => !allowedKeys.includes(k));
      if (extra.length)
        return toolErr(id, `REJECTED: unexpected parameter(s): ${extra.join(', ')}.`);

      try {
        const result = await callTool(name, args);
        return ok(id, { content: [{ type: 'text', text: JSON.stringify(result, null, 2) }] });
      } catch (e) {
        if (e instanceof Refusal) {
          audit({ tool: name, outcome: 'refused', reason: e.reason });
          return toolErr(id, `REFUSED: ${e.reason}`);
        }
        audit({ tool: name, outcome: 'error', message: e.message, status: e.status || null });
        return toolErr(id, `ERROR: ${e.message}${e.status ? ` (HTTP ${e.status})` : ''}`);
      }
    }

    default:
      if (isNotification) return;
      return fail(id, -32601, `Method not found: ${method}`);
  }
}

/* ---------------------------------------------------------------- stdio -- */

const boot = loadConfig();
process.stderr.write(
  `[cowork-power-automate] v${SERVER_VERSION} ready. Tools: ${TOOLS.map(t => t.name).join(', ')}\n` +
  `[cowork-power-automate] config: ${CONFIG_PATH} (${boot._loaded ? 'loaded' : boot._load_error})\n` +
  `[cowork-power-automate] auth=${boot.auth_strategy} cache=${boot.token_cache_file ? 'on' : 'OFF'} ` +
  `read_only=${boot.read_only} allow_delete=${boot.allow_delete} ` +
  `environments=${(boot.allowed_environments || []).length}\n` +
  `[cowork-power-automate] Dataverse Web API ${API_PATH}, workflow table, category ${CAT_MODERN}.\n`);

let buf = '';
process.stdin.setEncoding('utf8');
process.stdin.on('data', (chunk) => {
  buf += chunk;
  let nl;
  while ((nl = buf.indexOf('\n')) >= 0) {
    const line = buf.slice(0, nl).trim();
    buf = buf.slice(nl + 1);
    if (!line) continue;
    let msg;
    try { msg = JSON.parse(line); }
    catch (_) {
      send({ jsonrpc: '2.0', id: null, error: { code: -32700, message: 'Parse error' } });
      continue;
    }
    Promise.resolve(handle(msg)).catch((e) => {
      if (msg && msg.id !== undefined && msg.id !== null)
        fail(msg.id, -32603, `Internal error: ${e.message}`);
    });
  }
});

process.stdin.on('end', () => process.exit(0));
