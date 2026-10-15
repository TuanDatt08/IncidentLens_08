"""Bounded temporal sampling and overlapping frame sequences."""
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


def overview_frames(frames, size, critical):
    selected = {0, len(frames) - 1}
    targets = [critical, critical - .5, critical + .125, critical + .5]
    targets += [frames[0].time_start_s + i * (frames[-1].time_start_s - frames[0].time_start_s) / size for i in range(size)]
    for at in targets:
        if len(selected) >= size:
            break
        selected.add(min(range(len(frames)), key=lambda i: abs(frames[i].time_start_s - at)))
    return tuple(frames[i] for i in sorted(selected))
