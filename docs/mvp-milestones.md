# XLeRobot folding roadmap

Canonical milestone order, reviewed status, criteria and evidence associations.
Fold Lab reads this file on refresh. Product context: [PRD](prd.md).
Experiment PASS labels never promote milestones. Linked evidence can document
success, failure or an inconclusive attempt; checkboxes require reviewed proof.

## P0 — Known-good baseline

Status: proved
Goal: Reproduce Ilia's original short-shirt fold before changing the environment.
Blocker: None for the original scene; this does not establish XLeRobot transfer.
Next: Preserve baseline recordings as the regression reference.
Evidence: EV-0027, EV-0062, EV-0063

- [x] Original checkpoint visibly folds the original garment.
- [x] Three baseline recordings retained and visually reviewed.

## P1 — Leader-to-simulation teleoperation

Status: current
Goal: Control and record the known-good LeHome simulation using both physical leaders.
Blocker: End-to-end operator session and evidence remain unverified.
Next: Connect both powered leaders, verify mapping, and record a simulator canary.
Evidence: none

- [ ] Identify both leader ports and load calibration.
- [ ] Verify 12 joint directions and both grippers without follower motion.
- [ ] Display all three simulation cameras on the Mac.
- [ ] Verify disconnect and stale-action handling.
- [ ] Record and replay a synchronized two-minute episode; report latency and gaps.
- [ ] Complete two short repeats without remapping or restart.

## P2 — Valid XLeRobot simulation scene

Status: planned
Goal: Correct base placement, cameras, collisions and flat cloth reset.
Blocker: Previous geometry rollout began with malformed cloth and poor wrist views.
Next: Compare annotated original and XLeRobot reset frames before policy actions.
Evidence: EV-0064

- [ ] Match measured table, tray and arm placement.
- [ ] Show useful garment workspace and grippers in observations.
- [ ] Pass three physical and visual reset canaries.

## P3 — Reposition demonstration and frozen-policy test

Status: planned
Goal: Rotate or pull the original-size shirt into a reachable folding area.
Blocker: Valid scene and teleoperation are prerequisites.
Next: Test controlled translations and yaw angles, then record human recoveries.
Evidence: EV-0032

- [ ] Evaluate the frozen checkpoint before retraining.
- [ ] Record rotate, pull, place and release without off-table cloth.
- [ ] Teleoperator repositions and folds in three of five controlled layouts.

## P4 — Checkpoint adaptation without forgetting

Status: planned
Goal: Improve reposition-and-fold with corrections and original fold data.
Blocker: Valid corrections and a held-out evaluation set are required.
Next: Establish correction fine-tuning before adding reward shaping or AWR/RECAP changes.
Evidence: none

- [ ] Record dataset sources and replay sampling ratio.
- [ ] Define the original-scene regression guard before training.
- [ ] Improve held-out reposition results while meeting the regression guard.

## P5 — Adult-garment curriculum

Status: planned
Goal: Progressively extend garment size and difficulty with credible physics.
Blocker: Original-size reposition-and-fold must work first.
Next: Increase garment size gradually and inspect each manipulation phase.
Evidence: EV-0054, EV-0061

- [ ] Reject malformed resets and simulator exploits.
- [ ] Demonstrate repositioning, flattening and the intended fold sequence.
- [ ] Complete seven of ten held-out adult-shirt layouts with visual review.

## P6 — Real workstation transfer

Status: planned
Goal: Transfer the adapted policy to the calibrated physical workstation.
Blocker: Simulated adult-garment success and supervised workstation readiness.
Next: Match geometry, cameras, calibration and action rate.
Evidence: none

- [ ] Validate bounded actions and intervention controls with a present operator.
- [ ] Complete three of five standardized adult-shirt folds with synchronized video.

## P7 — Onsite continuous-improvement loop

Status: planned
Goal: Let an operator run, correct and improve folds without editing code.
Blocker: Repeatable physical folds and a regression suite are prerequisites.
Next: Connect intervention recording, aggregation, training and policy promotion.
Evidence: none

- [ ] Operator can capture and label corrections through the interface.
- [ ] Evaluate candidates on both new failures and previous capabilities.
- [ ] Reduce fixed-set failure rate over two iterations without prior-set regression.

# Historical mechanics work

The earlier M0–M5 ladder pursued a scripted adult-shirt teacher. Attempts 18–20
reported local retention in three bounded runs, but did not establish improved
reachability or a complete fold. This diagnostic finding does not promote P3
or P5. Attempt 16 remains a false-positive failure. Videos and ticket receipts
remain the historical evidence owners. Mobile pickup, whole-room simulation and
foundation-model replacement are deferred.
