# XLeRobot Folding Repository Guide

This repository extends Ilia Larchenko's LeHome solution. Preserve the upstream
structure and make the smallest change in the existing owner file.

## Default Rule

Before adding a file, search this index and the repository with `rg`. Modify the
existing owner whenever it can express the feature. A new source file is allowed
only when it introduces a genuinely independent runtime entry point or module
that has no existing owner; state that reason in the commit.

Do not create parallel `scripts/xlerobot/`, `simulation/`, DAgger, recording,
evaluation, or configuration trees. Local experiments, generated evidence,
videos, checkpoints, and one-off probes belong under ignored `.local/` paths.

## Feature Ownership Index

| Feature or change | Existing owner |
| --- | --- |
| RL pipeline values and simulation presets | `configs/rl_pipeline_sim.yaml` |
| Sim-to-real pipeline values | `configs/rl_pipeline_sim_to_real.yaml` |
| Real robot and camera values | `configs/real_robot.yaml` |
| Pipeline config schema, defaults, and validation | `src/lehome_solution/training/pipeline_config.py` |
| Training orchestration | `scripts/run_rl_pipeline.py` |
| Direct training entry point and training YAML parsing | `scripts/train.py`, `src/lehome_solution/training/yaml_train_config.py` |
| Policy evaluation and rollout launch | `scripts/run_eval.py`, `scripts/eval_worker.py` |
| Simulation DAgger collection | `scripts/dagger_collect.py` |
| Real demonstrations and corrections | `scripts/record_real_dagger.py` |
| Policy serving | `scripts/serve.py` |
| Real-to-sim replay and camera alignment | `scripts/replay_real_in_sim.py`, `scripts/real_camera_align.py` |
| Leader-arm inspection and visualization | `scripts/so101_reader.py`, `scripts/arm_viz.py` |
| Model architecture and policy behavior | `src/lehome_solution/models/`, `src/lehome_solution/policies/` |
| Dataset loading and transforms | `scripts/data_utils.py`, `src/lehome_solution/training/data_loader.py`, `src/lehome_solution/training/real_data_transforms.py` |
| Normalization statistics | `scripts/compute_norm_stats.py`, `src/lehome_solution/shared/normalize.py` |
| Hugging Face synchronization | `scripts/hf_sync_daemon.py`, `src/lehome_solution/distributed/` |
| Evaluation metadata, outputs, and rollout strategies | `src/lehome_solution/eval/` |
| Isaac task, cameras, and initial scene pose | `lehome-challenge/source/lehome/lehome/tasks/bedroom/garment_bi_cfg_v2.py` |
| Garment physics and base scale | `lehome-challenge/source/lehome/lehome/tasks/bedroom/config_file/particle_garment_cfg.yaml` |
| Fixed simulator arm placement | `configs/rl_pipeline_sim.yaml` (`simulation_geometry`), consumed by `lehome-challenge/scripts/utils/visual_augmentation.py` |
| Runtime garment augmentation | `lehome-challenge/scripts/utils/visual_augmentation.py`, configured by `configs/rl_pipeline_sim.yaml` |
| Robot asset and joint limits | `lehome-challenge/source/lehome/lehome/assets/robots/lerobot.py` |
| Leader-arm device mapping | `lehome-challenge/source/lehome/lehome/devices/lerobot/` |
| Tests | Extend the nearest existing file under `tests/`; add a test file only for a new independently owned module |

## Repository Boundary

- The parent repository owns policies, training, DAgger, evaluation, and their
  user-facing configuration.
- The `lehome-challenge` submodule owns Isaac Lab scenes, robot assets, garment
  physics, simulator devices, and environment implementation.
- Make simulator changes inside the submodule, commit and push them to the
  `KenjiPcx/lehome-challenge` fork, then update only the parent gitlink. Do not
  monkeypatch the simulator from a new parent-repo wrapper.
- Keep generated experiment journals and media out of Git. Commit only compact
  manifests or results when they are required to reproduce a decision.

## Current XLeRobot Extension

The XLeRobot geometry uses the existing pipeline transport without a separate
adapter:

- named `lehome` and `xlerobot` per-arm `[x_m, y_m, z_m, yaw_deg]` presets in
  `simulation_geometry.presets`, selected by `simulation_geometry.active_preset`
- transport through `scripts/run_rl_pipeline.py`
- root-pose application in
  `lehome-challenge/scripts/utils/visual_augmentation.py`

Change those config values for geometry experiments. Change
`pipeline_config.py` only when the schema itself changes, and change the
submodule augmentation module only when its behavior changes.

## Change Checklist

1. Locate the feature in the table and inspect its existing owner.
2. Search for related behavior with `rg`; reuse it before writing code.
3. Keep configurable values in the existing YAML and behavior in its owner.
4. If a feature has no row, add its durable owner to this index in the same
   change instead of creating a parallel surface.
5. Run the narrowest relevant test or import/compile check.
6. For submodule edits, verify both repositories are clean and the parent points
   to the pushed submodule commit.

Do not describe a scripted rollout as successful without inspecting the rendered
garment and arm motion. The current geometry extension has passed configuration
and compile checks; an Isaac rollout remains the proof for folding behavior.
