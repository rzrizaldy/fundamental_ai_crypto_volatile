# Interim Feedback for Team 3

## Overall interim assessment: Promising foundation

This is a credible Week 4 thin-slice submission. The strongest parts are the API service, the model selection rationale, and the effort to define a replay-mode path that matches the later system direction. The main need now is submission completeness. Several items named in the execution report are not present in the packaged deliverable, so the final needs a tighter link between what is described, what is stored in the repo, and what another reviewer can run.

## Top priorities before the final submission

- Make the package and report match exactly
- Include every script, test, and dashboard artifact mentioned in the report, or remove the references.
- Ensure the file paths in the report, README, Compose file, and docs all agree.
- Strengthen reproducibility of the replay path
- Include the replay smoke script and any validation tests used for the Week 4 run.
- Make it easy for a reviewer to rerun the replay flow from the delivered package alone.
- Turn screenshots into runnable evidence
- Include the real dashboard data or configuration where relevant, not just screenshots.
- Prepare for Weeks 5-7 by tightening the monitoring, QA, and handoff assets now.

## Recommended direction

- Continue current direction with targeted refinement
- Improve Docker reproducibility and startup clarity
- Strengthen replay pipeline integration
- Improve documentation and repo completeness
- Build a stronger path to monitoring and reliability

## Rubric

| Dimension | Overall rating | What is working well | What must be strengthened |
|---|---|---|---|
| 1) System architecture and thin-slice framing | Promising / On track | - The end-to-end thin-slice story is clear: replay data, model artifact, API endpoints, and monitoring hooks.<br>- The architecture intentionally uses replay mode for Week 4 instead of pretending the system is fully live.<br>- The team charter and system diagram make the service boundaries reasonably easy to follow. | - Several diagram and doc references point to files that are not in the delivered package, including the replay smoke script.<br>- Keep one authoritative implementation path so the architecture, file tree, and README all say the same thing.<br>- Make sure the final package backs the diagram with the actual runnable assets. |
| 2) Model selection and service rationale | Strong | - The logistic regression choice is sensible for Week 4 because it keeps the service path simple and testable.<br>- The included metrics show the selected model outperforming the baseline on PR-AUC and F1.<br>- The rationale focuses on operational fit, not just model quality, which is the right emphasis here. | - Keep the threshold and label-rule story fully consistent across the docs.<br>- Be explicit that the current model is regime-specific and should be treated as the service baseline, not the final modeling answer.<br>- Carry the same model designation consistently into later-week rollback and monitoring work. |
| 3) API functionality and contract compliance | Strong | - All four required endpoints are present: /health, /predict, /version, and /metrics.<br>- The request schema is concrete and the response includes model metadata that will matter later in operations.<br>- The replay-count option is a useful thin-slice design choice for Week 4 validation. | - Include one fully reproducible request and response example tied only to packaged files.<br>- Document the manual-row path and the replay path together so a reviewer does not have to infer the two modes.<br>- Keep the final API examples tightly synchronized with the README. |
| 4) Infrastructure, containerization, and one-command startup | Promising / On track | - Docker Compose and the two Dockerfiles are present in the packaged deliverable.<br>- Kafka, MLflow, and the API are all represented in the compose setup as the assignment expects.<br>- The README uses a simple startup command rather than a long manual sequence. | - The execution report cites docker/compose.yaml, while the delivered package uses top-level docker-compose.yaml. Remove that ambiguity.<br>- Make it obvious which exact files were used for the validated run.<br>- The final should be reproducible from the submitted package alone, not from unstated branch context. |
| 5) Replay pipeline and end-to-end integration | Promising / On track | - The execution report gives concrete replay results rather than vague claims.<br>- The package includes the feature parquet file and the selected model artifact needed for replay scoring.<br>- The API code contains explicit replay-slice logic, which is better than a placeholder endpoint. | - The replay smoke script named in the report is not included in the package.<br>- The updated test files mentioned in the report are also not present, which weakens the replay validation story.<br>- For the final, keep the full replay path inside the deliverable so another reviewer can rerun it directly. |
| 6) Engineering quality, documentation, and team coordination | Promising / On track | - The team charter is detailed and shows a realistic division of work across later weeks.<br>- The repo structure across pipeline, service, docs, and models is understandable.<br>- The docs are more disciplined than many interim submissions and do show handoff thinking. | - The docs still over-reference prior files and milestones that are not part of the current package.<br>- Tighten the README so it reflects only what a reviewer can inspect and run now.<br>- Keep the final submission focused on the actual team deliverable rather than the broader branch history. |
| 7) Observability and debugging readiness | Promising / On track | - The /metrics endpoint exposes counters, gauges, and a latency histogram, which is a good Week 4 start.<br>- The /health and /version endpoints provide practical debugging hooks.<br>- The screenshots suggest the team is already thinking about the monitoring path for later weeks. | - Most observability evidence is screenshot-based rather than runnable from the package.<br>- The report references dashboard and Evidently links, but the packaged monitoring assets are limited.<br>- The final should include the real dashboard JSON, runbook materials, and a clearer local monitoring path. |
| 8) Readiness for the final report and handoff | Promising / On track | - There is enough foundation here to move into CI, reliability, and later monitoring work.<br>- The selected-base model concept gives the team a stable starting point for the next phases.<br>- The thin-slice API surface is credible enough to support a stronger final system. | - Package completeness has to improve before the later-phase claims will feel fully convincing.<br>- Only claim later-week readiness when the matching scripts, configs, and docs are actually delivered.<br>- Use the final submission to close the gap between validation notes and reproducible artifacts. |
