# Pagination Contract

All list endpoints in this API return paginated responses with a consistent shape.

## Response Shape

```json
{
  "count": 142,
  "page": 1,
  "page_size": 50,
  "last_page": 3,
  "data": [...]
}
```

| Field | Type | Description |
|-------|------|-------------|
| `count` | int | Total number of items matching the query |
| `page` | int | Current page number (1-indexed) |
| `page_size` | int | Number of items per page |
| `last_page` | int | Total number of pages |
| `data` | array | Array of items for the current page |

## Request Parameters

All list endpoints accept these query parameters:

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `page` | int | 1 | Page number (must be ≥ 1) |
| `page_size` | int | 50 | Items per page (max 1000) |

## Error Responses

| Condition | Status | Response |
|-----------|--------|----------|
| `page ≤ 0` | 422 | Pydantic validation error |
| `page > last_page` | 400 | `{"detail": "Invalid page number"}` |

## Empty Results

When a filter matches no items, the response is still 200 OK:

```json
{
  "count": 0,
  "page": 1,
  "page_size": 50,
  "last_page": 1,
  "data": []
}
```

Note: `last_page` is always at least 1, even for empty results.
