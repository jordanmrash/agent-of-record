# Limitations

## Foundation, not a finished accounting application

This release demonstrates the operating foundation. It does not contain a complete public tax, audit, advisory, or bookkeeping product.

## Windows-specific implementation

The local execution layer uses Windows batch files, PowerShell, VS Code tasks, absolute paths, and a Windows browser profile.

## Microsoft 365 and Power Platform assumptions

The design assumes access to Microsoft 365 Copilot Cowork, dev tunnels or an equivalent reverse proxy, Power Automate, and a tenant whose policies permit the configured behavior.

## Human approval is necessary but not sufficient

Approval is only useful when the reviewer understands the proposed action. The executor cannot determine whether a person read the batch file carefully.

## Memory can preserve a wrong conclusion

The system supports correction, supersession, and retirement, but it cannot determine professional truth autonomously. A plausible lesson can still encode coincidence or a misunderstood failure.

## Behavioral verification is incomplete

Only a small subset of routed rules has a behavioral verdict. The presence of the verification harness should not be confused with comprehensive coverage.

## No universal enforcement

Automated checks remain blind to direct session behavior. The repository therefore reports zero rules fully enforced across every behavior surface.

## Snapshot publication model

The public repository is rebuilt as one commit. This protects against disclosure through historical commits but removes conventional public commit history and complicates direct contribution.

## Upstream dependencies

The browser and filesystem bridges depend on upstream MCP packages. Changes in those packages can change behavior outside this repository's tests.

## No professional assurance

This repository does not provide audit, tax, accounting, legal, security, or compliance assurance. Applied use requires the organization's normal review and approval processes.
