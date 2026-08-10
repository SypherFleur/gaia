# OPEN QUESTIONS

Only unresolved, architecture-impacting questions are listed here. Protocol Two defaults are treated as decisions and are not repeated as questions.

## Q1. First Alpha Domain and Deployment Surface

What domain or subdomain should the first alpha use?

Why this matters: authentication callbacks, Google OAuth redirect URIs, CORS, cookies, deployment documentation, and future public/invite-only routing depend on the deployment surface.

## Q2. First Alpha Access Model

Should the first alpha be private, invite-only, or public?

Why this matters: onboarding flow, rate limits, abuse controls, default workspace creation, telemetry, and support expectations change materially.

## Q3. Authentication Provider

Which authentication provider, if any, is already used by Cillian Industries and should GAIA integrate with first?

Why this matters: GAIA authorization is internal, but identity provider choice affects user IDs, OAuth/OIDC setup, local development, institution SSO, and migration paths.

## Q4. Target Hardware for Local Multimodal Inference

Beyond this development machine, what exact minimum hardware should GAIA Local support for image reasoning?

Why this matters: model adapter defaults, quantization strategy, local-provider test fixtures, UX expectations, and sovereign deployment guidance depend on target hardware.

## Q5. Existing Cillian/GreensWrld Schemas

Are there existing plant, observation, action, outcome, user, organization, or GreensWrld schemas that GAIA must preserve or map to?

Why this matters: core domain models and migration boundaries should avoid rework if existing production data shapes already exist.

## Q6. Institutional Telemetry Policy

What telemetry may Cillian collect from institution and sovereign deployments by default?

Why this matters: observability, audit exports, support diagnostics, privacy defaults, and network egress policy must be designed before remote logging or analytics exists.

## Q7. Personal Data Retention and Deletion Defaults

What deletion and retention expectation should personal users receive at launch?

Why this matters: schema design, attachment lifecycle, provenance exports, backups, account deletion, and outcome graph permissions all depend on retention semantics.

## Q8. Minors and Student Users

Are minors or students expected to use university, school, extension, or public deployments?

Why this matters: onboarding, consent, privacy, data retention, content safety, research exports, and institutional policy controls may need stricter defaults.

## Q9. Geographic Privacy Default

What should the initial geographic privacy default be: exact, 100m, 1km, county, or another policy?

Why this matters: location schema supports precision, but UI defaults, shared outputs, evidence bundles, and map behavior need a default before user-facing release.

## Q10. Paid Provider Approval Authority

Who may approve enabling any paid provider in the future?

Why this matters: the Cost Firewall can technically block paid usage by default, but manual override governance needs a named role or approval policy before any paid integration exists.

