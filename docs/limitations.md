# Limitations

## Foundation, not a finished accounting application

This release demonstrates the operating foundation. It does not contain a complete public tax, audit, advisory, or bookkeeping product.

## Windows-first implementation

The operated machine is Windows: the jobs are batch files and PowerShell, and the browser bridge drives a Windows profile. The POSIX launchers and the executor's `.sh` form are proven in a Linux container and by CI on macOS, not yet on a Mac someone uses.

## Microsoft 365 and Power Platform assumptions on the hosted route

The Copilot Cowork route assumes access to Microsoft 365 Copilot Cowork, dev tunnels or an equivalent reverse proxy, and a tenant whose policies permit custom connectors. The Claude Cowork route needs none of these and has no tenant surface at all; the Power Automate bridge is useful on either route only with a Power Platform tenant.

## The Claude Cowork route is described from vendor documentation

Its pages were written from Anthropic's published description of where Claude Cowork executes and how it handles memory and skills, and revised as that description changed. Nobody has run them end to end. Two facts they depend on - that shell commands run in a Linux VM rather than on the host, and that local MCP servers run only in a local desktop session - are the vendor's statements, not this repository's measurements.

## Human approval is necessary but not sufficient

Approval is only useful when the reviewer understands the proposed action. The executor cannot determine whether a person read the batch file carefully.

## Memory can preserve a wrong conclusion

The system supports correction, supersession, and retirement, but it cannot determine professional truth autonomously. A plausible lesson can still encode coincidence or a misunderstood failure.

## Behavioral verification is incomplete

Only a small subset of routed rules has a behavioral verdict. The presence of the verification harness should not be confused with comprehensive coverage.

## No universal enforcement

Automated checks remain blind to direct session behavior. The repository therefore reports zero rules fully enforced across every behavior surface.

## Discontinuous history before v0.3.0

Through v0.3.0 the public repository was rebuilt as one commit on each publication. That protected against disclosure through historical commits, and it means the history before the v0.3.0 tag is a series of unrelated roots rather than a lineage: a branch cut before it will not rebase onto `main`. From v0.3.0 the history is conventional and pull requests merge directly.

## Upstream dependencies

The browser and filesystem bridges depend on upstream MCP packages. Changes in those packages can change behavior outside this repository's tests.

## No professional assurance

This repository does not provide audit, tax, accounting, legal, security, or compliance assurance. Applied use requires the organization's normal review and approval processes.
