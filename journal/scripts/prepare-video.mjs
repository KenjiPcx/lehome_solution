import {readFileSync,mkdirSync,existsSync,renameSync} from 'node:fs';
import {spawn,spawnSync} from 'node:child_process';
import {resolve,join} from 'node:path';
const root=resolve(import.meta.dirname,'..');
const directory=join(root,'video-cache');
mkdirSync(directory,{recursive:true});
const rows=readFileSync(join(root,'../data/video-evidence/index.csv'),'utf8').trim().split(/\r?\n/).slice(1).map(line=>line.split(','));
const pending=rows.filter(row=>{
  const codec=spawnSync('ffprobe',['-v','error','-select_streams','v:0','-show_entries','stream=codec_name','-of','csv=p=0',row[6]],{encoding:'utf8'}).stdout.trim();
  return codec!=='h264'&&!existsSync(join(directory,row[5]));
});
async function worker(){
  while(pending.length){
    const row=pending.shift(),target=join(directory,row[5]),temp=target+'.partial.mp4';
    await new Promise((resolve,reject)=>{
      const child=spawn('ffmpeg',['-v','error','-y','-i',row[6],'-map','0:v:0','-an','-c:v','libx264','-preset','veryfast','-crf','21','-pix_fmt','yuv420p','-threads','2','-movflags','+faststart',temp],{stdio:'inherit'});
      child.on('error',reject);child.on('exit',code=>code===0?resolve():reject(new Error('Conversion failed: '+row[5])));
    });
    renameSync(temp,target);console.log('READY '+row[5]);
  }
}
await Promise.all(Array.from({length:4},worker));
