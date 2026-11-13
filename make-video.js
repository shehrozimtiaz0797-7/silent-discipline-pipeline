'use strict';
// Silent Discipline: makes stoic motivation Shorts for TikTok.
//   node make-video.js              make 1 video (and post it when TikTok posting is set up)
//   node make-video.js --sample     test video without any keys
const fs = require('fs');
const path = require('path');
const { ROOT, env, log } = require('./src/lib');
const { writeScript, addHistory, readHistory } = require('./src/script');
const { makeVoice } = require('./src/voice');
const { buildVideo } = require('./src/video');

const SAMPLE = process.argv.includes('--sample');

const sample = {
  theme: 'discipline when no one is watching',
  hook: 'NOBODY TELLS YOU THIS',
  lines: [
    'The people who *win* are not louder than you.',
    'They just keep going when the *room* is empty.',
    'No applause. No one checking. Just the *work*.',
    'Do it quietly for one year.',
    'Then let the *results* do the talking.',
  ],
  caption: 'Work in silence. 🗿 #stoic #discipline #motivation #selfimprovement #mindset',
};
sample.spoken = sample.lines.map(l => l.replace(/\*/g, '')).join(' ');

(async () => {
  const script = SAMPLE ? sample : await writeScript();
  const n = new Date(), p = v => String(v).padStart(2, '0');
  const dir = path.join(ROOT, 'output', `${n.getFullYear()}-${p(n.getMonth() + 1)}-${p(n.getDate())}_${p(n.getHours())}-${p(n.getMinutes())}`);
  fs.mkdirSync(dir, { recursive: true });
  fs.writeFileSync(path.join(dir, 'script.json'), JSON.stringify(script, null, 2));
  const voice = SAMPLE && !env('GEMINI_API_KEY') ? null : await makeVoice(script, dir, readHistory().length);
  const video = await buildVideo(script, voice, dir);
  fs.writeFileSync(path.join(dir, 'caption.txt'), script.caption);
  // TikTok posting is added in src/tiktok.js once the account is connected.
  if (!SAMPLE) addHistory({ theme: script.theme, hook: script.hook, lines: script.lines, spoken: script.spoken, date: new Date().toISOString() });
  log(`Done: ${video.file}`);
})().catch(e => { log('Failed: ' + (e.stack || e.message)); process.exit(1); });
