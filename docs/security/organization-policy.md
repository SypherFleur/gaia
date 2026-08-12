# Organization Policy

`OrganizationPolicy` centralizes deployment-specific behavior:

- deployment mode;
- default location precision;
- retention policy;
- telemetry policy;
- model policy;
- tool/provider policy;
- egress policy;
- export policy;
- data-sharing policy.

Model policy supports allowed model providers, allowed models, remote-model denial, and local-model requirements. Tool policy supports provider allowlists.

Policy changes require explicit organization policy permission. Feature code should not scatter organization-specific logic through individual modules.

