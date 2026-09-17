import { readFileSync } from 'node:fs';

export function parseRoadmap(markdown) {
  return markdown.split(/^## (?=P\d+ — )/m).slice(1).map(section => {
    const lines = section.trim().split('\n');
    const [, id, title] = lines.shift().match(/^(P\d+) — (.+)$/);
    const field = name => lines.find(line => line.startsWith(name + ': '))?.slice(name.length + 2) ?? '';
    const status = field('Status');
    if (!['proved', 'current', 'planned'].includes(status)) throw new Error('Invalid status for ' + id);
    return { id, title, status, goal: field('Goal'), blocker: field('Blocker'), next: field('Next'),
      evidence: field('Evidence').match(/EV-\d{4}/g) ?? [],
      criteria: lines.filter(line => /^- \[[ x]\] /.test(line)).map(line => ({ done: line[3] === 'x', text: line.slice(6) })) };
  });
}

export function readRoadmap(path) {
  return { milestones: parseRoadmap(readFileSync(path, 'utf8')) };
}
