"""Video-only two-tier pipeline (QWEN_VIDEO_PIPELINE=two_tier).

Tuned in docs/external-qwen/INC-4043C786F1C4/local-q8-memory (results.md):
1. Road band frames every 0.6 s: hood cut from pixels that stay static while the car moves,
   windshield ornament boxed once per video by Qwen and grayed out.
2. Tier 1: windows of 4 frames (stride 2) answered A normal / B near miss / C fall or collision / D empty.
3. Backend memory (<job>.two-tier.json) keeps every answer; old answers are never fed back to the model.
4. Rules: B needs >= 2 consecutive windows and a tier-2 answer other than A; it is high confidence when
   a strict distance re-check keeps >= 2 consecutive windows, else "review". C needs tier 2 to answer C.
5. Tier 2: Qwen boxes the main road user in 4 fps frames; one fixed crop window around its boxes; same question.
Only the frames are sent to the model; FFmpeg does every image operation.
"""
from __future__ import annotations

import base64
import json
import math
import re
import time
from pathlib import Path

import httpx

from backend.models.contracts import AnalysisResult
from backend.services.pipeline_status import update_status
from backend.services.processing import InsufficientEvidence, ProcessedResult, _evidence
from backend.services.qwen_local import ensure_ollama_runtime, validate_local_endpoint
from backend.services.video import VideoService

STEP_S, WINDOW, STRIDE = 0.6, 4, 2
TEXT = {'type': 'string'}
BOX = {'type': 'array', 'items': {'type': 'integer'}, 'minItems': 4, 'maxItems': 4}
ACTORS = ['none', 'pedestrian', 'motorcycle', 'bicycle', 'car', 'truck']
ACTOR_WORDS = {'motorcycle': ('motorcycl', 'scooter', 'motorbike'), 'bicycle': ('bicycl', 'cyclist'),
               'pedestrian': ('pedestrian', 'person', 'woman', ' man ', 'people'), 'car': ('car', 'suv', 'sedan', 'van'), 'truck': ('truck', 'bus')}


def obj(**props):
    # Ollama emits keys alphabetically, so a_* (observation) is generated before b_* (verdict).
    return {'type': 'object', 'required': list(props), 'properties': props, 'additionalProperties': False}


CHOICE = obj(a_description=TEXT, b_choice={'enum': ['A', 'B', 'C', 'D']})
OPTIONS = ('A) normal traffic: road users keep to their own paths, nothing dangerous\n'
           'B) a road user suddenly enters or crosses the camera car\'s path close ahead, or swerves hard (near miss)\n'
           'C) a road user falls or tips over, or there is contact or a collision\n'
           'D) no road users near the camera car\'s path')
STRICT_OPTIONS = ('A) not dangerous: normal traffic, lane changes, merges, turns or crossings that stay at a safe distance (more than about two car lengths ahead, or in another lane)\n'
                  'B) dangerous near miss: a road user comes within about two car lengths directly in front of the camera car, cutting into or crossing its lane, so the camera car must brake hard or swerve\n'
                  'C) a road user falls or tips over, or there is contact or a collision\n'
                  'D) no road users near the camera car\'s path')


def question(times, what='frames', strict=False):
    focus = ('the road user that comes closest to the camera car and how close it gets' if strict
             else 'what the road users near the camera car\'s path do across the frames')
    return (f'These are consecutive {what} from a forward dashcam on a camera car, in time order (t = {", ".join(f"{t:.2f}s" for t in times)}). '
            f'Gray boxes are masks; ignore them. First describe in at most 40 words {focus}, then choose:\n' + (STRICT_OPTIONS if strict else OPTIONS))


def smart_resize(w, h, factor=28, min_pixels=1024 * 28 * 28):
    wb, hb = round(w / factor) * factor, round(h / factor) * factor
    if wb * hb < min_pixels:
        beta = math.sqrt(min_pixels / (w * h))
        wb, hb = math.ceil(w * beta / factor) * factor, math.ceil(h * beta / factor) * factor
    return wb, hb


def to_pixels(model: str, box: list[int], w: int, h: int) -> list[int]:
    """Qwen3.x grounds in relative 0-1000 coordinates; Qwen2.5-VL in pixels of its resized input."""
    if model.startswith('qwen3'):
        return [round(v * (w if i % 2 == 0 else h) / 1000) for i, v in enumerate(box)]
    rw, rh = smart_resize(w, h)
    return [round(v * (w / rw if i % 2 == 0 else h / rh)) for i, v in enumerate(box)]


DANGER = re.compile(r'cross|run|into the (street|road|lane)|in front of|fall|fell|swerv|collid|tip|cut|enter', re.I)


def named_actors(text: str) -> list[str]:
    """Actors the tier-1 descriptions name, the ones in danger sentences first ("runs into the street",
    "falls off"), so tier 2 crops the road user doing the dangerous thing, not one merely in view."""
    sentences = [s for s in text.lower().replace('camera car', '').split('.') if s.strip()]
    score = {actor: sum(bool(DANGER.search(s)) for s in sentences if any(w in s for w in words)) for actor, words in ACTOR_WORDS.items()
             if any(w in s for s in sentences for w in words)}
    return sorted(score, key=lambda actor: -score[actor])   # stable: ties keep ACTOR_WORDS order


def runs(windows: list[dict], key: str = 'choice') -> list[list[dict]]:
    """Consecutive windows whose answer is B or C."""
    found, current = [], []
    for window in [*windows, {key: 'A'}]:
        if window.get(key) in ('B', 'C'):
            current.append(window)
        elif current:
            found.append(current)
            current = []
    return found


def classify(run: list[dict], tier2_choice: str) -> dict | None:
    """Rule engine on one run of flagged tier-1 windows (see module docstring)."""
    c_windows = [w for w in run if w['choice'] == 'C']
    if c_windows and tier2_choice == 'C':
        return {'kind': 'FALL_OR_COLLISION', 'confidence': 'high'}
    if len(run) < 2 or tier2_choice not in ('B', 'C'):
        return None
    strict_runs = runs([{**w, 'strict': w['choice'] if w['choice'] == 'C' else w.get('strict')} for w in run], 'strict')
    return {'kind': 'NEAR_MISS', 'confidence': 'high' if any(len(r) >= 2 for r in strict_runs) else 'review'}


def incident_type(kind: str, actor: str | None) -> str:
    if kind == 'FALL_OR_COLLISION':
        return 'LOSS_OF_CONTROL' if actor in ('motorcycle', 'bicycle') else 'COLLISION'
    return 'PEDESTRIAN_CONFLICT' if actor == 'pedestrian' else 'NEAR_COLLISION'


class TwoTier:
    def __init__(self, incident, *, root, settings, job_id, on_progress):
        self.settings, self.job_id, self.on_progress = settings, job_id, on_progress
        self.root = root
        self.output = root / incident['incident_id'] / 'output'
        self.work = self.output / 'two_tier'
        self.source = (root / incident['video_uri']).resolve()
        if root not in self.source.parents:
            raise ValueError('video outside storage')
        meta = incident['video_metadata']
        self.duration, self.width, self.height = float(meta['duration']), int(meta['width']), int(meta['height'])
        self.service = VideoService(settings.ffprobe_bin, settings.ffmpeg_bin, max_output_bytes=2 * 1024**3)
        self.memory = {'pipeline': 'two_tier_v1', 'model': settings.qwen_ollama_model, 'endpoint': settings.qwen_endpoint, 'calls': 0, 'windows': [], 'events': []}
        self.memory_path = self.output / f'{job_id}.two-tier.json'

    def status(self, stage, message, **details):
        update_status(self.output, self.job_id, stage, message, **details)

    def save(self):
        self.service.write_json(self.memory_path, self.memory)

    def ask(self, text: str, images: list[Path], schema: dict, max_tokens: int = 200) -> dict:
        # Native /api/chat on the same host as QWEN_ENDPOINT (local Ollama or the GPU tunnel). Measured on the
        # same frames and prompt: /v1/chat/completions adds ~20 template tokens and flips calm windows from A
        # to B; the thresholds in this module were validated on /api/chat.
        parsed = validate_local_endpoint(self.settings.qwen_endpoint)
        payload = {'model': self.settings.qwen_ollama_model, 'stream': False, 'format': schema,
                   'options': {'temperature': 0, 'seed': 42, 'num_ctx': 12288, 'num_predict': max_tokens},
                   'messages': [{'role': 'user', 'content': text, 'images': [base64.b64encode(p.read_bytes()).decode() for p in images]}],
                   **({'think': self.settings.qwen_reasoning_effort != 'none'} if self.settings.qwen_reasoning_effort else {})}
        self.memory['calls'] += 1
        if self.memory['calls'] > 400:
            raise InsufficientEvidence('Model call budget exhausted for the two-tier pipeline.')
        with httpx.Client(trust_env=False, timeout=self.settings.qwen_timeout_s, follow_redirects=False) as client:
            response = client.post(f'{parsed.scheme}://{parsed.netloc}/api/chat', json=payload)
            response.raise_for_status()
        raw = response.json()['message']['content']
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return {'unparsed': raw}

    # --- preprocessing -------------------------------------------------------------------------
    def hood_line(self) -> int:
        """First lower-half row where >= 60% of pixels barely change while the car moves; never above 75%."""
        cols, rows_n = 160, 90
        times = [t for t in (0.5 + i for i in range(min(60, int(self.duration)))) if t < self.duration - 0.2]
        frames = []
        for i, t in enumerate(times):
            path = self.service.extract_frame(self.source, t, self.work / 'hood' / f'{i:03d}.pgm', video_filter=f'scale={cols}:{rows_n},format=gray')
            data = path.read_bytes()[-cols * rows_n:]   # binary PGM: short text header, then one byte per pixel
            if len(data) == cols * rows_n:
                frames.append(data)
        if len(frames) < 4:
            return int(0.75 * self.height)
        moves = [sum(abs(a - b) for a, b in zip(x, y)) / len(x) for x, y in zip(frames, frames[1:])]
        cut = sorted(moves)[len(moves) // 2]
        moving = sorted({j for i, m in enumerate(moves) if m >= cut for j in (i, i + 1)})
        chosen = [frames[i] for i in moving] if len(moving) >= 4 else frames
        static_rows = []
        for r in range(rows_n):
            still = 0
            for c in range(cols):
                values = [f[r * cols + c] for f in chosen]
                mean = sum(values) / len(values)
                still += (sum((v - mean) ** 2 for v in values) / len(values)) ** 0.5 < 10
            static_rows.append(still / cols)
        hood_small = next((r for r in range(rows_n // 2, rows_n) if static_rows[r] >= 0.6), rows_n)
        return max(round(hood_small * self.height / rows_n) - 10, int(0.75 * self.height))

    def ornament_boxes(self) -> list[list[int]]:
        """Ask Qwen once per video (3 stills) for objects attached to the camera car; union + 30 px."""
        prompt = ('This is a frame from a dashcam mounted inside a car, looking forward through the windshield. '
                  'Find objects attached to the camera car itself: hanging ornaments, decorations, toys, stickers or phone holders on or behind the windshield. '
                  'Do not include the hood, the road, or vehicles and people outside the car. First say what you found, then output one bounding box per object '
                  'in pixel coordinates of this image (empty list if none).')
        sw, sh = 960, round(960 * self.height / self.width / 2) * 2
        boxes = []
        for i, frac in enumerate((0.25, 0.5, 0.75)):
            still = self.service.extract_frame(self.source, self.duration * frac, self.work / 'stills' / f's{i}.jpg', video_filter=f'scale={sw}:{sh}')
            answer = self.ask(prompt, [still], obj(a_found=TEXT, b_boxes={'type': 'array', 'items': BOX}), max_tokens=200)
            for box in answer.get('b_boxes', []):
                if len(box) == 4 and box[2] > box[0] and box[3] > box[1]:
                    x1, y1, x2, y2 = to_pixels(self.settings.qwen_ollama_model, box, sw, sh)
                    boxes.append([round(x1 * self.width / sw), round(y1 * self.height / sh), round(x2 * self.width / sw), round(y2 * self.height / sh)])
        small = [b for b in boxes if (b[2] - b[0]) * (b[3] - b[1]) < 0.08 * self.width * self.height]
        if not small:
            return []
        return [[max(0, min(b[0] for b in small) - 30), max(0, min(b[1] for b in small) - 30),
                 min(self.width, max(b[2] for b in small) + 30), min(self.height, max(b[3] for b in small) + 30)]]

    def band(self, at: float, destination: Path) -> Path:
        top = int(0.30 * self.height)
        masks = [f'drawbox=x={x1}:y={y1}:w={x2 - x1}:h={y2 - y1}:color=gray:t=fill' for x1, y1, x2, y2 in self.memory['ornament_boxes']]
        return self.service.extract_frame(self.source, at, destination, video_filter=','.join([*masks, f'crop={self.width}:{self.memory["hood_y"] - top}:0:{top}']))

    # --- tiers ---------------------------------------------------------------------------------
    def tier1(self):
        times = [round(0.3 + STEP_S * i, 2) for i in range(int((self.duration - 0.6) / STEP_S) + 1)]
        frames = [(t, self.band(t, self.work / 'scan' / f't{t:07.2f}.jpg')) for t in times]
        groups = [frames[i:i + WINDOW] for i in range(0, len(frames) - WINDOW + 1, STRIDE)]
        for n, group in enumerate(groups):
            answer = self.ask(question([t for t, _ in group]), [p for _, p in group], CHOICE)
            self.memory['windows'].append({'start_s': group[0][0], 'end_s': group[-1][0], 'frames': [p.relative_to(self.root).as_posix() for _, p in group],
                                           'choice': answer.get('b_choice', '?'), 'description': answer.get('a_description', answer.get('unparsed', ''))})
            self.on_progress(1, n + 1, len(groups))
            self.save()

    def strict(self, window: dict):
        paths = [self.root / p for p in window['frames']]
        answer = self.ask(question([float(Path(p).stem[1:]) for p in window['frames']], strict=True), paths, CHOICE)
        window['strict'], window['strict_description'] = answer.get('b_choice', '?'), answer.get('a_description', '')

    def tier2(self, t0: float, t1: float, hint: str, tag: str) -> dict:
        fps = min(4.0, 5 / max(0.5, t1 - t0))
        times = [round(t0 + i / fps, 2) for i in range(int((t1 - t0) * fps) + 1)]
        frames = [(t, self.band(t, self.work / tag / f't{t:07.2f}.jpg')) for t in times]
        bw, bh = self.width, self.memory['hood_y'] - int(0.30 * self.height)
        found = []
        for _, path in frames:
            answer = self.ask('Find the road user (vehicle, motorcycle, bicycle or pedestrian) closest to the camera car\'s path ahead. '
                              'Gray boxes are masks; ignore them. Give its type and its bounding box in pixel coordinates of this image; '
                              'type none and [0,0,0,0] if there is none.', [path], obj(a_actor={'enum': ACTORS}, b_bbox=BOX), max_tokens=80)
            box = answer.get('b_bbox', [0, 0, 0, 0])
            if answer.get('a_actor', 'none') != 'none' and len(box) == 4 and box[2] > box[0] and box[3] > box[1]:
                found.append((answer['a_actor'], to_pixels(self.settings.qwen_ollama_model, box, bw, bh)))
        if not found:
            return {'actor': None, 'choice': 'D', 'description': 'no road user found', 'crops': []}
        seen = [actor for actor, _ in found]
        actor = next((a for a in named_actors(hint) if a in seen), None) or max(set(seen), key=seen.count)
        boxes = [b for a, b in found if a == actor]
        x1, y1, x2, y2 = min(b[0] for b in boxes), min(b[1] for b in boxes), max(b[2] for b in boxes), max(b[3] for b in boxes)
        cx, cy, hw, hh = (x1 + x2) / 2, (y1 + y2) / 2, max(160, 0.65 * (x2 - x1)), max(120, 0.65 * (y2 - y1))
        x0, y0 = int(max(0, cx - hw)), int(max(0, cy - hh))
        cw, ch = int(min(bw, cx + hw)) - x0, int(min(bh, cy + hh)) - y0
        scale = 'scale=720:-2' if cw >= ch else 'scale=-2:720'
        crops = [(t, self.service.extract_frame(p, 0, self.work / tag / f'crop_t{t:07.2f}.jpg', video_filter=f'crop={cw}:{ch}:{x0}:{y0},{scale}')) for t, p in frames]
        answer = self.ask(question([t for t, _ in crops], 'crops around the main road user'), [p for _, p in crops], CHOICE)
        return {'actor': actor, 'choice': answer.get('b_choice', '?'), 'description': answer.get('a_description', answer.get('unparsed', '')),
                'crops': [[t, p.relative_to(self.root).as_posix()] for t, p in crops]}

    def run(self) -> ProcessedResult:
        ensure_ollama_runtime(self.settings)
        validate_local_endpoint(self.settings.qwen_endpoint)
        self.status('backend', 'Two-tier: cắt dải đường, tìm mép capo và vật gắn trên kính.')
        self.memory['hood_y'] = self.hood_line()
        self.memory['ornament_boxes'] = self.ornament_boxes()
        self.save()
        self.status('qwen', 'Two-tier tầng 1: quét cửa sổ 4 frame trên toàn video.', model=self.settings.qwen_ollama_model, hood_y=self.memory['hood_y'], ornament_boxes=self.memory['ornament_boxes'])
        started = time.monotonic()
        self.tier1()
        for run in runs(self.memory['windows']):
            c_windows = [w for w in run if w['choice'] == 'C']
            if len(run) < 2 and not c_windows:
                continue
            for window in run:
                if window['choice'] == 'B' and 'strict' not in window:
                    self.strict(window)
            span = c_windows or run
            self.status('qwen', f'Two-tier tầng 2: crop đối tượng {span[0]["start_s"]:.1f}–{span[-1]["end_s"]:.1f} s.')
            second = self.tier2(span[0]['start_s'], span[-1]['end_s'], ' '.join(w['description'] for w in span), f'event_{len(self.memory["events"]):02d}')
            decision = classify(run, second['choice'])
            self.memory['events'].append({'start_s': run[0]['start_s'], 'end_s': run[-1]['end_s'], 'windows': len(run),
                                          'tier1': 'C' if c_windows else 'B', 'tier2': second, **(decision or {'kind': None, 'confidence': 'rejected'})})
            self.save()
        self.memory['elapsed_s'] = round(time.monotonic() - started, 1)
        self.save()
        return self.result()

    # --- report ----------------------------------------------------------------------------------
    def result(self) -> ProcessedResult:
        events = [e for e in self.memory['events'] if e['kind']]
        high = sorted((e for e in events if e['confidence'] == 'high'), key=lambda e: (e['kind'] != 'FALL_OR_COLLISION', e['start_s']))
        review = [e for e in events if e['confidence'] == 'review']
        unknowns = [f'Chỉ phân tích frame mỗi {STEP_S} s trên dải đường; diễn biến giữa các frame chưa được quan sát.',
                    *(f'Cần xem lại: {e["kind"]} {e["start_s"]:.1f}–{e["end_s"]:.1f} s ({e["tier2"]["actor"]}): {e["tier2"]["description"]}' for e in review)]
        state = 'CONFIRMED' if high else 'INCONCLUSIVE' if review else 'NO_INCIDENT_IN_ANALYZED_COVERAGE'
        metadata = {'provider': 'ollama', 'model': self.settings.qwen_ollama_model, 'pipeline': 'two_tier_v1', 'detection_state': state,
                    'requires_engineer_review': True, 'events': events, 'memory_uri': self.memory_path.relative_to(self.root).as_posix(), 'unknowns': unknowns}
        self.status('database', f'Two-tier: {state}, {len(high)} sự kiện tin cậy cao, {len(review)} cần xem lại.')
        if not high:
            # A no-incident report must stay empty (reports.py); review candidates live in model_metadata only.
            return ProcessedResult(AnalysisResult(incident_detected=False, model_metadata=metadata), [], None)
        main = high[0]
        windows = [w for w in self.memory['windows'] if main['start_s'] <= w['start_s'] <= main['end_s'] and w['choice'] in ('B', 'C')]
        key = next((w for w in windows if w['choice'] == 'C'), None) or next((w for w in windows if w.get('strict') == 'B'), windows[0])
        offset = key['start_s'] + STEP_S
        evidence, timeline = {}, []
        for index, window in enumerate(windows):
            ids = []
            for uri in window['frames']:
                at = float(Path(uri).stem[1:])
                if uri not in evidence:
                    evidence[uri] = _evidence(self.root, self.root / uri, 'frame', at - offset, at - offset, 'image/jpeg')
                ids.append(evidence[uri].evidence_id)
            # The tier-2 entry below is the single CRITICAL moment; windows read as onset / build-up / after.
            phase = 'ONSET' if index == 0 else 'AFTER' if window['start_s'] > key['start_s'] else 'BEFORE'
            timeline.append({'time_s': round(window['start_s'] - offset, 3), 'phase': phase, 'description': window['description'], 'evidence_ids': ids, 'certainty': 'OBSERVED'})
        crop_ids = []
        for at, uri in main['tier2']['crops']:
            evidence[uri] = _evidence(self.root, self.root / uri, 'frame', at - offset, at - offset, 'image/jpeg')
            crop_ids.append(evidence[uri].evidence_id)
        timeline.append({'time_s': 0.0, 'phase': 'CRITICAL', 'description': 'Tầng 2 (crop đối tượng): ' + main['tier2']['description'], 'evidence_ids': crop_ids, 'certainty': 'OBSERVED'})
        label = {'FALL_OR_COLLISION': 'Ngã hoặc va chạm', 'NEAR_MISS': 'Suýt va chạm'}[main['kind']]
        summary = (f'{label} ({main["tier2"]["actor"]}) trong khoảng {main["start_s"]:.1f}–{main["end_s"]:.1f} s của video; '
                   f'tầng 1 và tầng 2 cùng xác nhận. Qwen mô tả: "{main["tier2"]["description"]}"')
        analysis = AnalysisResult(incident_detected=True, incident_type=incident_type(main['kind'], main['tier2']['actor']),
                                  incident_window={'start': main['start_s'] - offset, 'critical': 0.0, 'end': main['end_s'] - offset},
                                  summary=summary, timeline=sorted(timeline, key=lambda t: t['time_s']), unknowns=unknowns,
                                  model_metadata={**metadata, 'video_offset_s': offset})
        return ProcessedResult(analysis, list(evidence.values()), offset)


def process_two_tier_incident(incident, *, storage_root, settings, job_id, on_progress=None) -> ProcessedResult:
    root = Path(storage_root).resolve()
    return TwoTier(incident, root=root, settings=settings, job_id=job_id, on_progress=on_progress or (lambda *_: None)).run()
