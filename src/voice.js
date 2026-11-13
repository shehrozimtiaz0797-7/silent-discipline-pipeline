'use strict';
// Deep, calm narration with Gemini TTS (one request per video). Lowered pitch + light room for a cinematic feel.
const fs = require('fs');
const path = require('path');
const { env, log, run, duration, FFMPEG } = require('./lib');
const { speak } = require('./gemini');
const { withRetry } = require('./retry');

const TRIM = 'silenceremove=start_periods=1:start_threshold=-45dB,areverse,silenceremove=start_periods=1:start_threshold=-45dB,areverse';

// Finds where each line is spoken: the pauses between lines are the longest silences in the voice.
async function lineSegments(wav, dur, lines) {
  const { spawn } = require('child_process');
  const out = await new Promise(resolve => {
    const p = spawn(FFMPEG(), ['-hide_banner', '-i', wav, '-af', 'silencedetect=noise=-38dB:d=0.18', '-f', 'null', '-']);
    let err = ''; p.stderr.on('data', d => { err += d; }); p.on('close', () => resolve(err));
  });
  const gaps = []; let st = null;
  for (const line of out.split('\n')) {
    const a = line.match(/silence_start: ([\d.]+)/); const b = line.match(/silence_end: ([\d.]+)/);
    if (a) st = Number(a[1]);
    if (b && st !== null) { gaps.push({ start: st, end: Number(b[1]) }); st = null; }
  }
  const inner = gaps.filter(g => g.start > 0.3 && g.end < dur - 0.2);
  const need = lines.length - 1;
  if (inner.length < need) return null;
  const chosen = inner.slice().sort((x, y) => (y.end - y.start) - (x.end - x.start)).slice(0, need).sort((x, y) => x.start - y.start);
  const segs = [];
  let s0 = 0;
  for (const g of chosen) { segs.push({ start: s0, end: g.start }); s0 = g.end; }
  segs.push({ start: s0, end: dur });
  // sanity: each line's share of time should roughly follow its length
  const chars = lines.map(l => l.replace(/\*/g, '').length);
  const tot = chars.reduce((a, b) => a + b, 0);
  const bad = segs.some((sg, i) => { const share = (sg.end - sg.start) / dur; const want = chars[i] / tot; return share < want * 0.4 || share > want * 2.2; });
  return bad ? null : segs;
}

let turn = 0;
async function makeVoice(script, dir, n) {
  if (!env('GEMINI_API_KEY') || env('VOICE', 'on') === 'off') return null;
  const voices = env('GEMINI_TTS_VOICE', 'Charon,Orus,Algenib').split(',').map(s => s.trim()).filter(Boolean);
  const voice = voices[(n + turn++) % voices.length];
  // only the words: one sentence per line, with pauses between lines
  const text = script.lines.map(l => l.replace(/\*/g, '').replace(/([^.!?])$/, '$1.')).join('\n\n');
  try {
    const pcm = await withRetry('Voice', () => speak(text, voice), { tries: 2, waitMs: 20000, log });
    const raw = path.join(dir, 'voice.pcm'); const wav = path.join(dir, 'voice.wav');
    fs.writeFileSync(raw, pcm);
    const pitch = Number(env('VOICE_PITCH', '0.93')); const pace = Number(env('VOICE_PACE', '0.96'));
    await run(FFMPEG(), ['-y', '-loglevel', 'error', '-f', 's16le', '-ar', '24000', '-ac', '1', '-i', raw, '-af',
      `${TRIM},asetrate=${Math.round(24000 * pitch)},aresample=48000,atempo=${(pace / pitch).toFixed(4)},` +
      'highpass=f=70,equalizer=f=120:t=q:w=1:g=3,equalizer=f=3000:t=q:w=1.2:g=2,' +
      'acompressor=threshold=0.12:ratio=3:attack=5:release=90,aecho=0.8:0.6:40|70:0.18|0.10,loudnorm=I=-15:TP=-1.5',
      '-ar', '48000', wav]);
    fs.rmSync(raw, { force: true });
    const dur = await duration(wav);
    const segments = await lineSegments(wav, dur, script.lines);
    log(`Voice ready (${voice}, ${dur.toFixed(1)}s, lines found: ${segments ? 'yes' : 'estimated'})`);
    return { file: wav, dur, segments };
  } catch (e) {
    log(`Voice failed: ${String(e.message).slice(0, 200)}`);
    return null;
  }
}

module.exports = { makeVoice };
