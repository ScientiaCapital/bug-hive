# Bug Classifier Agent

## Overview

The **Bug Classifier Agent** transforms raw issues detected by the Page Analyzer into classified, prioritized, and deduplicated bugs ready for reporting. It uses intelligent rule-based classification for efficiency, with LLM fallback for uncertain cases.

## Architecture

```
RawIssue[] → BugClassifierAgent → Bug[]
                    ↓
         [Rule-based Classification]
                    ↓
         [LLM Classification (if confidence < 0.8)]
                    ↓
         [Deduplication]
                    ↓
         [Validated Bugs]
```

## Core Components

### 1. Classification System

**Rule-Based Classification (Primary)**
- **FREE and FAST**: No LLM calls for high-confidence issues
- Maps issue types to bug categories deterministically
- Estimates priority based on keywords and severity

**LLM Classification (Fallback)**
- **Triggered when**: `issue.confidence < 0.8`
- **Task**: `"classify_bug"` → DeepSeek-V3 (reasoning tier)
- **Returns**: Enhanced category, priority, and confidence

### 2. Bug Categories

| Category | Description | Examples |
|----------|-------------|----------|
| `ui_ux` | Visual defects, layout issues | Button misaligned, broken CSS, responsive issues |
| `data` | Data display problems | Missing data, incorrect API responses, stale cache |
| `edge_case` | Input handling failures | Form validation errors, boundary conditions |
| `performance` | Slow loads, resource issues | Page load > 3s, memory leaks, large bundles |
| `security` | Security vulnerabilities | XSS, injection, auth bypass, data exposure |

### 3. Priority Levels

| Priority | Criteria | Examples |
|----------|----------|----------|
| `critical` | App crash, data loss, security flaw | Server 500, auth bypass, XSS vulnerability |
| `high` | Core feature broken, major UX impact | Payment form broken, can't create account |
| `medium` | Feature partially broken, workaround exists | Search slow but functional, minor data issue |
| `low` | Minor visual issue, rare edge case | Button color off, text alignment issue |

### 4. Deduplication Strategy

**Fast Heuristics (No LLM)**
1. **Exact title match**: Same error message → duplicate
2. **Text similarity**: Jaccard similarity > 0.85 → duplicate
3. **Category filtering**: Only compare within same category

**LLM Deduplication (Critical/High Priority Only)**
- **Task**: `"deduplicate_bugs"` → DeepSeek-V3
- **Used for**: Critical and high-priority bugs requiring careful handling
- **Returns**: Binary duplicate decision with similarity score

## Classification Rules

### Issue Type → Category Mapping

```python
{
    "console_error": "ui_ux",      # JS errors affecting UI
    "network_failure": "data",      # API/data issues
    "performance": "performance",   # Performance issues
    "visual": "ui_ux",              # Visual defects
    "content": "data",              # Missing/incorrect content
    "form": "edge_case",            # Form validation issues
    "accessibility": "ui_ux",       # A11y issues
    "security": "security",         # Security vulnerabilities
}
```

### Priority Estimation Rules

**Critical Priority:**
- `type == "security"`
- Keywords: "crash", "fatal", "data loss", "injection", "xss", "auth bypass"

**High Priority:**
- Network failures: 500, 502, 503, 504 status codes
- Keywords: "broken", "not working", "fails", "error", "cannot", "unable to"
- Confidence > 0.7

**Medium Priority:**
- Confidence >= 0.7
- Default for most issues

**Low Priority:**
- Keywords: "cosmetic", "styling", "minor", "alignment", "spacing", "color"
- Confidence < 0.7

## Usage

### Basic Usage

```python
from src.agents import BugClassifierAgent
from src.llm import LLMRouter

# Initialize
llm_router = LLMRouter(anthropic_client, openrouter_client, cost_tracker)
classifier = BugClassifierAgent(llm_router)

# Process issues
raw_issues = await page_analyzer.analyze(page)
bugs = await classifier.process_issues(
    issues=raw_issues,
    session_id=session_id,
    page_id=page_id,
)

# Review classified bugs
for bug in bugs:
    print(f"{bug.priority.upper()}: {bug.title}")
    print(f"  Category: {bug.category}")
    print(f"  Confidence: {bug.confidence:.2%}")
    print(f"  Steps: {len(bug.steps_to_reproduce)} steps")
```

### Advanced Usage

```python
# Manual classification
bug = await classifier._classify_issue(
    issue=raw_issue,
    session_id=session_id,
    page_id=page_id,
)

# Check for duplicate
is_duplicate = await classifier._is_duplicate(
    bug=new_bug,
    existing_bugs=current_bugs,
)

# Compute similarity
similarity = await classifier._compute_similarity(
    text1=bug1.description,
    text2=bug2.description,
)
```

## Cost Optimization

### Rule-Based Classification (Free)

For high-confidence issues (confidence >= 0.8):
- **No LLM calls**: Uses deterministic rules
- **Instant**: < 1ms per issue
- **Cost**: $0.00

### LLM Classification (Paid)

For uncertain issues (confidence < 0.8):
- **Model**: DeepSeek-V3 (task: "classify_bug")
- **Tokens**: ~300 input + ~150 output = 450 tokens
- **Cost**: ~$0.0001 per issue (extremely cheap)
- **Latency**: ~500ms

### Deduplication Strategy

**Heuristics (Free):**
- Exact title match: 0 LLM calls
- Jaccard similarity: 0 LLM calls
- **Cost**: $0.00

**LLM Deduplication (Paid):**
- Only for critical/high priority bugs
- **Model**: DeepSeek-V3 (task: "deduplicate_bugs")
- **Cost**: ~$0.0001 per comparison
- **Benefit**: Prevents duplicate critical bug reports

### Cost Example (100 Issues)

Assuming:
- 70 high-confidence issues (>= 0.8) → rule-based
- 30 low-confidence issues (< 0.8) → LLM classification
- 5 critical bugs → LLM deduplication (10 comparisons)

**Total Cost:**
- Rule-based: 70 × $0.00 = $0.00
- LLM classification: 30 × $0.0001 = $0.003
- LLM deduplication: 10 × $0.0001 = $0.001
- **Total: ~$0.004** (less than half a cent)

## Generated Bug Properties

Each `Bug` object includes:

```python
Bug(
    id=UUID,                           # Unique identifier
    session_id=UUID,                   # Parent session
    page_id=UUID,                      # Source page
    category="ui_ux",                  # Bug category
    priority="high",                   # Priority level
    title="Submit button overlaps text",
    description="Detailed description...",
    steps_to_reproduce=[...],          # Generated steps
    evidence=[Evidence(...)],          # From RawIssue
    confidence=0.92,                   # AI confidence
    status="detected",                 # Lifecycle status
    expected_behavior="...",           # Inferred expectation
    actual_behavior="...",             # From description
    affected_users="Mobile users",     # Inferred scope
    created_at=datetime.utcnow(),
)
```

## Steps to Reproduce Generation

The classifier automatically generates reproduction steps based on issue type:

### Console Error
```
1. Navigate to https://example.com/products
2. Open browser developer console (F12)
3. Observe the console error as described
4. Refer to attached evidence for additional details
```

### Network Failure
```
1. Navigate to https://example.com/api
2. Open browser Network tab (F12 → Network)
3. Perform the action that triggers the network request
4. Observe the failed network request
5. Refer to attached evidence for additional details
```

### Visual Defect
```
1. Navigate to https://example.com/products
2. Observe the visual defect as described
3. Resize browser to mobile viewport (375px width)  # If mentioned in description
4. Refer to attached evidence for additional details
```

### Security Issue
```
1. Navigate to the affected page
2. ⚠️  WARNING: Security issue - handle with care
3. Follow security team's reproduction guidelines
4. Refer to attached evidence for additional details
```

## Logging

The classifier logs all classification decisions:

```
INFO  - Processing 15 raw issues for classification
DEBUG - Classifying issue 1/15: Button overlaps text on mobile
DEBUG - Low confidence (0.65), using LLM classification
DEBUG - LLM classification improved confidence: 0.65 → 0.82
INFO  - Classified bug: ui_ux/medium - Button overlaps text on mobile
DEBUG - Exact title match duplicate: TypeError in app.js
INFO  - Skipped duplicate bug: TypeError in app.js
INFO  - Classification complete: 12/15 unique bugs identified
```

## Testing

### Unit Tests

```bash
# Test classification logic (no dependencies)
python3 tests/test_classifier_logic.py
```

### Integration Tests

```bash
# Test with real LLM calls
pytest tests/agents/test_classifier_integration.py -v
```

## Error Handling

### LLM Classification Failure
- **Fallback**: Uses rule-based classification
- **Logged**: Warning with error details
- **Impact**: May have lower confidence score

### LLM Deduplication Failure
- **Fallback**: Uses Jaccard similarity
- **Logged**: Warning with error details
- **Impact**: Possible false negatives (duplicates not caught)

### Invalid JSON Response
- **Fallback**: Returns default classification
- **Logged**: Warning with unparsed content
- **Impact**: Classification may be suboptimal but functional

## Performance

### Throughput
- **Rule-based**: 1000+ issues/second
- **LLM-enhanced**: ~2-5 issues/second (network bound)
- **Mixed (70/30)**: ~300+ issues/second

### Latency (per issue)
- **Rule-based**: < 1ms
- **LLM classification**: ~500ms
- **LLM deduplication**: ~500ms

### Memory
- **Bug cache**: ~1KB per bug
- **Peak usage**: ~10MB for 1000 bugs

## Best Practices

1. **Maximize rule-based classification**: Tune confidence thresholds
2. **Batch processing**: Process all issues at once for efficiency
3. **Cache bugs**: Keep classifier instance alive to benefit from deduplication cache
4. **Monitor costs**: Track LLM usage via CostTracker
5. **Review uncertain classifications**: Log decisions for continuous improvement

## Future Enhancements

- [ ] Embeddings-based similarity for better deduplication
- [ ] Multi-label classification (bug can have multiple categories)
- [ ] Automatic category refinement based on user feedback
- [ ] Clustering similar bugs across sessions
- [ ] Priority adjustment based on affected user count
- [ ] Integration with bug tracking system for historical context
