# Fold Lab Journal

## Roadmap and experiments

Open **Roadmap** to see the current milestone, acceptance criteria, blocker,
next action and linked videos. Selecting an evidence card opens the existing
player; the player links back to its associated milestone.

`../docs/mvp-milestones.md` owns the milestone order and reviewed status.
The server parses `## P0 — Title` headings, `Status:`, `Goal:`, `Blocker:`,
`Next:`, `Evidence:` fields, and Markdown checklists. Status is one of
`proved`, `current`, or `planned`; evidence uses existing `EV-0000` IDs.
Edit the document and refresh the page; no catalog rebuild is required for
roadmap edits. Experiment results never automatically promote a milestone.

The PRD owns product context. The CSV remains the chronological evidence source.
Restart the local server after updating server code.

A local-first visual journal for the XLeRobot folding experiments. It presents every cataloged experiment as a chronological hypothesis, outcome, and set of watchable camera artifacts without duplicating the 1.22 GB evidence archive.

```bash
cd "/Users/kenjipcx/Zanarkand Technologies/projects/Robotics/xlerobot-folding/journal"
npm run catalog
npm run dev
```

Open <http://127.0.0.1:4173>. Re-run `npm run catalog` whenever new rows are added to `data/video-evidence/index.csv`.

The local server streams only media files explicitly listed in the evidence catalog. The generated thumbnails and `public/experiments.json` are disposable derivatives; the source recordings remain owned by `data/video-evidence/`.
