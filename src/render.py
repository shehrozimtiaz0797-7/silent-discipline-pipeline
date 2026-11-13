"""Silent Discipline: draws a dark cinematic quote Short frame by frame and pipes it to ffmpeg.
Scene: night mountains with fog and moon (sometimes rain), a lone figure on the ridge.
Opening: the hook fills the screen with an impact, then moves to the top.
Captions: word by word as the voice speaks, one gold key word per line, impact shake on the last line.
Usage: python render.py spec.json
"""
import json
import math
import random
import subprocess
import sys

from PIL import Image, ImageDraw, ImageFilter, ImageFont

spec = json.load(open(sys.argv[1], encoding="utf-8"))
W, H, FPS = 1080, 1920, 30
GOLD = (214, 178, 108)
WHITE = (240, 235, 224)
rng = random.Random(spec.get("seed", 1))
LORA, BOLD = spec["font_serif"], spec["font_bold"]
_f = {}


def font(size, serif=True, weight="SemiBold"):
    k = (size, serif, weight)
    if k not in _f:
        f = ImageFont.truetype(LORA if serif else BOLD, size)
        if serif:
            try:
                f.set_variation_by_name(weight)
            except Exception:
                pass
        _f[k] = f
    return _f[k]


def layer(w, h):
    return Image.new("RGBA", (w, h), (0, 0, 0, 0))


def with_alpha(img, a):
    if a >= 0.999:
        return img
    r, g, b, al = img.split()
    return Image.merge("RGBA", (r, g, b, al.point(lambda v: int(v * max(0.0, a)))))


def ease(x):
    x = max(0.0, min(1.0, x))
    return 1 - (1 - x) ** 3


def mix(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def shadowed(img, blur=10, a=0.9):
    sh = layer(*img.size)
    sh.paste((0, 0, 0, int(255 * a)), (0, 0), img.split()[3])
    out = sh.filter(ImageFilter.GaussianBlur(blur))
    out.alpha_composite(img)
    return out


# ---------- scene ----------
scene = spec.get("scene") or rng.choice(["dusk", "night", "rain"])
sky_top, sky_bot = {"dusk": ((14, 10, 12), (70, 42, 26)), "night": ((6, 8, 14), (28, 30, 44)), "rain": ((8, 9, 12), (34, 36, 40))}[scene]
sky = Image.new("RGB", (W, H))
sd = ImageDraw.Draw(sky)
for y in range(H):
    sd.line([(0, y), (W, y)], fill=mix(sky_top, sky_bot, min(1, y / (H * 0.75))))
sky = sky.convert("RGBA")
# moon / sun glow
glow = Image.new("L", (300, 300), 0)
ImageDraw.Draw(glow).ellipse([60, 60, 240, 240], fill=255)
glow = glow.filter(ImageFilter.GaussianBlur(40)).resize((1100, 1100), Image.BILINEAR)
moon_col = (255, 196, 120) if scene == "dusk" else (190, 200, 230)
moon = Image.new("RGBA", glow.size, moon_col + (255,))
moon.putalpha(glow.point(lambda v: int(v * (0.7 if scene == "dusk" else 0.5))))
disc = Image.new("RGBA", (130, 130), (0, 0, 0, 0))
ImageDraw.Draw(disc).ellipse([0, 0, 129, 129], fill=tuple(min(255, c + 40) for c in moon_col) + (245 if scene != "rain" else 140,))
moon.alpha_composite(disc, (485, 485))
MOON_X, MOON_Y = rng.choice([0.3, 0.68]) * W, H * 0.665  # rising behind the far ridge


def ridge(base_y, amp, rough, col, seed, width):
    r = random.Random(seed)
    ph = [r.uniform(0, 6.28) for _ in range(5)]
    img = layer(width, H)
    pts = []
    for x in range(0, width + 8, 8):
        y = base_y
        for i, (fr, a) in enumerate([(0.0016, 1.0), (0.0041, 0.5), (0.011, 0.22), (0.027, 0.1), (0.06, 0.05)]):
            y -= amp * a * math.sin(x * fr * rough + ph[i])
        pts.append((x, y))
    ImageDraw.Draw(img).polygon(pts + [(width, H), (0, H)], fill=col + (255,))
    return img, pts


PW = int(W * 1.35)
far = sky_bot
layers = []
for i, (by, amp, k) in enumerate([(1240, 170, 0.8), (1330, 150, 1.0), (1440, 130, 1.2), (1560, 110, 1.4)]):
    col = mix(tuple(min(255, int(c * 1.25)) for c in far), (3, 3, 5), 0.2 + 0.26 * i)
    img, pts = ridge(by, amp, k, col, rng.randint(0, 10 ** 6), PW)
    layers.append((img, 6 + 14 * i, pts))
# lone figure on the nearest ridge
near_img, near_pts = layers[-1][0], layers[-1][2]
peak = min(near_pts[len(near_pts) // 4: 3 * len(near_pts) // 4], key=lambda p: p[1])
fd = ImageDraw.Draw(near_img)
fx, fy = peak
c = (3, 3, 5, 255)
fd.ellipse([fx - 9, fy - 92, fx + 9, fy - 74], fill=c)
fd.polygon([(fx - 11, fy - 74), (fx + 11, fy - 74), (fx + 20, fy - 2), (fx - 20, fy - 2)], fill=c)
fd.polygon([(fx + 11, fy - 70), (fx + 40, fy - 30), (fx + 18, fy - 20)], fill=c)  # cloak in the wind

# fog bands
fogs = []
for i in range(3):
    f = layer(PW, 260)
    ImageDraw.Draw(f).ellipse([0, 60, PW, 200], fill=(200, 200, 210, 34))
    fogs.append((f.filter(ImageFilter.GaussianBlur(40)), 1250 + i * 120, 8 + 10 * i))

# readability: darken behind the text block
shade = Image.new("L", (W // 4, H // 4), 0)
ImageDraw.Draw(shade).rectangle([0, int(H / 4 * 0.12), W // 4, int(H / 4 * 0.70)], fill=150)
shade = shade.filter(ImageFilter.GaussianBlur(40)).resize((W, H), Image.BILINEAR)
shade_l = Image.new("RGBA", (W, H), (0, 0, 0, 255))
shade_l.putalpha(shade)
vs = 4
vm = Image.new("L", (W // vs, H // vs), 255)
ImageDraw.Draw(vm).ellipse([W // vs * 0.04, H // vs * 0.10, W // vs * 0.96, H // vs * 0.90], fill=0)
vm = vm.filter(ImageFilter.GaussianBlur(60)).resize((W, H), Image.BILINEAR)
vignette = Image.new("RGBA", (W, H), (0, 0, 0, 255))
vignette.putalpha(vm.point(lambda v: int(v * 0.8)))
grains = []
for i in range(6):
    g = Image.effect_noise((W // 2, H // 2), 40).resize((W, H), Image.NEAREST)
    gl = Image.new("RGBA", (W, H), (255, 255, 255, 255))
    gl.putalpha(g.point(lambda v: max(0, v - 128) // 6))
    grains.append(gl)
dust = [(rng.uniform(0, W), rng.uniform(0, H), rng.uniform(6, 22), rng.choice([1, 2, 2, 3]), rng.uniform(0, 6.28)) for _ in range(60)]
rain = [(rng.uniform(0, W * 1.2), rng.uniform(0, H), rng.uniform(1500, 2300), rng.uniform(30, 70)) for _ in range(160)] if scene == "rain" else []

TOTAL = float(spec["total"])


def background(t):
    fr = sky.copy()
    fr.alpha_composite(moon, (int(MOON_X - moon.size[0] / 2 + 10 * math.sin(t * 0.1)), int(MOON_Y - moon.size[1] / 2 - 25 * t / TOTAL)))
    p = t / TOTAL
    for img, speed, _ in layers:
        fr.alpha_composite(img, (int(-(PW - W) / 2 - speed * p * 4 + speed * 2), int(-speed * p * 1.2)))
    for f, y, sp in fogs:
        fr.alpha_composite(f, (int(-(PW - W) / 2 + math.sin(t * 0.08 * sp / 8) * 80), y))
    d = ImageDraw.Draw(fr)
    for x0, y0, sp, r, ph in dust:
        y = (y0 - sp * t) % H
        x = x0 + 10 * math.sin(t * 0.6 + ph)
        a = 0.3 + 0.3 * math.sin(t * 1.3 + ph)
        d.ellipse([x - r, y - r, x + r, y + r], fill=tuple(int(c * a) for c in GOLD) + (255,))
    for x0, y0, sp, ln in rain:
        y = (y0 + sp * t) % (H + 100) - 100
        x = x0 - 0.25 * (y - y0)
        d.line([(x, y), (x - ln * 0.25, y + ln)], fill=(150, 160, 175, 255), width=2)
    fr.alpha_composite(shade_l)
    fr.alpha_composite(vignette)
    fr.alpha_composite(grains[int(t * FPS) % len(grains)])
    return fr


# ---------- text: word by word ----------
lines = spec["lines"]
starts = spec["line_starts"]
voice_end = float(spec["voice_end"])
size = 70 if sum(len(l) for l in lines) < 240 else 62
F = font(size)
SPACE = F.getlength(" ")
LH = int(size * 1.3)
MAXW = W - 170


def parse(text):
    out, in_gold = [], False
    for raw in text.split():
        s, e = raw.startswith("*"), raw.endswith("*") and len(raw) > 1
        out.append((raw.replace("*", ""), in_gold or s))
        if s and not e:
            in_gold = True
        if e:
            in_gold = False
    return out


word_cache = {}


def word_img(w, gold):
    k = (w, gold)
    if k not in word_cache:
        fw = font(size, weight="Bold" if gold else "SemiBold")
        wl = int(fw.getlength(w)) + 30
        im = layer(wl, LH + 30)
        ImageDraw.Draw(im).text((15, 15 + LH / 2), w, font=fw, fill=(GOLD if gold else WHITE) + (255,), anchor="lm")
        word_cache[k] = shadowed(im, 8, 0.95)
    return word_cache[k]


blocks = []  # per line: list of (img, x, row, t_appear, gold)
for i, text in enumerate(lines):
    toks = parse(text)
    rows, cur, cw = [], [], 0
    for w, g in toks:
        wl = F.getlength(w)
        if cur and cw + SPACE + wl > MAXW:
            rows.append((cur, cw))
            cur, cw = [], 0
        cur.append((w, g, wl))
        cw += (SPACE if cw else 0) + wl
    rows.append((cur, cw))
    t0 = starts[i]
    ends_ = spec.get("line_ends")
    t1 = ends_[i] if ends_ else (starts[i + 1] if i + 1 < len(starts) else voice_end)
    span = max(0.5, (t1 - t0) * (0.92 if ends_ else 0.85))
    total_chars = sum(len(w) + 2 for w, _ in toks)
    acc = 0
    items = []
    for r, (row, rw) in enumerate(rows):
        x = (W - rw) / 2
        for w, g, wl in row:
            items.append((word_img(w, g), x - 15, r, t0 + span * acc / total_chars, g))
            acc += len(w) + 2
            x += wl + SPACE
    blocks.append((items, len(rows)))

GAP = 30
heights = [n * LH for _, n in blocks]
total_h = sum(heights) + GAP * (len(blocks) - 1)
top = int(H * 0.47 - total_h / 2)
ys, y = [], top
for h in heights:
    ys.append(y)
    y += h + GAP

# hook: big in the middle first, then small at the top
hook = spec["hook"]


def hook_image(sz, color):
    fh = font(sz, serif=False)
    words_ = hook.split()
    rows, cur = [], ""
    for w in words_:
        test = (cur + " " + w).strip()
        if fh.getlength(test) > W - 140 and cur:
            rows.append(cur)
            cur = w
        else:
            cur = test
    rows.append(cur)
    rows = rows[:3]
    lh = int(sz * 1.15)
    im = layer(W, lh * len(rows) + 40)
    d = ImageDraw.Draw(im)
    for i, r in enumerate(rows):
        d.text((W // 2, 20 + i * lh + lh // 2), r, font=fh, fill=color + (255,), anchor="mm")
    d.line([(W // 2 - 70, im.size[1] - 8), (W // 2 + 70, im.size[1] - 8)], fill=GOLD + (230,), width=4)
    return shadowed(im, 12, 0.95)


hook_big = hook_image(104, WHITE)
hook_small = hook_image(52, GOLD)
brand = layer(W, 60)
ImageDraw.Draw(brand).text((W // 2, 30), "S I L E N T   D I S C I P L I N E", font=font(26, serif=False), fill=(170, 160, 140, 255), anchor="mm")
INTRO = float(spec.get("intro", 1.6))
LAST = starts[-1]

frames = int(TOTAL * FPS)
ff = subprocess.Popen([spec["ffmpeg"], "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS),
                       "-i", "-", "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p", spec["out"]], stdin=subprocess.PIPE)
for n in range(frames):
    t = n / FPS
    fr = background(t)
    # shake on the last line
    sx = sy = 0
    if LAST <= t < LAST + 0.35:
        k = 1 - (t - LAST) / 0.35
        sx, sy = int(rng.uniform(-10, 10) * k), int(rng.uniform(-10, 10) * k)
    # hook
    if t < INTRO:
        s = 1.25 - 0.25 * ease(t / 0.35)
        im = hook_big.resize((int(hook_big.size[0] * s), int(hook_big.size[1] * s)), Image.BILINEAR) if abs(s - 1) > 0.01 else hook_big
        fr.alpha_composite(with_alpha(im, ease(t / 0.2)), (int((W - im.size[0]) / 2), int(H * 0.45 - im.size[1] / 2)))
    elif t < INTRO + 0.45:
        k = ease((t - INTRO) / 0.45)
        fr.alpha_composite(with_alpha(hook_big, 1 - k), (0, int(H * 0.45 - hook_big.size[1] / 2 - k * 300)))
        fr.alpha_composite(with_alpha(hook_small, k), (0, 250))
    else:
        fr.alpha_composite(hook_small, (0, 250))
    fr.alpha_composite(brand, (0, 1590))
    # words
    current = max([i for i, s in enumerate(starts) if t >= s] or [-1])
    for i, (items, _) in enumerate(blocks):
        if t < starts[i] - 0.05:
            continue
        dim = 1.0
        if i < current:
            dim = max(0.35, 1 - 0.65 * ease((t - starts[i + 1]) / 0.5))
        for im, x, r, ta, gold in items:
            if t < ta:
                continue
            a = ease((t - ta) / 0.18) * dim
            pop = 1.0
            if gold and t - ta < 0.3:
                pop = 1 + 0.22 * (1 - ease((t - ta) / 0.3))
            img = im if pop == 1.0 else im.resize((int(im.size[0] * pop), int(im.size[1] * pop)), Image.BILINEAR)
            dx = (img.size[0] - im.size[0]) / 2
            dy = (img.size[1] - im.size[1]) / 2 + 10 * (1 - ease((t - ta) / 0.18))
            fr.alpha_composite(with_alpha(img, a), (int(x - dx + sx), int(ys[i] + r * LH - 15 - dy + sy)))
    if t < 0.12 or (LAST <= t < LAST + 0.15):
        k = (0.12 - t) / 0.12 if t < 0.12 else 1 - (t - LAST) / 0.15
        fr = Image.blend(fr, Image.new("RGBA", (W, H), (255, 245, 225, 255)), 0.28 * max(0, k))
    if t > TOTAL - 0.8:
        fr = Image.blend(fr, Image.new("RGBA", (W, H), (0, 0, 0, 255)), min(1.0, (t - (TOTAL - 0.8)) / 0.8) * 0.9)
    ff.stdin.write(fr.convert("RGB").tobytes())
ff.stdin.close()
sys.exit(ff.wait())
