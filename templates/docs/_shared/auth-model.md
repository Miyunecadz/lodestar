# Auth Model

<!-- TODO: This describes authentication and authorization across the whole system.
     It lives in `docs/_shared/` because auth spans every repo: the backend issues,
     the clients store, and permissions are enforced at the API boundary. -->

## Token type & lifecycle (JWT)

The backend issues a **JWT** on successful login; clients send it on every request; the
backend verifies it and (via graphql-shield) authorizes each operation.

<!-- TODO: Fill in the real lifecycle. -->

- **Issued by:** <!-- TODO: backend mutation, e.g. `login` / `refreshToken` -->
- **Signing:** <!-- TODO: algorithm (e.g. HS256/RS256) and where the secret/key lives -->
- **Claims:** <!-- TODO: e.g. `sub` (user id), `role`, `iat`, `exp` -->
- **Access token TTL:** <!-- TODO: e.g. 15m / 24h -->
- **Refresh:** <!-- TODO: refresh-token flow? rotation? revocation/blocklist? -->
- **Sent as:** <!-- TODO: `Authorization: Bearer <jwt>` header, or cookie — per client below -->

## Two-factor authentication (2FA)

TOTP-based, using **speakeasy** on the backend.

<!-- TODO: Fill in the real flow. -->

- **Type:** TOTP (authenticator app) via `speakeasy`
- **Enrollment:** <!-- TODO: generate secret → show QR/otpauth URL → verify first code → store secret -->
- **Secret storage:** <!-- TODO: where the per-user TOTP secret is stored (encrypted?) -->
- **Login step:** <!-- TODO: after password, require a valid TOTP code before issuing the full JWT -->
- **Recovery:** <!-- TODO: backup codes? admin reset? -->

## Where tokens are stored (per client)

The backend **issues** tokens; each client stores them differently.

| Client | Storage mechanism | Notes |
|---|---|---|
| Backend | issues, does not store client-side | Signs & verifies; may keep a refresh/revocation store <!-- TODO --> |
| Frontend (web) | cookies via `js-cookie` | <!-- TODO: cookie name, `Secure`/`SameSite`/`HttpOnly`, expiry, domain per tier --> |
| Mobile | `@react-native-async-storage/async-storage` | <!-- TODO: key name; consider secure storage for sensitive tokens --> |

<!-- TODO: Note any XSS/CSRF considerations for the cookie approach, and whether the
     mobile token should move to secure/keychain storage. -->

## Where permissions are enforced (graphql-shield)

Authorization is enforced **at the API boundary** with **graphql-shield**, not in the
clients. Clients may hide UI for unavailable actions, but the backend is the gate.

<!-- TODO: Fill in specifics. -->

- **Rules location:** <!-- TODO: path to the shield permissions file -->
- **Default policy:** <!-- TODO: deny-by-default recommended; list public exceptions -->
- **Role model:** <!-- TODO: the roles that exist and what each can do -->

| Rule | Meaning | Applied to |
|---|---|---|
| `isAuthenticated` <!-- example --> | Valid, unexpired JWT present | Most operations |
| `isAdmin` <!-- example --> | JWT `role` claim is admin | Admin-only operations |
| `isOwner` <!-- example --> | Requester owns the target resource | Per-resource mutations |
| <!-- TODO --> | | |

See [`graphql-contract.md`](./graphql-contract.md) for how rules map onto specific
types/fields, and [`env-matrix.md`](./env-matrix.md) for per-tier cookie domains/endpoints.
