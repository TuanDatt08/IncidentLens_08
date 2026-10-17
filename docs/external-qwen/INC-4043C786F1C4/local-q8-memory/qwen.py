"""Shared local-Ollama helper for the memory experiments (stdlib only).
QWEN_MODEL selects the model (default qwen2.5vl:7b)."""
import base64, json, math, os, time, urllib.request
from pathlib import Path

URL = 'http://127.0.0.1:11434/api/chat'
MODEL = os.environ.get('QWEN_MODEL', 'qwen2.5vl:7b')
THINK = os.environ.get('QWEN_THINK') == '1'          # Qwen3.5 thinks by default; off unless asked
TAG = MODEL.replace(':', '-').replace('.', '') + ('-think' if THINK else '')


def chat(content, images=(), schema=None, system=None, history=(), num_predict=200, num_ctx=12288, **options):
    """One stateless call. history = earlier (user, assistant) message dicts the backend chose to resend."""
    user = {'role': 'user', 'content': content, 'images': [base64.b64encode(Path(p).read_bytes()).decode() for p in images]}
    body = {'model': MODEL, 'stream': False, 'messages': ([{'role': 'system', 'content': system}] if system else []) + list(history) + [user],
            'options': {'temperature': 0, 'seed': 42, 'num_ctx': num_ctx, 'num_predict': num_predict, **options}}
    if schema:
        body['format'] = schema
    if MODEL.startswith('qwen3'):
        body['think'] = THINK
    started = time.time()
    r = json.load(urllib.request.urlopen(urllib.request.Request(URL, json.dumps(body).encode(), {'Content-Type': 'application/json'}), timeout=1800))
    raw = r['message']['content']
    try:
        answer = json.loads(raw) if schema else raw
    except json.JSONDecodeError:
        answer = {'unparsed': raw}
    return answer, raw, user, round(time.time() - started, 1)


def obj(**props):
    # Ollama emits object keys alphabetically: name them a_*, b_* ... so reasoning comes before verdicts.
    return {'type': 'object', 'required': list(props), 'properties': props}


TEXT = {'type': 'string'}
BOX = {'type': 'array', 'items': {'type': 'integer'}, 'minItems': 4, 'maxItems': 4}


def smart_resize(w, h, factor=28, min_pixels=1024 * 28 * 28):
    # Image size Qwen actually sees through Ollama (verified 720x440 -> 1148x728).
    wb, hb = round(w / factor) * factor, round(h / factor) * factor
    if wb * hb < min_pixels:
        beta = math.sqrt(min_pixels / (w * h))
        wb, hb = math.ceil(w * beta / factor) * factor, math.ceil(h * beta / factor) * factor
    return wb, hb


def to_pixels(box, w, h):
    if MODEL.startswith('qwen3'):   # Qwen3-VL grounds in relative 0-1000 coordinates
        return [round(v * (w if i % 2 == 0 else h) / 1000) for i, v in enumerate(box)]
    rw, rh = smart_resize(w, h)
    return [round(v * (w / rw if i % 2 == 0 else h / rh)) for i, v in enumerate(box)]
