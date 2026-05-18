# Week 11 Data Card

## 1. Purpose

This project currently uses several different data assets for different goals:
- model demonstration
- offline sentiment evaluation
- edge-case / guardrail testing
- customer-service knowledge grounding

This data card summarizes what each asset is used for and how it should be interpreted in reports.

## 2. Main datasets

### 2.1 `week3_raw_reviews_1000_unprocessed.csv`
- Role: main MVP review sample set
- Size: 1000 rows
- Key fields:
  - `review_id`
  - `category`
  - `label_raw`
  - `review_text`
  - `source_file`
- Use: frontend demo, batch-analysis flow, exploratory analysis

### 2.2 `gold_200_end.csv`
- Role: offline gold evaluation result comparison file
- Size: 200 rows
- Key fields:
  - `text`
  - `sentiment`
  - `confidence`
  - `pain_points`
  - `summary_zh`
- Use: accuracy discussion, mismatch analysis, prompt improvement review

### 2.3 `week9_extreme_edge_cases.csv`
- Role: boundary / safety / defensive prompt validation set
- Focus:
  - sarcasm
  - emoji-heavy input
  - gibberish
  - hostile text
  - prompt injection / suspicious links
- Use: guardrail and handoff behavior checks

### 2.4 `week11_prompt_eval_set.csv`
- Role: compact curated prompt regression set
- Use:
  - prompt iteration reporting
  - language-control checks
  - pain-point extraction checks
  - guardrail correctness checks

## 3. Annotation dimensions

The current project has effectively four annotation dimensions:
- `sentiment`
  - `positive`
  - `neutral`
  - `negative`
- `pain_points`
  - short issue phrases, can be empty for non-problematic reviews
- `summary_zh`
  - field name is legacy-compatible
  - content language is controlled by prompt mode (`zh` or `en`)
- `expected_guardrail`
  - for extreme cases only
  - examples:
    - `normal`
    - `conservative`
    - `handoff_human`

## 4. Known limitations

### 4.1 Label subjectivity
- Some “neutral vs negative” cases remain subjective.
- Mild complaints and mixed-tone reviews are the main ambiguity zone.

### 4.2 Pain-point granularity inconsistency
- Some labels are very concrete (e.g. `包装破损`)
- Some are broader abstractions (e.g. `综合体验不佳`)
- This affects exact-match evaluation unless a normalization step is added.

### 4.3 Mixed business scenarios
- The current datasets are mainly e-commerce review oriented.
- They are not yet representative of all customer-service dialog scenarios.

### 4.4 Language asymmetry
- Chinese coverage is stronger than English coverage.
- English examples currently serve more as prompt-control validation than as a large-scale benchmark.

## 5. Recommended evaluation usage

### For sentiment-analysis reporting
- Use `gold_200_end.csv`
- Report:
  - overall accuracy
  - negative recall
  - representative mismatch types

### For guardrail / prompt reporting
- Use `week9_extreme_edge_cases.csv` + `week11_prompt_eval_set.csv`
- Report:
  - guardrail correctness
  - conservative response rate
  - handoff recommendation correctness

### For demo / frontend testing
- Use:
  - `week5_sample_50_with_time.csv`
  - `week5_sample_50_with_time_en_offline.csv`
- Report:
  - time trend support
  - bilingual summary support

## 6. Next suggested data work

- Build a normalized pain-point taxonomy table
- Add 20 to 30 multilingual customer-service dialog samples
- Add one machine-readable evaluation script for `week11_prompt_eval_set.csv`
