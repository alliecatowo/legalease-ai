# Hybrid Search Fix - Summary Report

**Date**: 2025-10-11
**Issue**: Hybrid search was producing the same results as keyword/text search
**Status**: ✅ FIXED

## Root Cause

The hybrid search implementation was using the **fusion score** (which combines BM25 + dense results) as a proxy for the BM25 score during score normalization and boosting. This caused the system to incorrectly boost results, making hybrid search behave almost identically to keyword-only search.

### Specific Problem Location

In `/home/Allie/develop/legalease/backend/app/services/search_service.py`, the original `search_with_query_api` method:

```python
# Line 360 - THE BUG
bm25_scores[point_id] = score  # Using fusion score as BM25 score proxy!
```

This meant:
1. The system executed both BM25 and dense vector searches ✓
2. Qdrant properly fused the results ✓
3. BUT the fusion score was incorrectly used as the "BM25 score" for boosting ✗
4. The normalization logic then boosted results based on fusion scores, not actual BM25 scores ✗
5. This made hybrid search behave like keyword search ✗

## Solution

### 1. Separate BM25 and Dense Searches

Modified `search_with_query_api()` to perform **three separate searches**:

```python
# Step 1: Perform BM25 search independently
bm25_search = self.client.query_points(...)
for point in bm25_search.points:
    bm25_results_map[str(point.id)] = point.score

# Step 2: Perform dense vector search independently
dense_search = self.client.query_points(...)
for point in dense_search.points:
    dense_results_map[str(point.id)] = point.score

# Step 3: Perform hybrid fusion
results = self.client.query_points(
    prefetch=[bm25_prefetch, dense_prefetch],
    query=FusionQuery(fusion=Fusion.RRF)
)
```

### 2. Track Actual Scores

Store both actual BM25 and dense scores in results:

```python
formatted_results.append({
    "id": point_id,
    "score": score,  # Fusion score
    "payload": payload,
    "bm25_score": bm25_results_map.get(point_id, 0.0),  # Actual BM25 score
    "dense_score": dense_results_map.get(point_id, 0.0),  # Actual dense score
})
```

### 3. Use Actual BM25 Scores for Boosting

```python
# Use actual BM25 score for boosting (not fusion score!)
bm25_scores[point_id] = actual_bm25_score
```

### 4. Improved Match Type Detection

Updated match type logic to use actual scores:

```python
if actual_bm25_score > 0 and actual_dense_score > 0:
    # Found by both - determine which ranked it higher
    match_type = "bm25" if actual_bm25_score > actual_dense_score else "semantic"
elif actual_bm25_score > 0:
    match_type = "bm25"  # Only BM25 found this
elif actual_dense_score > 0:
    match_type = "semantic"  # Only dense found this
```

### 5. Enhanced Debug Logging

Added detailed logging to track search statistics:

```python
logger.info(f"BM25 search returned {len(bm25_results_map)} results")
logger.info(f"Dense search returned {len(dense_results_map)} results")
logger.info(f"Result breakdown: {bm25_only_count} BM25-only, "
           f"{dense_only_count} dense-only, {both_count} in both")
```

## Files Modified

1. **`/home/Allie/develop/legalease/backend/app/services/search_service.py`**
   - Modified `search_with_query_api()` method (lines 271-459)
   - Updated `_normalize_and_boost_scores()` debug info (lines 189-196)
   - Updated match type detection in `search()` method (lines 528-548)
   - Added match breakdown statistics (lines 576-610)

2. **`/home/Allie/develop/legalease/backend/app/api/v1/transcriptions.py`**
   - Fixed missing `Field` import (line 9)

## Verification Results

Test query: "software development"

### Hybrid Search (BM25 + Semantic)
- **Match Breakdown**: 1 BM25 match, 4 semantic matches
- **Results**: Mix of keyword and semantic results
- **First Result**: Semantic match (BM25: 0.000, Dense: 0.500)

### Keyword-Only Search (BM25)
- **Match Breakdown**: 2 BM25 matches, 0 semantic matches
- **Results**: Only keyword matches
- **First Result**: BM25 match (BM25: 0.500, Dense: 0.000)

### Semantic-Only Search (Dense)
- **Match Breakdown**: 0 BM25 matches, 5 semantic matches
- **Results**: Only semantic matches
- **First Result**: Semantic match (BM25: 0.000, Dense: 0.500)

### Comparison Summary
- ✅ Hybrid unique results: 1
- ✅ Keyword unique results: 1
- ✅ Semantic unique results: 2
- ✅ Results in both Hybrid & Keyword: 1
- ✅ Results in both Hybrid & Semantic: 3

**Result**: Hybrid search now returns DIFFERENT results than keyword-only and semantic-only searches!

## API Response Enhancements

The search response now includes:

```json
{
  "search_metadata": {
    "use_bm25": true,
    "use_dense": true,
    "match_breakdown": {
      "bm25_matches": 1,
      "semantic_matches": 4,
      "hybrid_matches": 0
    }
  },
  "results": [
    {
      "match_type": "semantic",  // or "bm25"
      "metadata": {
        "bm25_score": 0.0,       // Actual BM25 score
        "dense_score": 0.5,      // Actual dense score
        "score_debug": {
          "raw_fusion_score": 0.5,
          "normalized_fusion": 1.0,
          "actual_bm25_score": 0.0,
          "actual_dense_score": 0.5,
          "keyword_boost": 0.0,
          "final_score": 1.0
        }
      }
    }
  ]
}
```

## Testing

A test script was created at `/home/Allie/develop/legalease/test_search_modes.py` that:
- Tests all three search modes (hybrid, keyword-only, semantic-only)
- Compares result sets
- Verifies different results are returned
- Shows match type breakdown
- Displays score comparisons

Run the test with:
```bash
cd /home/Allie/develop/legalease
python3 test_search_modes.py
```

## Impact

✅ **Hybrid search now properly combines BM25 and semantic results**
✅ **Each search mode returns distinct results**
✅ **Match types (BM25 vs semantic) are correctly identified**
✅ **Scores are properly tracked and boosted**
✅ **Debug metadata helps understand search behavior**

## Next Steps

1. ✅ Restart backend container to apply changes
2. ✅ Test hybrid search in frontend UI
3. ✅ Verify search highlights work correctly
4. ✅ Monitor search performance with new 3-query approach
5. Consider caching BM25/dense results for frequently searched terms
6. Add user-facing documentation about search modes
