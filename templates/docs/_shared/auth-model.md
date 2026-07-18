# Auth Model

> **How this gets filled:** `/onboard-repo` pre-fills what it can ground in the repo (scheme from the auth dep, where it's enforced, client storage) with a cited basis, and leaves `<!-- TODO: human -->` for the rest (TTLs, rotation, recovery). Confirm the filled values; answer the TODOs.

<!-- TODO: This describes authentication and authorization across the whole system.
     It lives in `docs/_shared/` because auth spans every repo: the backend issues,
     the clients store, and permissions are enforced at the API boundary. The examples
     below use a token/JWT flow — replace with your real scheme (session cookies, opaque
     tokens, OAuth, etc.). -->

## Token type & lifecycle

The backend issues a credential on successful login; clients send it on every request; the
backend verifies it and authorizes each operation at the API boundary.

<!-- TODO: Fill in the real lifecycle. Common example shown: a signed JWT. -->

- **Scheme:** <!-- TODO: e.g. signed JWT / opaque token / session cookie / OAuth -->
- **Issued by:** <!-- TODO: backend endpoint/operation, e.g. `login` / `refreshToken` -->
- **Signing / validation:** <!-- TODO: algorithm and where the secret/key lives (JWT), or the session store (cookies) -->
- **Claims / session data:** <!-- TODO: e.g. `sub` (user id), `role`, `iat`, `exp` -->
- **Access TTL:** <!-- TODO: e.g. 15m / 24h -->
- **Refresh / renewal:** <!-- TODO: refresh flow? rotation? revocation/blocklist? -->
- **Sent as:** <!-- TODO: `Authorization: Bearer <token>` header, or cookie — per client below -->

## Multi-factor authentication (optional)

<!-- TODO: If you use MFA/2FA, describe it here; otherwise delete this section.
     Common example: TOTP via an authenticator app. -->

- **Type:** <!-- TODO: e.g. TOTP (authenticator app) / SMS / WebAuthn -->
- **Enrollment:** <!-- TODO: generate secret → show QR/otpauth URL → verify first code → store -->
- **Secret storage:** <!-- TODO: where the per-user MFA secret is stored (encrypted?) -->
- **Login step:** <!-- TODO: after password, require a valid code before issuing the full credential -->
- **Recovery:** <!-- TODO: backup codes? admin reset? -->

## Where credentials are stored (per client)

The backend **issues** credentials; each client stores them differently.

<!-- TODO: Replace the example rows with your real clients and storage mechanisms. -->

| Client | Storage mechanism | Notes |
|---|---|---|
| Backend | issues, does not store client-side | Signs & verifies; may keep a refresh/revocation store <!-- TODO --> |
| Web client _(example)_ | cookie or web storage | <!-- TODO: name; `Secure`/`SameSite`/`HttpOnly`, expiry, domain per tier --> |
| Mobile/other _(example)_ | platform secure storage | <!-- TODO: key name; prefer secure/keychain storage for sensitive tokens --> |

<!-- TODO: Note any XSS/CSRF considerations for the cookie approach, and whether a mobile
     token should live in secure/keychain storage. -->

## Where permissions are enforced

Authorization is enforced **at the API boundary**, not in the clients. Clients may hide UI
for unavailable actions, but the backend is the gate.

<!-- TODO: Fill in specifics — your framework's authorization layer (middleware, permission
     classes, a policy/rules module, a gateway, etc.). -->

- **Rules location:** <!-- TODO: path to the authorization layer in the backend -->
- **Default policy:** <!-- TODO: deny-by-default recommended; list public exceptions -->
- **Role model:** <!-- TODO: the roles that exist and what each can do -->

| Rule | Meaning | Applied to |
|---|---|---|
| `isAuthenticated` <!-- example --> | Valid, unexpired credential present | Most operations |
| `isAdmin` <!-- example --> | Requester has the admin role | Admin-only operations |
| `isOwner` <!-- example --> | Requester owns the target resource | Per-resource mutations |
| <!-- TODO --> | | |

See [`api-contract.md`](./api-contract.md) for how rules map onto specific operations, and
[`env-matrix.md`](./env-matrix.md) for per-tier cookie domains/endpoints.
