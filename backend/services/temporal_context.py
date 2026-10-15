"""Bounded temporal sampling and overlapping frame sequences."""
import json
from copy import deepcopy

from backend.services.evidence_extraction import window_sample_times


def temporal_sample_times(candidate, metadata, fps):
    times = set(window_sample_times(candidate, metadata, fps))
    last = metadata['duration'] - 1 / metadata['fps']
    for step in range(-8, 9):
        at = round(candidate.critical_s + step / 8, 6)
        if candidate.start_s <= at < candidate.end_s and at <= last:
            times.add(at)
    if len(times) > 256:
        raise ValueError('candidate exceeds total extraction budget of 256 frames')
    return tuple(sorted(times))


def temporal_batches(frames, size):
    if size < 4:
        raise ValueError('temporal batches require at least four frames')
    batches = []
    for start in range(0, len(frames), size - 2):
        batches.append(frames[start:start + size])
        if start + size >= len(frames):
            break
    return batches


def trigger_batches(frames, size=6):
    """Advance four core images, with real adjacent context at either boundary."""
    if size != 6:
        raise ValueError('trigger context requires a six-frame batch budget')
    batches = []
    for start in range(0, len(frames), 4):
        end = min(start + 4, len(frames))
        indices = range(max(0, start - 1), min(len(frames), end + 1))
        batches.append((tuple(frames[i] for i in indices),
                        tuple('BEFORE' if i < start else 'AFTER' if i >= end else 'CORE' for i in indices)))
    return batches


def trigger_memory(context_id, observations, max_chars=32000):
    """Replay every sequence; shorten prose, never drop times, IDs or error states.

    Character budget is conservative input sizing, not a tokenizer measurement.
    Complete originals remain in the worker's trigger ledger and request journal.
    """
    memory = {'context_id': context_id, 'observations': deepcopy(observations),
              'prose_compacted': False, 'notice': 'Prior model notes are fallible; missing observations remain unknown.'}
    for limit in (500, 256, 128, 64, 32):
        def shorten(value):
            if isinstance(value, dict):
                return {key: shorten(item) if key not in {'evidence_id', 'evidence_ids', 'code'} else item for key, item in value.items()}
            if isinstance(value, list):
                return [shorten(item) for item in value]
            if isinstance(value, str) and len(value) > limit:
                memory['prose_compacted'] = True
                return value[:limit] + ' [truncated; full ledger retained]'
            return value
        memory['observations'] = shorten(deepcopy(observations))
        if len(json.dumps(memory, ensure_ascii=False)) <= max_chars:
            return memory
    raise ValueError('trigger memory exceeds safe text budget; split trigger or inspect full ledger')


def overview_frames(frames, size, critical):
    selected = {0, len(frames) - 1}
    targets = [critical, critical - .5, critical + .125, critical + .5]
    targets += [frames[0].time_start_s + i * (frames[-1].time_start_s - frames[0].time_start_s) / size for i in range(size)]
    for at in targets:
        if len(selected) >= size:
            break
        selected.add(min(range(len(frames)), key=lambda i: abs(frames[i].time_start_s - at)))
    return tuple(frames[i] for i in sorted(selected))
