"""Frame tools for the memory experiments (run with IncidentLens_08/.venv python).

  python frames.py hood  <video> <out_dir> <t0> <t1>      hood line from pixels that stay static while the car drives
  python frames.py grab  <video> <out_dir> <t0> <t1> <fps>  road-band frames t0..t1 at fps, ornament boxes grayed
  python frames.py still <video> <out_dir> <t> [...]        full frames (960 px) for Qwen to box the ornament

meta.json in out_dir holds hood_y and ornament_boxes (full-frame pixels) shared by every step.
"""
import json, sys
from pathlib import Path

import cv2
import numpy as np


def read(cap, t):
    cap.set(cv2.CAP_PROP_POS_FRAMES, round(t * cap.get(cv2.CAP_PROP_FPS)))
    ok, frame = cap.read()
    return frame if ok else None


def meta(out, **update):
    path = out / 'meta.json'
    data = json.loads(path.read_text()) if path.exists() else {}
    data.update(update)
    path.write_text(json.dumps(data, indent=2))
    return data


def hood(video, out, t0, t1):
    # Sample only a driving span: when the car stands still the whole scene is static too.
    cap = cv2.VideoCapture(str(video))
    small = [cv2.resize(f, (480, 270)).astype(np.float32) for f in (read(cap, t) for t in np.arange(t0, t1, 1 / 3)) if f is not None]
    static = np.std(np.stack(small), axis=0).max(axis=2) < 14
    rows = static.mean(axis=1)
    lower = np.arange(135, 270)
    hood_small = int(lower[np.argmax(rows[lower] >= 0.6)]) if (rows[lower] >= 0.6).any() else 270
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    # Texture-less asphalt (simulators) also looks static; a hood never reaches above 75% of the height.
    hood_y = max(round(hood_small * h / 270) - 10, int(0.75 * h))
    check = read(cap, (t0 + t1) / 2).copy()
    cv2.line(check, (0, hood_y), (check.shape[1], hood_y), (0, 0, 255), 4)
    cv2.imwrite(str(out / 'hood_check.jpg'), cv2.resize(check, (960, round(960 * h / check.shape[1]))))
    print('hood_y', meta(out, hood_y=hood_y, frame_h=h)['hood_y'])


def band(frame, m):
    # Road band from 30% of the height down to the hood line; ornament boxes grayed out.
    frame = frame.copy()
    for x1, y1, x2, y2 in m.get('ornament_boxes', []):
        frame[max(0, y1):y2, max(0, x1):x2] = 128
    return frame[int(0.30 * frame.shape[0]):m['hood_y']]


def grab(video, out, t0, t1, fps, sub='frames'):
    cap = cv2.VideoCapture(str(video))
    m = meta(out)
    (out / sub).mkdir(exist_ok=True)
    times = [round(t, 2) for t in np.arange(t0, t1 + 1e-6, 1 / fps)]
    for t in times:
        frame = read(cap, t)
        if frame is not None:
            cv2.imwrite(str(out / sub / f't{t:06.2f}.png'), band(frame, m))
    print('wrote', len(times), 'frames', t0, '->', t1, '@', fps, 'fps into', sub)


def still(video, out, times):
    cap = cv2.VideoCapture(str(video))
    (out / 'stills').mkdir(exist_ok=True)
    for t in times:
        cv2.imwrite(str(out / 'stills' / f's{t:06.2f}.png'), cv2.resize(read(cap, t), (960, 540)))


if __name__ == '__main__':
    cmd, video, out = sys.argv[1], Path(sys.argv[2]), Path(sys.argv[3])
    out.mkdir(parents=True, exist_ok=True)
    args = [float(a) for a in sys.argv[4:7 if cmd == 'grab' else None]]
    {'hood': lambda: hood(video, out, *args), 'grab': lambda: grab(video, out, *args, *(sys.argv[7:8])),
     'still': lambda: still(video, out, args)}[cmd]()
