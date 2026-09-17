import { createReadStream, existsSync, readFileSync, statSync } from 'node:fs';
import { createServer } from 'node:http';
import { extname, join, normalize, resolve } from 'node:path';
import { readRoadmap } from './roadmap.mjs';

const root = resolve(import.meta.dirname);
const publicDir = join(root, 'public');
const catalog = JSON.parse(readFileSync(join(publicDir, 'experiments.json'), 'utf8'));
const media = new Map(catalog.experiments.flatMap((experiment) => experiment.artifacts.map((artifact) => [artifact.file, artifact])));
const evidenceCsv = readFileSync(join(root, '../data/video-evidence/index.csv'), 'utf8').split(/\r?\n/);
const sources = new Map();
for (const line of evidenceCsv.slice(1)) {
  const parts = line.split(',');
  if (parts.length >= 7) sources.set(parts[5], parts[6]);
}

const mime = { '.html': 'text/html; charset=utf-8', '.css': 'text/css; charset=utf-8', '.js': 'text/javascript; charset=utf-8', '.json': 'application/json', '.jpg': 'image/jpeg', '.svg': 'image/svg+xml', '.mp4': 'video/mp4' };
const sendFile = (req, res, file) => {
  if (!existsSync(file)) { res.writeHead(404); res.end('Not found'); return; }
  const stat = statSync(file);
  const range = req.headers.range;
  res.setHeader('Content-Type', mime[extname(file)] ?? 'application/octet-stream');
  res.setHeader('Accept-Ranges', 'bytes');
  if (range) {
    const [startRaw, endRaw] = range.replace('bytes=', '').split('-');
    const start = startRaw ? Number(startRaw) : Math.max(0, stat.size - Number(endRaw));
    const end = startRaw && endRaw ? Math.min(Number(endRaw), stat.size - 1) : stat.size - 1;
    if (!Number.isInteger(start) || !Number.isInteger(end) || start < 0 || start > end || start >= stat.size) {
      res.writeHead(416, {'Content-Range': `bytes */${stat.size}`});res.end();return;
    }
    res.writeHead(206, { 'Content-Range': `bytes ${start}-${end}/${stat.size}`, 'Content-Length': end - start + 1 });
    createReadStream(file, { start, end }).pipe(res);
  } else {
    res.writeHead(200, { 'Content-Length': stat.size });
    createReadStream(file).pipe(res);
  }
};

createServer((req, res) => {
  const url = new URL(req.url, 'http://localhost');
  if (url.pathname === '/roadmap.json') {
    try {
      const roadmap = readRoadmap(join(root, '../docs/mvp-milestones.md'));
      res.writeHead(200, { 'Content-Type': 'application/json', 'Cache-Control': 'no-store' });
      res.end(JSON.stringify(roadmap));
    } catch {
      res.writeHead(500, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ error: 'Unable to load milestone document' }));
    }
    return;
  }
  if (/^\/combined\/EV-\d{4}\.mp4$/.test(url.pathname)) {
    const id=url.pathname.split('/').pop().replace('.mp4','');
    sendFile(req,res,join(root,'video-cache',id+'__combined.mp4'));return;
  }
  if (url.pathname.startsWith('/media/')) {
    const name = decodeURIComponent(url.pathname.slice('/media/'.length));
    if (!media.has(name) || !sources.has(name)) { res.writeHead(404); res.end('Unknown evidence'); return; }
    const playable = join(root, 'video-cache', name);
    sendFile(req, res, existsSync(playable) ? playable : sources.get(name));
    return;
  }
  let path = normalize(decodeURIComponent(url.pathname)).replace(/^(\.\.(\/|\\|$))+/, '');
  if (path === '/') path = '/index.html';
  sendFile(req, res, join(publicDir, path));
}).listen(4173, '127.0.0.1', () => console.log('Fold Lab Journal → http://127.0.0.1:4173'));
