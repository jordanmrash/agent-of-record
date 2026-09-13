# Installation evidence

`scripts/install_check.py --json` writes a results file describing one real
installation: the host, the runtime versions, whether each own-code bridge
completed a live MCP handshake, and the corpus checks. This folder is the
reviewed home for those files.

A results file here is a claim of the form "on this host, on this date, the
installation reached this state" - made by the checker, not by prose. It is the
evidence `docs/setup.md` and `docs/setup-macos.md` rest on. When a setup guide
says a step works, a file here should show that it did.

## Contributing one

1. Run the checker on the installed machine, naming the route the host uses:

   ```bash
   python3 scripts/install_check.py --route local --json install-results.json   # Claude Cowork, Mac or Windows
   python  scripts/install_check.py --json install-results.json                 # Copilot Cowork on Windows (hosted)
   ```

   `--route` defaults to `hosted`, which needs the pinned supergateway, so a
   Claude Cowork install checked without the flag reports
   `FAIL supergateway installed` and writes a file with `"clean": false` -
   a record of a failing install that never failed. The root-level filename is
   gitignored so a private run never lands by accident.
2. Read it. The `host` block names your OS and Python. The checker has already
   replaced your Cowork folder path with `<config-root>` and your home directory
   with `<home>` wherever either appeared, because the file is written to be
   committed. Confirm that with a glance; `scripts/public_scan.py` will refuse
   the file if a real path survived.
3. Save it here as `install-<platform>-<yyyy-mm-dd>.json`, for example
   `install-macos-2026-09-15.json`, and open a pull request.

A file with `"clean": false` is welcome. A failing check on a real machine is a
more useful contribution than a passing one edited into shape, and the
`detail` field on each failure is the start of the fix.
