# Backend Changes - September 16, 2026

## Overview

This document outlines the backend changes made to support new features in the mobile app, specifically around mission registration and featured testimonies.

---

## 1. Featured Testimonies Endpoint

### Change
Added a new API endpoint `GET /api/testimonies/featured/` that returns admin-selected testimonies for display on the home screen.

### Justification
The home screen "Testimony Highlights" section was previously fetching the user's own testimonies or all approved testimonies. The business requirement is to show **curated testimonies** that admins have specifically selected for public display - inspirational stories that encourage all users.

### Technical Details

**File:** `api/testimonies/api.py`
```python
@router.get(
    "/featured/",
    response={200: List[schemas.TestimonyOutSchema], 400: DetailOut},
    auth=jwt_auth
)
@require_permission("list_featured_testimonies")
def featured_testimonies_list_api(request, limit: int = 5):
    """
    Get testimonies that have been selected by admins for featuring on the home screen.
    These are public testimonies that have been approved and marked as selected.
    """
    testimonies = selectors.featured_testimonies_list(limit=limit)
    return 200, [schemas.TestimonyOutSchema(**t.to_dict(request)) for t in testimonies]
```

**File:** `api/testimonies/selectors.py`
```python
def featured_testimonies_list(limit: int = 5):
    """
    Get testimonies that have been selected by admins for featuring.
    These are public testimonies that are both:
    - is_selected=True (admin selected)
    - review_status='approved' (approved for publication)
    """
    return Testimony.objects.select_related('soul', 'user', 'mission').filter(
        is_selected=True,
        review_status=ReviewStatus.APPROVED,
    ).order_by('-updated_at', '-created_at')[:limit]
```

### Route Ordering
The `/featured/` route was placed **before** the `/{testimony_id}/` route to ensure proper matching. Without this ordering, "featured" would be interpreted as a testimony ID, causing a 422 validation error.

---

## 2. New Permission: `list_featured_testimonies`

### Change
Added `list_featured_testimonies` permission to the permissions system.

### Justification
The featured testimonies endpoint needs access control. All authenticated users (missioners, staff, execs) should be able to view featured testimonies on their home screen.

### Technical Details

**File:** `api/authentication/permissions_list.py`

Added to:
- `ALL_PERMISSIONS` - Master list of all permissions
- `MISSIONER_PERMISSIONS` - Regular app users can view featured testimonies
- `EXEC_PERMISSIONS` - Executive users can view featured testimonies

Staff and Admin inherit from `MISSIONER_PERMISSIONS`, so they automatically get this permission.

---

## 3. Mission Status: `REGISTERING`

### Change
Ensured the `REGISTERING` status is properly defined in the mission status enum.

### Justification
The mobile app filters missions by status to show "Open for Registration" cards on the home screen. The `registering` status indicates missions that are accepting participant sign-ups.

### Technical Details

**File:** `api/missions/constants.py`
```python
class MissionStatus(models.TextChoices):
    UPCOMING = 'upcoming', _('Upcoming')
    REGISTERING = 'registering', _('Registering')
    LIVE = 'live', _('Live')
    COMPLETE = 'complete', _('Complete')
    CANCELLED = 'cancelled', _('Cancelled')
```

**File:** `api/missions/schemas.py`
```python
class MissionStatus(str, Enum):
    UPCOMING = 'upcoming'
    REGISTERING = 'registering'
    LIVE = 'live'
    COMPLETE = 'complete'
    CANCELLED = 'cancelled'
```

---

## 4. Validation Error Handler Fix

### Change
Fixed the validation error handler to call `exc.errors()` as a method instead of accessing it as a property.

### Technical Details

**File:** `api/project/api.py`
```python
@api.exception_handler(ValidationError)
def validation_errors(request: HttpRequest, exc: Union[ValidationError, str]) -> HttpResponse:
    """Customize validation error"""
    if isinstance(exc, str):
        response = {"detail": exc}
    else:
        response = {"detail": exc.errors()}  # Fixed: was exc.errors (missing parentheses)

    return api.create_response(request, response, status=400)
```

---

## Summary of Modified Files

| File | Change |
|------|--------|
| `api/testimonies/api.py` | Added `/featured/` endpoint, fixed route ordering |
| `api/testimonies/selectors.py` | Added `featured_testimonies_list()` selector |
| `api/authentication/permissions_list.py` | Added `list_featured_testimonies` permission |
| `api/missions/constants.py` | Confirmed `REGISTERING` status exists |
| `api/missions/schemas.py` | Confirmed `REGISTERING` status in schema enum |
| `api/project/api.py` | Fixed `exc.errors()` method call |

---

## Testing

1. **Featured Testimonies Endpoint**
   ```bash
   curl -H "Authorization: Bearer <token>" http://localhost:9050/api/testimonies/featured/
   ```
   Should return testimonies where `is_selected=True` and `review_status='approved'`

2. **Missions with Registering Status**
   ```bash
   curl -H "Authorization: Bearer <token>" http://localhost:9050/api/missions/
   ```
   Should include missions with `status: "registering"`

---

## Rollback Plan

If issues arise:
1. Remove the `/featured/` endpoint from `api/testimonies/api.py`
2. Remove `featured_testimonies_list` from `api/testimonies/selectors.py`
3. Remove `list_featured_testimonies` from permission lists
4. Rebuild and redeploy the backend container
