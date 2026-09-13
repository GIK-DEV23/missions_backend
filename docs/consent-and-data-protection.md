# Consent and Data Protection Documentation

This document describes the consent mechanisms and data protection measures implemented in the GIK Souls App backend.

## Consent Fields on Soul Records

Each `Soul` record includes the following consent-related fields:

| Field | Type | Description |
|-------|------|-------------|
| `consent_given` | boolean | Whether the individual consented to their data being stored for follow-up |
| `consent_recorded_at` | datetime | When consent was recorded (auto-set when `consent_given` flips to true) |
| `do_not_contact` | boolean | Individual has requested not to be contacted |
| `do_not_contact_at` | datetime | When do-not-contact was recorded |

## App-Side Consent Copy

When recording a new soul, the app should display the following consent prompt:

> **Consent for Follow-Up**
>
> "Do you give us permission to save your contact information so someone from the ministry can follow up with you about your faith journey?"
>
> - [x] Yes, I consent
> - [ ] No, I do not consent
>
> For minors (under 18), consent should be obtained from a parent or guardian.

The checkbox state maps to the `consent_given` field. If the individual declines, the soul can still be recorded (with `consent_given=false`) but should be flagged in the UI for attention.

## Anonymous Submissions

Testimonies, miracles, and highlight moments can be submitted without authentication via the `POST /testimonies/anonymous/` endpoint.

**Rate limiting**: Anonymous submissions are rate-limited by a hashed device token to prevent spam. The device token is hashed using SHA-256 before storage — the original token is never stored.

**What is stored**: Only the hash of the device token, submission count, and window timestamps. The hash cannot be reversed to identify the device or user.

**Privacy note for anonymous submissions**:
> "Your testimony will be submitted anonymously. We store a non-identifying technical token solely to prevent spam — it is never linked to your identity or shown to anyone."

## Data Protection Act (DPA) Compliance

The backend supports Kenya's Data Protection Act, 2019 through:

1. **Purpose limitation**: Data is collected only for follow-up and ministry coordination
2. **Consent tracking**: Explicit consent fields on soul records
3. **Right to erasure**: Soul records can be deleted or merged (soft-deleted via `deleted_at`)
4. **Audit logging**: All modifications are logged with user attribution
5. **Access controls**: Role-based permissions limit who can see what data
6. **Data minimization**: Only necessary fields are collected

## User Stats Endpoint

The `/users/me/stats/` endpoint includes `souls_without_consent_count` to help users identify souls needing consent follow-up.

## References

- [Privacy Policy](./privacy-policy.md) — Full privacy policy document
- [Pagination Contract](./pagination.md) — API response formats
