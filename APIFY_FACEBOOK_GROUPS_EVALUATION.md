# Facebook Groups Scraper Evaluation Report

## Test Overview

| Field | Value |
|-------|-------|
| Actor | `apify/facebook-groups-scraper` |
| Target Group | `عقارات أربيل لبيع وشراء وايجار المنازل والأراضي` (Erbil Real Estate for Sale/Rent Houses and Lands) |
| Group ID | `125622874273965` |
| Group URL | `https://www.facebook.com/groups/125622874273965` |
| Run ID | `ycTNWTsTKeF9uAs9l` |
| Dataset ID | `ECAbuiOZk4kXYMOns` |
| Status | SUCCEEDED |
| Posts scraped | 10 |
| Total cost | $0.051 (10 posts + 1 actor start) |
| Cost cap | $0.10 (within limit) |
| Date | 2026-10-20 |

## Results Summary

### Post Volume
- **10 posts** successfully retrieved from the target group
- All posts from the same group (ID `125622874273965`)
- Posts span from `2026-10-20T13:04:21Z` to `2026-10-20T20:26:41Z` (all same day)

### Content Type Breakdown
| Type | Count | Examples |
|------|-------|----------|
| Photo posts | ~5 | Posts 1, 2, 4, 5, 7, 8 (photos) |
| Video posts | 4 | Posts 3, 6, 9, 10 |
| Mixed media | Present | Some posts contain both photos and videos |

### Real Estate Relevance
**All 10 posts are real estate or home-services related:**

| Post | Type | Key Content |
|------|------|-------------|
| 1 | House for sale | 125m² + 25m² garden, 4 bedrooms, Erbil Ashti Complex 1 |
| 2 | Contractor services | General contractor, foundation to structure, installment payment |
| 3 | Gardening/landscaping | Garden design, tree planting, monthly maintenance, Erbil |
| 4 | House for sale | 250m², 4 bedrooms, Erbil Ashti Complex 1, phone: 0773 222 91 42 |
| 5 | House for sale | 110m² agricultural plot, garden, private bathroom |
| 6 | Apartment for rent | VIP furnished, 170m², Wao Towers, 100m street |
| 7 | Apartment for rent | Global City Complex, 300m², 4 bedrooms, unfurnished, phones: 07806833704, 07754701339 |
| 8 | House for sale | 200m² two-story, 4 bedrooms, garden, garage, Erbil Lana City Complex |
| 9 | Apartment for rent | Furnished, 1 bedroom, Wafi Avenue, 100m street, phone: 07852562878 |
| 10 | Apartment for rent | Duplicate of post 9 (same content, same phone) |

### Arabic Text Quality
- All post texts are in **Arabic** with clear real estate terminology:
  - "للبيع" (for sale), "للإيجار" (for rent), "مفروشة" (furnished), "غرف نوم" (bedrooms), "مطبخ" (kitchen), "صالة" (living room), "مساحة" (area/m²), "طابو" (title deed), "صراف" (cash)
- Text is well-structured with bullet points, emojis (🔹, ▪️, 👇, 📍, ￼), and contact phone numbers
- **Readability: Excellent** — native Arabic speakers posting naturally

### Image/Video Links
- Every post includes at least one media attachment (photo thumbnail or video)
- Thumbnails are served from `scontent-*.fbcdn.net` CDN URLs
- Video posts include `permalink_url` pointing to Facebook video pages
- **Media availability: High** — all posts have visual content suitable for a listing platform

### Dates
- All 10 posts are from the same day (2026-10-20), indicating recent, active content
- Timestamps are in ISO 8601 format (UTC)

### Engagement Metrics
- All posts show 0 likes, 0 shares, 0 comments (scraped shortly after posting)
- This is expected for fresh posts in a real estate group

## Assessment for Aqarati

| Criterion | Result | Verdict |
|-----------|--------|---------|
| Post volume | 10 posts per group run | Moderate |
| Arabic quality | Native Arabic, clear real estate terms | Excellent |
| Media (photos/videos) | All posts have attachments | High |
| Contact info | Phone numbers embedded in post text | High |
| Real estate relevance | 10/10 posts are real-estate related | Excellent |
| Location specificity | Erbil, Iraq (specific complexes/streets) | Excellent |
| Recency | All posts from same day | High |
| Cost | $0.051 (within $0.10 cap) | Excellent |
| Duplicate detection | Post 9 and 10 are duplicates | Needs dedup logic |

## Conclusion

The Facebook Groups scraper is **viable for Aqarati's data sourcing needs**. It successfully extracts:

1. Real estate listings in Arabic with clear property details (bedrooms, area, price context, location)
2. Contact phone numbers directly from post text
3. Photo/video media for each listing
4. Timestamps for recency filtering
5. Group context (which Erbil group the listing came from)

**Recommended next steps:**
- Implement Arabic text parsing to extract structured fields (price, bedrooms, area, location, phone)
- Add deduplication (post 9 and 10 were identical)
- Scale to multiple Erbil/Baghdad real estate groups
- Monitor cost per run (~$0.05 per 10 posts)

## Files

- `apify_facebook_groups_results.json` — Raw scraped data (10 posts, clean extraction)
- `parse_groups.py` — Parsing script used to extract key fields
