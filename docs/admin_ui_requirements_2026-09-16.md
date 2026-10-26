# Admin UI Requirements - September 16, 2026

## Overview

This document outlines the admin web UI features that need to be added or modified to support recent backend and mobile app changes.

---

## 1. Featured Testimonies Management

### Requirement
Admins need the ability to **select testimonies for featuring** on the mobile app's home screen.

### Current State
- The `Testimony` model has an `is_selected` boolean field
- The `review_status` field tracks approval status (pending, approved, rejected)
- No dedicated UI exists for managing featured testimonies

### Required Admin UI Changes

#### A. Testimony List View Enhancements
- [ ] Add "Featured" column showing `is_selected` status (checkbox or icon)
- [ ] Add filter option: "Show Featured Only"
- [ ] Add bulk action: "Mark as Featured" / "Remove from Featured"
- [ ] Add visual indicator (star icon, highlight color) for featured testimonies

#### B. Testimony Detail/Edit View
- [ ] Add prominent "Feature this Testimony" toggle/checkbox
- [ ] Show warning: "Featured testimonies appear on all users' home screens"
- [ ] Only allow featuring of **approved** testimonies (disable toggle if `review_status != 'approved'`)

#### C. New "Featured Testimonies" Dashboard Section
- [ ] Create dedicated page: `/admin/testimonies/featured/`
- [ ] Show list of currently featured testimonies
- [ ] Allow drag-and-drop reordering (future: add `featured_order` field)
- [ ] Quick actions: Remove from featured, View details
- [ ] Show preview of how testimony appears on mobile home screen

### Business Rules
1. Only **approved** testimonies can be featured
2. If a featured testimony is later rejected, automatically un-feature it
3. Limit featured testimonies to a reasonable number (suggest max 10-20)
4. Consider adding `featured_at` timestamp for sorting by recency

---

## 2. Mission Status Management

### Requirement
Admins need clear visibility and control over mission registration status.

### Current State
- Missions have a `status` field with values: `upcoming`, `registering`, `live`, `complete`, `cancelled`
- The mobile app shows "Open for Registration" cards for missions with `status = 'registering'`

### Required Admin UI Changes

#### A. Mission List View
- [ ] Add color-coded status badges:
  - `upcoming` - Gray
  - `registering` - Green (highlight - action needed from users)
  - `live` - Blue with pulse animation
  - `complete` - Dark gray
  - `cancelled` - Red
- [ ] Add filter by status
- [ ] Add quick status change dropdown in list view

#### B. Mission Detail/Edit View
- [ ] Add status transition buttons with confirmation:
  - "Open Registration" (upcoming → registering)
  - "Close Registration & Go Live" (registering → live)
  - "Mark Complete" (live → complete)
  - "Cancel Mission" (any → cancelled)
- [ ] Show warning when changing status (affects mobile app display)
- [ ] Add status history/audit log

#### C. Registration Management
- [ ] Show registration statistics on mission detail:
  - Places total vs filled
  - Registration open/close dates
  - Days until registration closes
- [ ] Alert when registration is closing soon (< 7 days)
- [ ] Alert when places are almost full (> 80%)

---

## 3. Testimony Review Workflow

### Requirement
Streamline the testimony approval process since only approved testimonies can be featured.

### Required Admin UI Changes

#### A. Review Queue
- [ ] Create dedicated review queue: `/admin/testimonies/pending/`
- [ ] Show testimonies with `review_status = 'pending'`
- [ ] One-click approve/reject buttons
- [ ] Rejection reason input (required when rejecting)
- [ ] Bulk approve/reject actions

#### B. Review Actions
- [ ] After approving, prompt: "Would you like to feature this testimony?"
- [ ] Show content preview before approval
- [ ] Flag potentially sensitive content

---

## 4. Permission Management

### Requirement
New permission `list_featured_testimonies` was added. Admins should be able to manage this.

### Required Admin UI Changes

#### A. Role Management
- [ ] Ensure `list_featured_testimonies` appears in permission list when editing roles
- [ ] Group testimony-related permissions together:
  - `create_testimony`
  - `list_testimonies`
  - `view_testimony`
  - `update_testimony`
  - `delete_testimony`
  - `approve_testimony`
  - `reject_testimony`
  - `list_featured_testimonies` ← NEW

---

## 5. Dashboard Widgets (Nice to Have)

### Suggested Dashboard Additions

#### A. Featured Content Widget
- Count of currently featured testimonies
- Quick link to manage featured content
- Alert if no testimonies are featured

#### B. Registration Status Widget
- Missions currently open for registration
- Upcoming registration deadlines
- Registration fill rates

#### C. Pending Reviews Widget
- Count of testimonies awaiting review
- Count of miracles awaiting review
- Quick link to review queue

---

## Implementation Priority

| Priority | Feature | Effort |
|----------|---------|--------|
| **P0 - Critical** | Featured toggle on Testimony edit | Low |
| **P0 - Critical** | Mission status badges and filters | Low |
| **P1 - High** | Featured testimonies list filter | Low |
| **P1 - High** | Bulk feature/un-feature actions | Medium |
| **P2 - Medium** | Dedicated featured testimonies page | Medium |
| **P2 - Medium** | Testimony review queue | Medium |
| **P3 - Low** | Dashboard widgets | Medium |
| **P3 - Low** | Drag-and-drop featured ordering | High |

---

## Database Considerations

### Potential Schema Changes for Future Features

```python
# Add to Testimony model for ordering featured testimonies
featured_at = models.DateTimeField(null=True, blank=True)
featured_order = models.PositiveIntegerField(null=True, blank=True)

# Auto-set featured_at when is_selected changes to True
def save(self, *args, **kwargs):
    if self.is_selected and not self.featured_at:
        self.featured_at = timezone.now()
    elif not self.is_selected:
        self.featured_at = None
        self.featured_order = None
    super().save(*args, **kwargs)
```

---

## Notes

- The mobile app currently fetches up to 5 featured testimonies
- Featured testimonies should be high-quality, inspiring content
- Consider adding a "Featured Testimonies" section to the public website as well
- Analytics: Track which featured testimonies get the most engagement
