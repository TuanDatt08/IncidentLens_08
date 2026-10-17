"""Ask Qwen once per video for objects attached to the camera car (windshield ornament etc.).
Union of boxes over the stills + margin -> meta.json ornament_boxes (full-frame pixels).

  python ornament.py <out_dir> <frame_w> <frame_h>
"""
import json, sys
from pathlib import Path

from qwen import BOX, TEXT, chat, obj, to_pixels

out, fw, fh = Path(sys.argv[1]), int(sys.argv[2]), int(sys.argv[3])
PROMPT = ('This is a frame from a dashcam mounted inside a car, looking forward through the windshield. '
          'Find objects attached to the camera car itself: hanging ornaments, decorations, toys, stickers or phone holders on or behind the windshield. '
          'Do not include the hood, the road, or vehicles and people outside the car. First say what you found, then output one bounding box per object '
          'in pixel coordinates of this image (empty list if none).')
boxes = []
for still in sorted((out / 'stills').glob('s*.png')):
    answer, _, _, wall = chat(PROMPT, [still], obj(a_found=TEXT, b_boxes={'type': 'array', 'items': BOX}), num_predict=150)
    found = [to_pixels(b, 960, 540) for b in answer.get('b_boxes', []) if b[2] > b[0] and b[3] > b[1]]
    print(still.name, wall, 's', answer.get('a_found'), found, flush=True)
    boxes += [[round(v * fw / 960) if i % 2 == 0 else round(v * fh / 540) for i, v in enumerate(b)] for b in found]
# Ignore huge boxes (whole hood / whole frame) and merge the rest into one padded region per video.
small = [b for b in boxes if (b[2] - b[0]) * (b[3] - b[1]) < 0.08 * fw * fh]
merged = [[max(0, min(b[0] for b in small) - 30), max(0, min(b[1] for b in small) - 30),
           min(fw, max(b[2] for b in small) + 30), min(fh, max(b[3] for b in small) + 30)]] if small else []
meta_path = out / 'meta.json'
meta = json.loads(meta_path.read_text())
meta.update(ornament_boxes=merged, ornament_raw_boxes=boxes)
meta_path.write_text(json.dumps(meta, indent=2))
print('ornament_boxes', merged)
