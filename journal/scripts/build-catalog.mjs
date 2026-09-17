import { createReadStream, existsSync, mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { dirname, join, resolve } from 'node:path';
import { spawnSync } from 'node:child_process';

const root = resolve(import.meta.dirname, '..');
const project = resolve(root, '..');
const csvPath = join(project, 'data/video-evidence/index.csv');
const outPath = join(root, 'public/experiments.json');
const thumbDir = join(root, 'public/thumbs');

const parseCsvLine = (line) => {
  const cells = [];
  let current = '';
  let quoted = false;
  for (let i = 0; i < line.length; i++) {
    const char = line[i];
    if (char === '"' && line[i + 1] === '"') { current += '"'; i++; }
    else if (char === '"') quoted = !quoted;
    else if (char === ',' && !quoted) { cells.push(current); current = ''; }
    else current += char;
  }
  cells.push(current);
  return cells;
};

const lines = readFileSync(csvPath, 'utf8').trim().split(/\r?\n/);
const headers = parseCsvLine(lines.shift());
const rows = lines.map((line) => Object.fromEntries(headers.map((h, i) => [h, parseCsvLine(line)[i]])));
const groups = new Map();

const phaseFor = (name) => {
  if (/baseline|Top_Short/.test(name)) return 'Baseline';
  if (/geometry/.test(name)) return 'Geometry transfer';
  if (/physical-fold|local-grasp|reposition|assisted/.test(name)) return 'Simulation';
  if (/camera|head-view/.test(name)) return 'Perception';
  return 'Hardware';
};

const copy = {
  'EV-0054': ['Does script completion prove a physical fold?', 'No. Attempt 16 reported a false PASS while the garment remained malformed. Visual review rejected it and motivated settling and physical-outcome checks.', 'failed'],
  'EV-0001': ['Can coordinated arm motion be observed safely?', 'Established a synchronized multi-camera record of the first bimanual movement.', 'inconclusive'],
  'EV-0002': ['Can the gripper produce a visible controlled pinch?', 'Small command range produced a detectable gripper response.', 'passed'],
  'EV-0010': ['Can the head camera frame the shared workspace?', 'Tested three tilt positions and selected the useful downward view.', 'passed'],
  'EV-0022': ['Can Cartesian control lift a grasped cloth patch?', 'Began the lift-and-transfer debugging sequence.', 'inconclusive'],
  'EV-0024': ['Can the arm retain fabric through a larger transfer?', 'Produced the clearest early grasp-transfer highlight.', 'passed'],
  'EV-0027': ['Does Ilia’s unmodified LeHome baseline visibly fold?', 'Recovered the author baseline and a real folding reference.', 'passed'],
  'EV-0029': ['Does the transferred policy work before scene adaptation?', 'Policy behavior exposed an environment and geometry mismatch.', 'failed'],
  'EV-0032': ['Can the garment be repositioned before folding?', 'The first explicit reposition rollout established the task boundary.', 'failed'],
  'EV-0038': ['Is cloth mass/contact tuning the main failure?', 'Isolated contact behavior without yet producing a complete fold.', 'inconclusive'],
  'EV-0042': ['Can one local cloth patch be grasped without warping the mesh?', 'Local grasp retention remained too weak for reliable manipulation.', 'failed'],
  'EV-0048': ['Can a physics-respecting scripted sequence complete a fold?', 'Started the native-contact folding ladder.', 'failed'],
  'EV-0055': ['Does a cheap canary reject broken cloth before full rollout?', 'Added a short physical preflight to prevent expensive false positives.', 'passed'],
  'EV-0061': ['Can the refined physical sequence create a credible fold?', 'Reached the final assisted physical-fold attempt before baseline reset.', 'inconclusive'],
  'EV-0062': ['Does the frozen published policy reproduce a visible fold?', 'Exact author task completed successfully in 329 steps.', 'passed'],
  'EV-0063': ['Is the recovered baseline repeatable?', 'A second exact-seed episode also completed a compact fold.', 'passed'],
  'EV-0064': ['Does the frozen policy survive XLeRobot geometry alone?', 'Failed honestly: moved roots corrupted cloth pose and wrist-camera views.', 'failed']
};

for (const row of rows) {
  const group = groups.get(row.evidence_id) ?? {
    id: row.evidence_id,
    experiment: row.experiment,
    recordedAt: row.recorded_at,
    phase: phaseFor(row.experiment),
    artifacts: [],
  };
  group.artifacts.push({ view: row.view, file: row.catalog_file, bytes: Number(row.bytes), url: `/media/${encodeURIComponent(row.catalog_file)}` });
  groups.set(row.evidence_id, group);
}

mkdirSync(dirname(outPath), { recursive: true });
mkdirSync(thumbDir, { recursive: true });
const experiments = [...groups.values()].map((item) => {
  const [hypothesis, learning, status] = copy[item.id] ?? [
    `What does ${item.experiment.replaceAll('-', ' ')} reveal about the current system?`,
    'Retained as chronological evidence; interpretation is pending consolidation.',
    /probe|test/.test(item.experiment) ? 'inconclusive' : 'failed',
  ];
  const first = rows.find((r) => r.evidence_id === item.id);
  const thumb = `${item.id}.jpg`;
  const thumbPath = join(thumbDir, thumb);
  if (!existsSync(thumbPath) && first?.source && existsSync(first.source)) {
    const result = spawnSync('ffmpeg', ['-loglevel', 'error', '-ss', '1', '-i', first.source, '-frames:v', '1', '-vf', 'scale=720:-2', '-q:v', '4', '-y', thumbPath]);
    if (result.status !== 0 || !existsSync(thumbPath)) {
      spawnSync('ffmpeg', ['-loglevel', 'error', '-ss', '0.05', '-i', first.source, '-frames:v', '1', '-vf', 'scale=720:-2', '-q:v', '4', '-y', thumbPath]);
    }
  }
  return { ...item, hypothesis, learning, status, thumbnail: `/thumbs/${thumb}` };
});

const payload = {
  generatedAt: new Date().toISOString(),
  summary: { experiments: experiments.length, artifacts: rows.length, bytes: rows.reduce((sum, row) => sum + Number(row.bytes), 0) },
  experiments: experiments.reverse(),
};
writeFileSync(outPath, `${JSON.stringify(payload, null, 2)}\n`);
console.log(`Built ${experiments.length} experiments and ${rows.length} artifacts.`);
