'use strict';
// Builds the final video: frames (render.py) + voice + music (ducked under the voice), loudness for social apps.
const fs = require('fs');
const path = require('path');
const { ROOT, log, run, FFMPEG, PYTHON } = require('./lib');


async function buildVideo(script, voice, dir) {
  const VSTART = 1.6; // hook impact plays alone first
  const plain = script.lines.map(l => l.replace(/\*/g, ''));
  const speakDur = voice ? voice.dur : Math.max(12, plain.join(' ').split(' ').length / 2.3);
  const total = VSTART + speakDur + 1.8;
  // each line appears when the voice reaches it (estimated by its share of the characters)
  const chars = plain.map(l => l.length + 6);
  const sum = chars.reduce((a, b) => a + b, 0);
  let acc = 0;
  const starts = chars.map(c => { const s = VSTART + speakDur * (acc / sum) - 0.15; acc += c; return Math.max(0.3, s); });

  const silent = path.join(dir, 'silent.mp4');
  const spec = {
    font_serif: path.join(ROOT, 'fonts', 'Lora-Variable.ttf'), font_bold: path.join(ROOT, 'fonts', 'Poppins-Bold.ttf'),
    hook: script.hook, lines: script.lines, line_starts: starts, total, intro: VSTART, voice_end: VSTART + speakDur, ffmpeg: FFMPEG(), out: silent, seed: Date.now() % 100000,
  };
  const specFile = path.join(dir, 'render.json');
  fs.writeFileSync(specFile, JSON.stringify(spec, null, 2));
  log(`Drawing video (${total.toFixed(1)}s)...`);
  await run(PYTHON(), [path.join(ROOT, 'src', 'render.py'), specFile]);

  const music = path.join(dir, 'music.wav');
  await run(PYTHON(), [path.join(ROOT, 'src', 'music.py'), specFile, music]);
  const file = path.join(dir, 'final.mp4');
  const inputs = ['-i', silent, '-i', music];
  let filter;
  if (voice) {
    inputs.push('-i', voice.file);
    filter = `[2:a]aformat=sample_rates=48000:channel_layouts=stereo,adelay=${Math.round(VSTART * 1000)}:all=1,apad,asplit=2[v1][v2];` +
      `[1:a]volume=1.0[m];[m][v2]sidechaincompress=threshold=0.04:ratio=4:attack=30:release=600[md];` +
      `[md][v1]amix=inputs=2:duration=first:normalize=0,loudnorm=I=-14:TP=-1.5:LRA=9,aresample=48000[aout]`;
  } else {
    filter = '[1:a]loudnorm=I=-14:TP=-1.5,aresample=48000[aout]';
  }
  await run(FFMPEG(), ['-y', '-loglevel', 'error', ...inputs, '-filter_complex', filter, '-map', '0:v', '-map', '[aout]',
    '-c:v', 'copy', '-c:a', 'aac', '-b:a', '192k', '-ac', '2', '-t', total.toFixed(2), '-movflags', '+faststart', file]);
  for (const x of [silent, music]) fs.rmSync(x, { force: true });
  log(`Video ready: ${file}`);
  return { file, duration: total };
}

module.exports = { buildVideo };
