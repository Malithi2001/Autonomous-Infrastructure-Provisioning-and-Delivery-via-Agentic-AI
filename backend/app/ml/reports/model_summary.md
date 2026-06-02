# CI/CD Failure Classification Model Summary

## Model Type

The trained production model is a scikit-learn `Pipeline` with TF-IDF text
features and a balanced Logistic Regression classifier.

## Dataset Size

- Total usable examples: 330
- Training examples: 247
- Test examples: 83
- Number of labels: 11

## Labels

- `docker_build_failed`
- `maven_test_failed`
- `module_not_found`
- `npm_build_failed`
- `npm_install_failed`
- `npm_missing_lockfile`
- `npm_missing_test_script`
- `pytest_not_found`
- `python_missing_dependency`
- `unknown_failure`
- `wrong_runtime_version`

## Preprocessing

- Empty log text and empty labels are removed.
- `log_text`, `label`, and `suggested_fix` values are converted to stripped strings.
- Duplicate `(log_text, label, suggested_fix)` rows are removed.
- Text is vectorized with TF-IDF using lowercase normalization, English stop words, and 1-2 gram features.

## Train/Test Split

- Random state: 42
- Stratified split used: True
- Test split target: 0.25

## Evaluation Metrics

| Metric | Value |
| --- | ---: |
| Accuracy | 0.7952 |
| Macro precision | 0.7813 |
| Macro recall | 0.7938 |
| Macro F1 | 0.7760 |
| Weighted precision | 0.7849 |
| Weighted recall | 0.7952 |
| Weighted F1 | 0.7786 |

## Limitations

- The dataset is project-sized and synthetic/demo-oriented, so results should
  not be treated as production-grade reliability.
- CI/CD logs can contain project-specific tooling, secret redactions, and noisy
  output that may differ from the training examples.
- Some labels may have fewer examples than others, which can reduce recall for minority failure categories.
- The model predicts a likely failure category; human review is still needed before applying repository changes.

Generated at: 2026-06-02T08:58:14.399155+00:00
