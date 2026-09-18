# PRD: XLeRobot adult-garment folding deployment

## Status

- Phase: evidence-building
- Immediate gate: physical leader arms teleoperate the original LeHome simulation
- Canonical experiment history: `data/video-evidence/index.csv`
- Generated evidence viewers and media remain local under ignored paths.

## Problem / Context

The open LeHome policy visibly folds the original simulated garments, but that
does not yet prove that it can operate with XLeRobot geometry, recover a badly
positioned garment, fold adult-sized garments, or transfer to the physical
workstation. Previous experiments mixed physics debugging, scripted teachers,
policy evaluation, and product claims, which allowed internal metrics to pass
even when the video did not show a credible fold.

The project needs one ordered evidence ladder. Each rung must prove one new
capability with watchable video and mechanical receipts before training or
deployment advances.

## First-Principles Basis

- **Objective:** deploy an XLeRobot system that reliably folds standardized
  adult garments and can improve from onsite human corrections.
- **User or system need:** a tailor or operator must be able to run, correct,
  and improve the robot without editing policy code.
- **Root cause:** the pretrained LeHome policy is coupled to its training
  geometry, observations, action distribution, and garment layouts; our first
  XLeRobot rollout also began from an invalid cloth reset, so repositioning has
  not yet received a fair test.
- **Key assumptions:** Ilia's checkpoint supplies useful folding priors; the
  physical SO101 leader arms can provide valid simulator actions; small
  aggregated correction datasets can adapt the checkpoint without erasing its
  original folding skill.
- **Constraints:** Mac-hosted leader arms, RunPod-hosted Isaac simulation,
  XLeRobot follower geometry, three robot cameras, deformable-cloth physics,
  asynchronous network transport, and eventual Jetson deployment.
- **First viable slice:** use both physical leader arms to control the original
  short-shirt LeHome simulation while receiving its three camera views on the
  Mac, and save one synchronized episode.
- **Proof / falsification:** pass only when both leaders independently produce
  the intended simulated arm/gripper motion, the UI remains usable, and the
  saved episode replays with synchronized actions and cameras. Connection alone
  is not success.
- **Tradeoff accepted:** prove the data path in the known-good original scene
  before adapting the scene or collecting useful XLeRobot training data.
- **Non-goals:** a new foundation model, whole-room digital twin, mobile
  laundry pickup, arbitrary garments, and unattended physical rollout.

## Audience

- **Primary:** the developer/operator building and correcting the folding
  system with physical leader arms.
- **Secondary:** a tailor who will later run folds and record corrections onsite
  through a simplified interface.

## JTBD

When the folding policy fails on a garment or workstation layout, I want to
take over with the leader arms and record a valid correction, so the next policy
version improves that failure without losing behavior that already worked.

## SLC Slice — Simulation Teleoperation Proof

The next release is a complete correction-data path, not a folding-policy
improvement:

```text
physical leader arms on Mac
        -> calibrated joint readings
        -> SSH action stream
        -> original LeHome simulation on RunPod
        -> three-camera/operator UI on Mac
        -> synchronized episode + video + manifest
```

It deliberately uses the original known-good LeHome scene. After transport is
proven, the same path moves to the corrected XLeRobot scene.

## Prototype / PoC Gates

- **Highest-risk assumption:** two physical leaders and the remote simulator can
  form a responsive, correctly mapped, recordable control loop.
- **Prototype artifact:** one cataloged teleoperated episode containing two
  leader streams, simulated actions/states, three camera streams, timing, and a
  screen recording.
- **Pass signal:** both arms and grippers map correctly; no cross-wiring or
  sign inversion; median control latency is reported; no dropped interval over
  500 ms during a two-minute episode; replay is decodable and synchronized.
- **Ticket before full production build:** yes, after this PRD is accepted.

## Capability Milestones

Experiment PASS labels never promote milestones. Evidence can document success,
failure, or an inconclusive attempt; checklist completion requires reviewed
proof.

### P0 — Known-good baseline

**Status:** proved. Reproduce Ilia's original short-shirt fold before changing
the environment. The original checkpoint visibly folds the original garment;
baseline recordings EV-0027, EV-0062, and EV-0063 are retained.

### P1 — Leader-to-simulation teleoperation

**Status:** partial. Both physical leaders control and record the known-good
LeHome simulation with selectable direct/mirrored mapping and three returned
camera views. Remaining proof is a replayable synchronized episode without a
restart or dropped interval.

### P2 — Valid XLeRobot simulation scene

**Status:** planned. Match measured base placement, cameras, collisions, and
flat-cloth reset. Compare annotated original and XLeRobot reset frames before
policy actions and pass three physical/visual reset canaries. Evidence EV-0064
records the previous malformed-cloth failure.

### P3 — Reposition demonstration and frozen-policy test

**Status:** planned. Rotate or pull the original-size shirt into a reachable
folding area, test the frozen checkpoint before retraining, and teleoperate a
complete reposition-and-fold in three of five controlled layouts.

### P4 — Checkpoint adaptation without forgetting

**Status:** planned. Fine-tune with human corrections plus original successful
fold data. Promotion requires improved held-out reposition results without
regression on the original scene.

### P5 — Adult-garment curriculum

**Status:** planned. Increase garment size gradually with credible physics,
reject malformed resets and simulator exploits, and complete seven of ten
held-out adult-shirt layouts with visual review.

### P6 — Real workstation transfer

**Status:** planned. Match geometry, cameras, calibration, and action rate at
the physical workstation. Validate bounded actions and complete three of five
standardized adult-shirt folds with synchronized video.

### P7 — Onsite continuous improvement

**Status:** planned. Let an operator run, correct, retrain, and promote policies
without editing code. Candidates must improve a fixed failure set without
regressing prior capabilities.

Historical mechanics note: attempts 18–20 showed bounded local retention but
did not establish improved reachability or a complete fold. Attempt 16 remains
a false positive. Mobile pickup, whole-room simulation, and foundation-model
replacement remain deferred.

## Metric Candidates

- **Current primary:** end-to-end teleoperation episode passes or fails.
- **Transport:** median and p95 action-to-simulation latency; longest dropped
  control interval.
- **Mapping:** 12/12 joint directions and 2/2 grippers verified.
- **Recording:** three camera streams plus actions/states replay synchronously.
- **Policy milestones:** task success on a frozen held-out seed/layout set.
- **Guards:** original-scene regression, invalid-physics rate, off-table rate,
  collision/joint-limit violations, and human-reviewed terminal silhouette.

## User Stories

### US-001: Teleoperate simulation with physical leaders

As the developer, I want both physical leaders to control the simulated arms so
that I can create corrections without risking the follower hardware.

**Acceptance Criteria:**

- [ ] Device doctor identifies both leader ports and calibration files.
- [ ] Left/right mapping and every joint direction are visibly verified.
- [ ] Loss of either serial connection or network stream stops command updates
      and reports the failed side.
- [ ] Original LeHome three-camera UI is visible on the Mac.
- [ ] A complete episode is recorded, replayed, and cataloged.

### US-002: Diagnose experiments visually

As the developer, I want every promoted experiment to include chronological
video and metrics so that an internal PASS cannot hide a visibly broken fold.

**Acceptance Criteria:**

- [ ] Each retained experiment has an ID, hypothesis, configuration, result,
      video paths, and human visual verdict.
- [ ] Failed attempts remain in chronological order and are never relabeled as
      successes because a script completed.
- [ ] The evidence catalog can filter baseline, teleoperation, scene, reposition,
      adaptation, adult-garment, and real-world runs.

### US-003: Add corrections without catastrophic forgetting

As the developer, I want new corrections trained with prior successful data so
that fixing repositioning does not destroy folding.

**Acceptance Criteria:**

- [ ] Dataset manifest records source and sampling weight for every episode.
- [ ] Every candidate checkpoint is evaluated on both the new failure set and
      the frozen original-scene regression set.
- [ ] Promotion requires improvement on the target set and compliance with the
      regression guard.

## Functional Requirements

- **FR-1:** one command performs a read-only Mac leader-arm doctor.
- **FR-2:** the teleoperation bridge fails closed on stale actions, disconnect,
  malformed packets, or missing calibration.
- **FR-3:** the UI returns three simulated camera feeds and operator controls to
  the Mac without exposing a public service port.
- **FR-4:** recording stores synchronized observations, leader readings,
  simulator actions/states, timestamps, run configuration, and outcome.
- **FR-5:** every experiment is appended to the chronological evidence catalog.
- **FR-6:** training manifests distinguish original demonstrations, autonomous
  rollouts, human corrections, simulated data, and real data.
- **FR-7:** policy promotion always runs a frozen regression suite.

## Experiment Operating Contract

Every experiment must state:

1. **ID and date** — monotonically increasing and chronological.
2. **Question** — one uncertainty the run resolves.
3. **Prediction** — observable result expected if the change is correct.
4. **Single material change** — no bundled parameter sweeps before a canary.
5. **Inputs** — code revision, checkpoint, seed, scene and calibration hashes.
6. **Evidence** — videos, manifest, metrics, sampled frames, and logs.
7. **Verdict** — pass, fail, invalid, or inconclusive with human visual review.
8. **Next action** — promote, revise, or stop; never infer success from script
   completion alone.

The CSV catalog is the source of chronological evidence. Any generated viewer
is disposable and must not become a second source of truth.

## Immediate Todo

1. Connect and power both leader arms; followers may remain disconnected.
2. Run the read-only serial/device doctor and bind left/right ports.
3. Verify calibration loading and 12 joint directions without EEPROM writes.
4. Start the Mac/RunPod bridge against the original LeHome DAgger scene.
5. Complete a short motion/gripper canary and inspect all three views.
6. Record, replay, and catalog one two-minute episode plus two short repeats.
7. Only then repair the XLeRobot scene reset/cameras and collect reposition
   demonstrations.

## Constraints

- **Safety:** leader-arm reads must not enable follower torque; physical policy
  rollouts require bounded speed, joint limits, emergency stop, and a human in
  reach of power.
- **Privacy:** calibration and credentials remain machine-local; experiment
  manifests store hashes/identifiers rather than secrets.
- **Performance:** report measured teleoperation latency before using recorded
  data for training; do not silently interpolate long connection gaps.
- **Platform:** Mac handles USB leaders/UI; RunPod handles Isaac and training;
  Jetson deployment comes after simulated adaptation.
- **Budget/time:** use the already authorized RunPod resources, but prefer cheap
  preflight/canary gates before full render or training runs.

## Autonomy Readiness

- **Human inputs/assets needed:** two connected, powered leader arms; physical
  garment/reset actions only when real-world work begins.
- **Credentials / external services:** existing RunPod pod, SSH key, and volume.
- **Compute or runtime needs:** Mac serial access and RunPod Isaac environment.
- **Tooling gaps:** a single doctor/launcher, stale-action watchdog, synchronized
  recorder, and automatic evidence-catalog update.
- **Hard-to-QA surfaces:** cloth realism, grasp quality, and final fold quality
  require video review in addition to metrics.
- **Human gates:** visual approval of milestone evidence; physical emergency
  stop during real rollouts; explicit approval before deleting data or stopping
  paid infrastructure.
- **Agent decision boundaries:** safe diagnostics, simulator edits, canaries,
  recordings, and authorized cloud compute may proceed autonomously; no
  unobserved physical movement or destructive migration.

## Risks / Unknowns

- Leader/follower kinematic and joint-sign mappings may differ.
- Network latency may make direct teleoperation awkward but still usable for
  low-rate corrections.
- The failed XLeRobot rollout does not distinguish observation shift from
  invalid reset because both occurred together.
- Sparse correction data can cause catastrophic forgetting without replay and
  frozen regression evaluation.
- Adult cloth fidelity may remain inadequate even after controller progress;
  visual/physical gates must reject simulator exploits.

## Backpressure / Evidence to Ship

- **Tests:** packet/schema tests, calibration/mapping checks, disconnect and
  stale-action tests, recorder/replay integrity.
- **QA:** operated teleoperation video with all three cameras and visible
  two-arm/gripper response.
- **Performance:** latency distribution and dropped-control interval report.
- **Experiment proof:** catalog row, immutable run manifest, source/checkpoint
  revisions, human visual verdict, and links to retained artifacts.

## Deferred

- Whole-room scanning and general household simulation.
- Mobile-base pile collection.
- General language-conditioned autonomy or replacement foundation models.
- Pi0.7/other-model migration before the current data and evaluation loop works.
- Production tailor UI before developer teleoperation and promotion gates are
  proven.
