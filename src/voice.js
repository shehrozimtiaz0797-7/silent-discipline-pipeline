'use strict';
// Deep, calm narration with Gemini TTS (one request per video). Lowered pitch + light room for a cinematic feel.
const fs = require('fs');
const path = require('path');
const { env, log, run, duration, FFMPEG } = require('./lib');
const { speak } = require('./gemini');
const { withRetry } = require('./retry');

const TRIM = 'silenceremove=start_periods=1:start_threshold=-45dB,areverse,silenceremove=start_periods=1:start_threshold=-45dB,areverse';

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
    log(`Voice ready (${voice}, ${dur.toFixed(1)}s)`);
    return { file: wav, dur };
  } catch (e) {
    log(`Voice failed: ${String(e.message).slice(0, 200)}`);
    return null;
  }
}

module.exports = { makeVoice };
