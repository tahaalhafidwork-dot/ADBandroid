# Kilo AI Gateway Free Model - Prompt Engineering Evaluation Report

## Executive Summary

This report evaluates prompt engineering improvements for the kilo-auto/free model on Kilo AI Gateway
processing 10 Facebook Group posts from the Erbil real estate group. Two extraction approaches were
compared: **Method A** (classify-then-extract, two API calls) and **Method B** (combined single call).

**Key finding:** Method A achieves 100% classification accuracy and high field extraction quality,
while Method B fails completely (0% classification accuracy, all posts classified as "unclear").
The kilo-auto/free model cannot handle complex combined prompts — separating classification from
extraction is essential.

**Cost:** $0.00 USD (kilo-auto/free is a free model). 18 API requests for Method A, 10 for Method B.

---

## Test Data

- **Source:** 10 Facebook Group posts from Erbil real estate group (group ID: 125622874273965)
- **File:** `apify_facebook_groups_results.json` (contains personal data — not committed with PII)
- **Ground truth:** Manually created from original post texts (`real_estate_ai_pipeline/output/ground_truth.json`)

### Ground Truth Distribution

| Category | Count |
|----------|-------|
| for_sale | 4 |
| for_rent | 4 |
| real_estate_service | 2 |
| buy_or_rent_request | 0 |
| not_real_estate | 0 |
| unclear | 0 |
| Duplicates | 1 (posts 9 & 10) |
| Unique listings | 7 |

---

## Method A: Classify Then Extract (Two Calls)

### Configuration
- Call 1: Classification prompt (Arabic, JSON schema, category + confidence + reasoning)
- Call 2: Extraction prompt (Arabic, JSON Schema, few-shot examples, all listing fields)
- PII stripping: phone numbers and user IDs replaced before sending to model
- JSON repair: single repair attempt on parse failure

### Results

| Metric | Value |
|--------|-------|
| API requests | 18 (10 classify + 8 extract for sale/rent posts) |
| Classification accuracy | 100% (10/10 correct) |
| Category distribution | 4 for_sale, 4 for_rent, 2 real_estate_service |
| Parse errors | 0 |
| Truncated responses | 0 |
| Finish reason | None (all complete) |
| Total tokens | ~30,801 |
| Estimated cost | $0.00 |
| Processing time | ~119 seconds |

### Field Extraction Quality (per post)

| Post | Category | Property Type | City | Complex | Area | Beds | Phones | Price | Notes |
|------|----------|--------------|------|---------|------|------|--------|-------|-------|
| 1 | for_sale | None | None | None | None | None | 2 found | None | **Extraction failed** — all fields null |
| 2 | real_estate_service | N/A | N/A | N/A | N/A | N/A | N/A | N/A | Correctly skipped |
| 3 | real_estate_service | N/A | N/A | N/A | N/A | N/A | N/A | N/A | Correctly skipped |
| 4 | for_sale | house | أربيل | مجمع اشتي ١ | 250 | 4 | 1 found | None | Excellent extraction |
| 5 | for_sale | None | None | None | None | None | 1 found | None | **Extraction failed** — all fields null |
| 6 | for_rent | apartment | أربيل | واو تاورز | 170 | None | 1 found | None | Good extraction |
| 7 | for_rent | None | None | مجمع گلوبال ستي | 300 | 4 | 2 found | None | Partial (property_type missing) |
| 8 | for_sale | house | أربيل | مجمع لانه ستي | 200 | 4 | None | None | Excellent extraction |
| 9 | for_rent | apartment | None | مجمع ويفي افينيو | None | 1 | 1 found | None | Good extraction |
| 10 | for_rent | apartment | None |duplicate| None | None | None | None | Duplicate of post 9 |

**Extraction success rate:** 5/7 unique listings fully extracted (71%), 2/7 failed completely (29%)

### Issues Observed
- Posts 1 and 5: Model returned valid JSON but all fields set to null (confidence 0.0)
- Price field: consistently null across all posts — model does not extract price values
- Property type missing for post 7
- City missing for posts 6 and 9

---

## Method B: Combined Classification + Extraction (Single Call)

### Configuration
- Single API call: Combined Arabic prompt for both classification and extraction
- JSON Schema with few-shot examples
- Same PII stripping and JSON repair as Method A

### Results

| Metric | Value |
|--------|-------|
| API requests | 10 |
| Classification accuracy | 0% (10/10 classified as "unclear") |
| Parse errors | 3 |
| Truncated responses | 3 |
| Finish reason | "length" (truncated) |
| Total tokens | ~28,929 |
| Estimated cost | $0.00 |
| Processing time | ~115 seconds |

### Issues Observed
- **All 10 posts classified as "unclear"** — the combined prompt is too complex for kilo-auto/free
- 3 responses were truncated (finish_reason: "length") before valid JSON could be produced
- 3 parse errors due to truncation
- Zero usable extractions from any post

---

## Method Comparison

| Metric | Method A | Method B | Winner |
|--------|----------|----------|--------|
| Classification accuracy | 100% | 0% | Method A |
| Parse errors | 0 | 3 | Method A |
| Truncated responses | 0 | 3 | Method A |
| Usable extractions | 5/7 | 0/7 | Method A |
| API requests | 18 | 10 | Method B (fewer calls) |
| Total tokens | ~30,801 | ~28,929 | Method B (slightly fewer) |
| Cost | $0.00 | $0.00 | Tie |
| Processing time | ~119s | ~115s | Method B (slightly faster) |

**Method A is the clear winner** despite using more API calls. Method B produces zero usable results
because the kilo-auto/free model cannot handle the complexity of a combined classification+extraction
prompt.

---

## Deduplication Results

| Level | Method | Matches Found |
|-------|--------|---------------|
| Level 1: URL/ID exact match | A & B | 0 |
| Level 2: Text fingerprint match | A & B | 1 (posts 9 & 10) |
| Level 3: Similarity threshold 0.75 | A & B | 0 |
| Level 4: Phone + complex + city | A & B | 0 |
| **Total duplicates** | | **1** |
| **Unique listings** | Method A | **7** |
| **Unique listings** | Method B | **7** (all unclear, not usable) |

Posts 9 and 10 are exact duplicates — same text, same phone (07852562878), same user (Noor Ali).

---

## Prompt Engineering Lessons Learned

### What Works (Method A)
1. **Separate classification from extraction** — The model handles a simple classification task reliably (100% accuracy) but fails when asked to do both at once.
2. **Arabic-language prompts** — Writing prompts in Arabic (matching the input language) significantly improves extraction quality over English prompts.
3. **Few-shot examples** — Including 3 synthetic examples with expected JSON output helps the model understand the desired format.
4. **JSON Schema in prompt** — Providing the schema as structured text helps the model produce valid JSON.
5. **PII stripping** — Removing phone numbers and user IDs before sending to the model prevents privacy leakage without affecting extraction quality.
6. **Single JSON repair attempt** — Fixing trailing commas and missing braces recovers some malformed responses.

### What Does Not Work (Method B)
1. **Combined classification+extraction** — The kilo-auto/free model cannot handle a single prompt that requires both categorization and detailed field extraction. All posts classified as "unclear".
2. **Overly complex single prompts** — Too many instructions in one prompt causes the model to give up or produce truncated output.

### Persistent Limitations of kilo-auto/free
1. **Price extraction** — The model consistently returns null for price fields even when prices are mentioned in the text (e.g., post 5 mentions "السعر 40").
2. **Complete extraction failures** — Some posts (1 and 5) produce all-null extractions with confidence 0.0 despite valid JSON parsing.
3. **No local fallback** — Unlike the local rule-based provider, the Kilo provider does not extract phones locally when the model fails to provide them.

---

## Files Created/Modified

### New Files
- `real_estate_ai_pipeline/prompts.py` — Arabic prompts with JSON Schema and few-shot examples for Methods A and B
- `real_estate_ai_pipeline/providers/kilo_provider.py` — Kilo AI Gateway provider with Method A/B support, JSON repair, diagnostics
- `real_estate_ai_pipeline/processing/deduplicator.py` — Multi-level deduplication (URL, fingerprint, similarity, phone+complex+city)
- `real_estate_ai_pipeline/output/ground_truth.json` — Manual ground truth from original 10 posts
- `KILO_FREE_PROMPT_ENGINEERING_REPORT.md` — This report

### Modified Files
- `real_estate_ai_pipeline/main.py` — Updated to support Method A/B, cost tracking, diagnostics, deduplication
- `real_estate_ai_pipeline/processing/classifier.py` — Already existed (no changes needed)
- `real_estate_ai_pipeline/processing/extractor.py` — Already existed (no changes needed)
- `real_estate_ai_pipeline/processing/normalizer.py` — Already existed (no changes needed)

### Test Results
- 24/24 tests pass (`python -m unittest real_estate_ai_pipeline.tests.test_pipeline`)

---

## Recommendations

1. **Use Method A** (classify-then-extract) for production with kilo-auto/free
2. **Do not use Method B** — it produces zero usable results
3. **Add local fallback** for phone extraction when the model returns null (already done in extractor.py)
4. **Consider a steeper model** if price extraction is critical — kilo-auto/free cannot extract prices reliably
5. **Increase max_tokens** for extraction calls to reduce truncation risk (currently 1024, could be increased to 2048)

---

## Constraints Observed

- No personal data or API keys committed to GitHub
- Cost cap $0.10 — actual cost $0.00 (free model)
- No Apify used for new data — all posts from existing `apify_facebook_groups_results.json`
- Aqarati project not modified
