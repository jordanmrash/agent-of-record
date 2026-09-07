#!/usr/bin/env python3
"""
bridge_policy_selftest.py - prove the restart authorisation refuses as often
as it permits.

An authorisation that only ever says yes is not a policy, it is a rubber stamp.
Half these cases assert REFUSE and NOACTION; the negative controls matter more
than the positive ones, because the failure mode being guarded against is an
unnecessary restart that takes working bridges off the air.

Run:  python bridge_policy_selftest.py
Exit: 0 all cases passed, 1 otherwise
"""

import sys

from bridge_policy import decide, parse_state

results = []


def check(name, state, expect_action, expect_scripts=None):
    d = decide(state)
    ok = d["action"] == expect_action
    if ok and expect_scripts is not None:
        ok = d["scripts"] == expect_scripts
    results.append((name, ok))
    print("%-58s %s%s" % (name, "PASS" if ok else "FAIL",
                          "" if ok else "  <- got %s %s" % (d["action"], d["scripts"])))


def up(*ports):
    return {p: (p in ports) for p in ("8931", "8932", "8933")}


def main():
    # --- the do-nothing case, which must be the common one -----------------
    check("all three healthy -> NOACTION",
          up("8931", "8932", "8933"), "NOACTION", [])

    # --- refusals: the whole point of bounding the authorisation -----------
    check("8933 down -> REFUSE (cannot restart executor from executor)",
          up("8931", "8932"), "REFUSE", [])
    check("8933 down + 8931 down -> REFUSE, not a partial restart",
          up("8932"), "REFUSE", [])
    check("8933 down + 8932 down -> REFUSE",
          up("8931"), "REFUSE", [])
    check("all three down -> REFUSE (ports would go Private)",
          up(), "REFUSE", [])

    # --- the narrow permissions -------------------------------------------
    check("8931 down only -> restart 8931 alone",
          up("8932", "8933"), "RESTART", ["bridge-restart-8931.bat"])
    check("8932 down only -> restart 8932 alone",
          up("8931", "8933"), "RESTART", ["bridge-restart-8932.bat"])
    check("8931+8932 down, 8933 up -> restart both, 8933 verifies",
          up("8933"), "RESTART",
          ["bridge-restart-8931.bat", "bridge-restart-8932.bat"])

    # --- restart-all must never be proposed by this policy -----------------
    allstates = [up(), up("8931"), up("8932"), up("8933"),
                 up("8931", "8932"), up("8931", "8933"),
                 up("8932", "8933"), up("8931", "8932", "8933")]
    never = all("bridge-restart-all.bat" not in decide(s)["scripts"]
                for s in allstates)
    results.append(("restart-all is NEVER proposed, in any of the 8 states", never))
    print("%-58s %s" % ("restart-all is NEVER proposed, in any of the 8 states",
                        "PASS" if never else "FAIL"))

    # --- a missing measurement must not read as healthy --------------------
    d = decide({"8931": True, "8932": True})
    ok = d["action"] == "ERROR"
    results.append(("a missing measurement is ERROR, never NOACTION", ok))
    print("%-58s %s%s" % ("a missing measurement is ERROR, never NOACTION",
                          "PASS" if ok else "FAIL",
                          "" if ok else "  <- got " + d["action"]))

    # --- input parsing ------------------------------------------------------
    ok = parse_state("8931=up,8932=down,8933=up") == {
        "8931": True, "8932": False, "8933": True}
    results.append(("parse_state reads a state string correctly", ok))
    print("%-58s %s" % ("parse_state reads a state string correctly",
                        "PASS" if ok else "FAIL"))

    for bad in ("8931=maybe,8932=up,8933=up", "9999=up", "8931"):
        try:
            parse_state(bad)
            good = False
        except ValueError:
            good = True
        results.append(("bad input %r is rejected" % bad, good))
        print("%-58s %s" % ("bad input %r is rejected" % bad,
                            "PASS" if good else "FAIL"))

    failed = [r for r in results if not r[1]]
    print("\n%d/%d cases passed" % (len(results) - len(failed), len(results)))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
