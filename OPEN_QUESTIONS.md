# OPEN QUESTIONS

Protocol Two defaults are treated as decisions and are not repeated as questions.

## Active Questions

## Q1. First Alpha Domain and Deployment Surface

What domain or subdomain should the first alpha use?

Why this matters: authentication callbacks, Google OAuth redirect URIs, CORS, cookies, deployment documentation, and future public/invite-only routing depend on the deployment surface.

## Q2. First Alpha Access Model

Should the first alpha be private, invite-only, or public?

Why this matters: onboarding flow, rate limits, abuse controls, default workspace creation, telemetry, and support expectations change materially.

## Q10. Paid Provider Approval Authority

Who may approve enabling any paid provider in the future?

Why this matters: the Cost Firewall can technically block paid usage by default, but manual override governance needs a named role or approval policy before any paid integration exists.

## Resolved for Commit 2

## Q3. Authentication Provider

Resolved by D037 and D038: no commercial provider is selected in Phase 1; GAIA uses a provider-neutral authentication boundary plus safe development identity.

## Q4. Target Hardware for Local Multimodal Inference

Resolved by D047 and D048 for current development: use existing lightweight Ollama/LLaVA where practical, mock heavily, and do not make CI depend on a GPU model. Nemotron remains a future benchmark candidate.

Future minimum supported hardware remains a product/deployment question, but it does not block Commit 2.

## Q5. Existing Cillian/GreensWrld Schemas

Resolved by D035 and D036: GAIA's canonical core schema is standalone and must not depend on GreensWrld. Future integration uses an adapter/mapping layer.

## Q6. Institutional Telemetry Policy

Resolved by D042, D043, and D044: collect minimum necessary operational telemetry for Public; exclude private content/coordinates/media/datasets from analytics by default; institution/sovereign telemetry must support disablement, local-only operation, and administrator configuration.

## Q7. Personal Data Retention and Deletion Defaults

Resolved by D039, D040, and D041: active data is retained while account/workspace exists; user-requested deletion immediately makes data inaccessible and hard-deletes eligible personal content within 30 days; schema records retention metadata.

## Q8. Minors and Student Users

Resolved by D052: do not design a special student/minor workflow yet; GAIA Public should not intentionally target children in the MVP.

## Q9. Geographic Privacy Default

Resolved by D045 and D046: ordinary consumer/public accounts default to `privacy_precision = "approximate"` and exact coordinates require authorized use.
