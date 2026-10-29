# Local QA execution results

This document records observed local execution separately from the scenario plan
in [QA_TESTING.md](QA_TESTING.md). Final run identifiers, counts and limitations
are updated after verification. Until then, the generated report directories are
the authoritative evidence; no pending scenario is represented as passing.

Historical model metrics are stored under `backend/app/ml/reports/` and were
generated on 2 June 2026. They are not newly measured by UI rendering tests.

## Chapter 6 adaptation

The software quality evaluation used a layered strategy combining existing pytest
unit and integration tests, Selenium browser automation and controlled HTTP
security checks. External language-model, GitHub and Docker operations were
replaced with deterministic fixtures, while authentication, authorization,
orchestration, database persistence and approval enforcement used application
code. This design increased repeatability and prevented unintended changes to
production repositories or infrastructure.

Source inspection and boundary-case experiments identified defects in repository
readiness classification, expired approval presentation, prediction confidence
validation, shell argument restrictions and webhook payload handling. Focused
corrections were evaluated through regression tests. Evidence includes JUnit and
HTML reports, statement coverage, failure screenshots and a traceability table
linking each executed scenario to its observed result and tested source revision.

Quantitative outcomes must be taken from the final execution table below and
its referenced report files. A blocked ZAP scan provides no vulnerability-assessment
result. Successful controlled tests support only the behaviors and inputs tested;
they do not establish complete security, production performance or universal model
accuracy. Historical model metrics should be discussed as a separate experiment.
