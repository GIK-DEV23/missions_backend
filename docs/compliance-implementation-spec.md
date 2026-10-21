# Compliance Implementation Specification

*Created: 2026-10-20*  
*Status: Pending Implementation*

This document specifies the backend compliance features required to support GDPR/CCPA/DPA compliance for the GIK Souls App. These endpoints complement the mobile app's local compliance features (DeletionLedger, ConsentRecords, DataExport).

---

## Overview

| Feature | Mobile Status | Backend Status |
|---------|--------------|----------------|
| Consent tracking on souls | ✅ Exists (`consent_given` field) | ✅ Exists |
| Account deletion | ✅ Done (`delete_account_screen.dart`) | ✅ Exists (`DELETE /users/me/`) |
| Deletion audit ledger | ✅ Done (local SQLite `DeletionLedger`) | ❌ **Pending** |
| Consent audit trail | ✅ Done (local SQLite `ConsentRecords`) | ❌ **Pending** |
| Data export | ✅ Done (local `DataExportService`) | ❌ **Pending** |
| Consent sync to server | ❌ Not implemented | ❌ **Pending** |

---

## 1. Data Export Endpoint

### `GET /api/users/me/export/`

Returns all personal data associated with the authenticated user as a JSON download.

**Response:** `200 OK` with `Content-Disposition: attachment; filename="gik-data-export-{user_id}-{date}.json"`

```json
{
  "export_metadata": {
    "exported_at": "2026-10-20T08:00:00Z",
    "user_id": "uuid",
    "format_version": "1.0"
  },
  "account": {
    "id": "uuid",
    "email": "user@example.com",
    "username": "username",
    "first_name": "John",
    "last_name": "Doe",
    "phone_number": "+254...",
    "created_at": "2026-01-01T00:00:00Z",
    "roles": ["missioner"]
  },
  "souls": [
    {
      "id": "uuid",
      "name": "...",
      "phone_number": "...",
      "consent_given": true,
      "consent_recorded_at": "...",
      "created_at": "...",
      "check_ins": [...],
      "co_carers": [...]
    }
  ],
  "testimonies": [...],
  "miracles": [...],
  "mission_registrations": [...],
  "audit_log_summary": {
    "total_actions": 150,
    "first_action": "2026-01-01T00:00:00Z",
    "last_action": "2026-10-20T07:00:00Z"
  }
}
```

**Implementation notes:**
- Include all souls created by the user
- Include all testimonies/miracles submitted by the user
- Include mission registrations
- Include summary of audit log (not full log for size)
- Exclude: other users' data, system internals

---

## 2. Deletion Audit Ledger Endpoint

### `POST /api/audit/deletion-records/`

Receives deletion audit records from mobile clients after account deletion.

**Request:**
```json
{
  "records": [
    {
      "data_type": "soul",
      "item_identifier": "uuid",
      "description": "Soul record: John Doe",
      "trigger": "account_deletion",
      "deleted_at": "2026-10-20T08:00:00Z",
      "data_hash": "sha256...",
      "record_count": 1
    }
  ]
}
```

**Data types:** `soul`, `check_in`, `testimony`, `miracle`, `mission_registration`, `personal_mission`, `preference`, `consent_record`

**Triggers:** `account_deletion`, `user_action`, `retention_expiry`, `server_sync`, `demo_cleanup`

**Response:** `201 Created`
```json
{
  "received": 5,
  "stored": 5
}
```

**Implementation notes:**
- Store in `DeletionAuditLog` model
- Link to user (anonymized after account deletion)
- Used for compliance audits / right-to-erasure proof

### `GET /api/audit/deletion-records/`

Returns deletion records for the authenticated user (or admin query).

**Query params:**
- `user_id` (admin only)
- `data_type`
- `from_date` / `to_date`

---

## 3. Consent Audit Trail Endpoint

### `POST /api/audit/consent-records/`

Receives consent audit records from mobile clients.

**Request:**
```json
{
  "records": [
    {
      "consent_type": "age_verification",
      "consent_method": "self_attestation",
      "granted_at": "2026-10-20T08:00:00Z",
      "document_version": null,
      "user_age_at_consent": 25,
      "device_hash": "sha256...",
      "is_active": true,
      "withdrawn_at": null
    }
  ]
}
```

**Consent types:**
- `age_verification`
- `parental_consent`
- `terms_of_service`
- `privacy_policy`
- `marketing`
- `data_processing`
- `location_access`
- `photo_access`

**Consent methods:**
- `self_attestation`
- `guardian_verification`
- `checkbox`
- `explicit_action`
- `implicit`

**Response:** `201 Created`

### `GET /api/audit/consent-records/`

Returns consent records for the authenticated user.

---

## 4. Enhanced Account Deletion

The existing `DELETE /users/me/` endpoint should be enhanced:

### Current behavior (keep):
- Anonymizes personal data
- Invalidates refresh tokens
- Deactivates account

### New behavior (add):
1. **Before anonymization:** Generate a deletion manifest listing all data being purged
2. **Create DeletionAuditLog entries** for each data category
3. **Soft-delete related records:**
   - Souls created by user → set `deleted_at`, anonymize names
   - Testimonies/miracles → set `deleted_at` or transfer ownership to "Deleted User"
   - Check-ins → retain for ministry records but anonymize author
4. **Return deletion manifest** in response for mobile to store locally

**Updated response:**
```json
{
  "detail": "Account deleted successfully",
  "deletion_manifest": {
    "deleted_at": "2026-10-20T08:00:00Z",
    "records_affected": {
      "souls": 15,
      "check_ins": 47,
      "testimonies": 3,
      "miracles": 1,
      "mission_registrations": 5
    }
  }
}
```

---

## 5. Database Models

### `DeletionAuditLog`

```python
class DeletionAuditLog(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    user_id = models.UUIDField()  # Retained even after user anonymization
    data_type = models.CharField(max_length=50)
    item_identifier = models.CharField(max_length=255, null=True)
    description = models.TextField(null=True)
    trigger = models.CharField(max_length=50)
    deleted_at = models.DateTimeField()
    data_hash = models.CharField(max_length=64, null=True)  # SHA-256
    record_count = models.IntegerField(default=1)
    received_from_client_at = models.DateTimeField(null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'deletion_audit_log'
        indexes = [
            models.Index(fields=['user_id']),
            models.Index(fields=['data_type']),
            models.Index(fields=['deleted_at']),
        ]
```

### `ConsentAuditLog`

```python
class ConsentAuditLog(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    user_id = models.UUIDField()
    consent_type = models.CharField(max_length=50)
    consent_method = models.CharField(max_length=50)
    granted_at = models.DateTimeField()
    document_version = models.CharField(max_length=50, null=True)
    user_age_at_consent = models.IntegerField(null=True)
    device_hash = models.CharField(max_length=64, null=True)
    is_active = models.BooleanField(default=True)
    withdrawn_at = models.DateTimeField(null=True)
    received_from_client_at = models.DateTimeField(null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'consent_audit_log'
        indexes = [
            models.Index(fields=['user_id']),
            models.Index(fields=['consent_type']),
            models.Index(fields=['granted_at']),
        ]
```

---

## 6. Permissions

| Endpoint | Permission Required |
|----------|---------------------|
| `GET /users/me/export/` | Authenticated (own data only) |
| `POST /audit/deletion-records/` | Authenticated |
| `GET /audit/deletion-records/` | Authenticated (own) or `audit_logs` (admin) |
| `POST /audit/consent-records/` | Authenticated |
| `GET /audit/consent-records/` | Authenticated (own) or `audit_logs` (admin) |

---

## 7. Implementation Checklist

- [ ] Create `DeletionAuditLog` model + migration
- [ ] Create `ConsentAuditLog` model + migration
- [ ] Implement `GET /users/me/export/` endpoint
- [ ] Implement `POST /audit/deletion-records/` endpoint
- [ ] Implement `GET /audit/deletion-records/` endpoint
- [ ] Implement `POST /audit/consent-records/` endpoint
- [ ] Implement `GET /audit/consent-records/` endpoint
- [ ] Enhance `DELETE /users/me/` to create deletion audit entries
- [ ] Add admin UI for viewing audit logs (web-admin)
- [ ] Update mobile app to sync consent/deletion records on connectivity

---

## References

- [Privacy Policy](./privacy-policy.md)
- [Consent and Data Protection](./consent-and-data-protection.md)
- Mobile implementation: `souls_app` branch `feat/compliance-gdpr-ccpa`
