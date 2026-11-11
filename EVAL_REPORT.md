# Eval report

Synthetic corpus (seed 42): 25 documents, 40 questions (30 answerable, 10 unanswerable).

## Results

| Metric | Value | Gate | Result |
|---|---|---|---|
| recall@5 | 0.967 | 0.85 | PASS |
| citation accuracy | 0.933 | 0.90 | PASS |
| refusal rate | 1.000 | 0.90 | PASS |

Overall: PASS

## Settings

| Setting | Value |
|---|---|
| chat model | qwen2.5:7b |
| embed model | nomic-embed-text |
| min score | 0.35 |
| chunk size | 800 |
| chunk overlap | 150 |
| top k | 5 |

## Failing cases

| Id | Question | Problem | Answer |
|---|---|---|---|
| Q09 | What is the access code for Project Ember Falcon? | wrong citation | QQA-6324 [1] |
| Q12 | What is the access code for Project Crimson Summit? | refused an answerable question, expected file not retrieved | I cannot find the answer in your documents. |
