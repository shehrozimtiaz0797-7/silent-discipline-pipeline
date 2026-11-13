'use strict';
// Writes one Silent Discipline short: an on-screen hook + 4-6 spoken lines in a calm stoic voice.
const fs = require('fs');
const path = require('path');
const { ROOT, log } = require('./lib');
const { askJSON } = require('./gemini');

const HISTORY = path.join(ROOT, 'history.json');
const THEMES = [
  'discipline when no one is watching', 'staying silent instead of explaining yourself', 'pain as a teacher',
  'losing people as you grow', 'doing the work when motivation is gone', 'controlling only what you can control',
  'being alone and becoming stronger', 'quiet confidence vs loud ego', 'delayed gratification', 'mornings and habits',
  'not reacting to insults', 'comparison and focusing on your own path', 'failure as data', 'time is running out',
  'your phone is stealing your life', 'rest is not quitting', 'small daily wins', 'fear and doing it anyway',
  'letting go of what you cannot change', 'keeping promises to yourself', 'being underestimated',
  'patience while results are invisible', 'the version of you in 5 years', 'comfort is the enemy',
];

function readHistory() { try { return JSON.parse(fs.readFileSync(HISTORY, 'utf8')); } catch (_) { return []; } }
function addHistory(entry) {
  const h = readHistory(); h.push(entry);
  fs.writeFileSync(HISTORY, JSON.stringify(h.slice(-400), null, 2));
}

const words = s => new Set(String(s).toLowerCase().replace(/[^a-z ]+/g, ' ').split(/\s+/).filter(w => w.length > 3));
function similar(a, b) {
  const A = words(a), B = words(b); if (!A.size || !B.size) return 0;
  let n = 0; for (const w of A) if (B.has(w)) n++;
  return n / (A.size + B.size - n);
}

function prompt(theme, past) {
  return `You write scripts for "Silent Discipline", a TikTok account of short stoic motivation videos.
Voice: calm, deep, slow, certain. Like an older mentor speaking quietly. Never shouting, never hype.

Theme for this video: ${theme}

Write ONE video:
- "hook": on-screen text shown at the top for the whole video, 3 to 7 words, in capital letters. It must create curiosity and be DIFFERENT from the spoken words (e.g. "NOBODY TELLS YOU THIS", "READ THIS TWICE", "IF YOU FEEL ALONE RIGHT NOW").
- "lines": 4 to 6 spoken lines, each 5 to 12 words, 40 to 60 words in total. Speak to the viewer as "you". The first line must grab attention on its own. The last line must land hard and be worth re-watching. In each line wrap exactly ONE key word in *asterisks* (it will be shown in gold).
- "caption": TikTok caption under 150 characters, then 5 hashtags (#stoic #discipline #motivation #selfimprovement and one more that fits).
- Everything must be ORIGINAL. Do not quote or name real people (no Marcus Aurelius, no Seneca, no celebrities). No religion, no politics, no money promises, no insults to any group, no "alpha male" or anti-women content, no self-harm.

Do not repeat ideas or opening lines from these recent videos:
${past || '- (none yet)'}

Return ONLY JSON: {"hook": "...", "lines": ["...", "..."], "caption": "..."}`;
}

function clean(s, theme) {
  const lines = (s.lines || []).map(l => String(l).replace(/\s+/g, ' ').trim()).filter(Boolean);
  const hook = String(s.hook || '').replace(/\s+/g, ' ').trim().toUpperCase();
  const plain = lines.map(l => l.replace(/\*/g, '')).join(' ');
  const n = plain.split(/\s+/).length;
  if (!hook || hook.split(' ').length > 8) throw new Error('bad hook');
  if (lines.length < 3 || lines.length > 7) throw new Error('need 4-6 lines');
  if (n < 25 || n > 75) throw new Error(`script is ${n} words`);
  if (/marcus|aurelius|seneca|epictetus|god\b|allah|jesus/i.test(plain + hook)) throw new Error('names or religion');
  return { theme, hook, lines, spoken: plain, caption: String(s.caption || '').trim().slice(0, 300) };
}

async function writeScript() {
  const hist = readHistory();
  const recentThemes = hist.slice(-12).map(h => h.theme);
  const options = THEMES.filter(t => !recentThemes.includes(t));
  const past = hist.slice(-25).map(h => `- ${h.lines[0].replace(/\*/g, '')}`).join('\n');
  let lastErr;
  for (let i = 1; i <= 5; i++) {
    const theme = options[Math.floor(Math.random() * options.length)] || THEMES[0];
    try {
      const s = clean(await askJSON(prompt(theme, past), { temperature: 1.0 }), theme);
      const close = hist.slice(-200).find(h => similar(h.spoken, s.spoken) > 0.4);
      if (close) throw new Error('too close to an earlier video');
      log(`Script ready (${theme}): ${s.hook} | ${s.spoken}`);
      return s;
    } catch (e) {
      lastErr = e; log(`Script try ${i} rejected: ${String(e.message).slice(0, 160)}`);
      if (/quota|RESOURCE_EXHAUSTED|API key/i.test(e.message)) break;
    }
  }
  throw lastErr;
}

module.exports = { writeScript, addHistory, readHistory };
