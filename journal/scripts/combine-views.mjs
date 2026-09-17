import {readFileSync,existsSync,renameSync} from 'node:fs';
import {spawn,spawnSync} from 'node:child_process';
import {resolve,join} from 'node:path';
const root=resolve(import.meta.dirname,'..');
const catalog=JSON.parse(readFileSync(join(root,'public/experiments.json')));
const sources=new Map(readFileSync(join(root,'../data/video-evidence/index.csv'),'utf8').trim().split(/\r?\n/).slice(1).map(l=>{const p=l.split(',');return[p[5],p[6]]}));
const queue=catalog.experiments.filter(e=>['top','left','right'].every(v=>e.artifacts.some(a=>a.view===v)));
async function worker(){while(queue.length){
 const e=queue.shift(),out=join(root,'video-cache',e.id+'__combined.mp4');
 if(existsSync(out))continue;
 const views=['top','left','right'].map(v=>e.artifacts.find(a=>a.view===v));
 const files=views.map(a=>existsSync(join(root,'video-cache',a.file))?join(root,'video-cache',a.file):sources.get(a.file));
 const durations=files.map(f=>Number(spawnSync('ffprobe',['-v','error','-show_entries','format=duration','-of','csv=p=0',f],{encoding:'utf8'}).stdout.trim()));
 if(Math.max(...durations)-Math.min(...durations)>.15)throw new Error(e.id+' camera durations mismatch; review alignment');
 const filter='[0:v]setpts=PTS-STARTPTS,fps=30,scale=768:576:force_original_aspect_ratio=decrease,pad=768:576:(ow-iw)/2:(oh-ih)/2[top];[1:v]setpts=PTS-STARTPTS,fps=30,scale=384:288:force_original_aspect_ratio=decrease,pad=384:288:(ow-iw)/2:(oh-ih)/2[left];[2:v]setpts=PTS-STARTPTS,fps=30,scale=384:288:force_original_aspect_ratio=decrease,pad=384:288:(ow-iw)/2:(oh-ih)/2[right];[left][right]vstack=inputs=2[side];[top][side]hstack=inputs=2:shortest=1[out]';
 await new Promise((ok,no)=>{const p=spawn('ffmpeg',['-v','error','-y',...files.flatMap(f=>['-i',f]),'-filter_complex_threads','1','-filter_complex',filter,'-map','[out]','-an','-c:v','libx264','-threads','2','-preset','veryfast','-crf','22','-pix_fmt','yuv420p','-movflags','+faststart',out+'.partial.mp4'],{stdio:'inherit'});p.on('error',no);p.on('exit',c=>c===0?ok():no(new Error(e.id)));});
 renameSync(out+'.partial.mp4',out);console.log('Combined '+e.id);
}}
await Promise.all([worker(),worker()]);
