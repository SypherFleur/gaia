# Calendar OAuth Security

Google Calendar requires OAuth. GAIA must never request or store a Google account password.

## Requirements

- state validation;
- minimum scopes;
- encrypted credential reference;
- revoke/disconnect support;
- tenant and user isolation;
- no token logging.

## Permissions

Calendar operations require distinct permissions:

- `calendar.read`
- `calendar.create`
- `calendar.update`
- `calendar.delete`

Read does not imply create. Create requires preview and explicit confirmation. Meaningful updates require confirmation. Delete requires explicit user action.

## Egress

Calendar event creation sends only event-required data. It must not send unrelated plant history, private research, or exact coordinates unless a future explicit workflow needs them and policy permits it.

## Cost

Google Calendar is classified as free/OAuth in the provider registry and remains disabled by default until configured. Any future API-economic change requires provider policy review. Paid fallback is forbidden.

