"""Translate model-only frame coordinates while preserving API video seconds."""
import math
import re
from bisect import bisect_left


class FrameClock:
    def __init__(self, times, duration):
        self.times = tuple(sorted(set(times)))
        if not self.times or self.times[-1] >= duration:
            raise ValueError('invalid sampled frame clock')
        self.duration = duration
        self.positions = {at: index + 1 for index, at in enumerate(self.times)}
        self.positions[duration] = len(self.times) + 1  # Exclusive boundary, never an image.

    @staticmethod
    def wire_key(key):
        if key == 'video_duration_s':
            return 'total_frames'
        if key == 'time_s':
            return 'frame_seq'
        return key[:-2] + '_frame_seq' if key.endswith('_s') else key

    def position(self, at):
        if at in self.positions:
            return self.positions[at]
        index = bisect_left(self.times, at)
        nearby = range(max(0, index - 1), min(len(self.times), index + 1))
        return min(nearby, key=lambda i: abs(self.times[i] - at)) + 1

    def timestamp(self, position):
        if isinstance(position, bool) or not isinstance(position, (int, float)) or not math.isfinite(position) or int(position) != position or not 1 <= position <= len(self.times) + 1:
            raise ValueError('unknown or fractional frame coordinate')
        return self.duration if position == len(self.times) + 1 else self.times[int(position) - 1]

    def text(self, text):
        text = re.sub(r'\b\w+_s\b', lambda match: self.wire_key(match[0]), text)
        return text.replace('video_seconds', 'frame_sequence')

    def encode(self, value):
        if isinstance(value, dict):
            result = {}
            for key, item in value.items():
                encoded = len(self.times) if key == 'video_duration_s' and isinstance(item, (int, float)) else self.position(item) if key.endswith('_s') and isinstance(item, (int, float)) else self.encode(item)
                if key.endswith('_s') and isinstance(item, dict):
                    branches = [encoded, *encoded.get('anyOf', [])]
                    for branch in branches:
                        if branch.get('type') == 'number':
                            branch.update(type='integer', minimum=1, maximum=len(self.times)+1)
                            if key == 'video_duration_s':
                                branch['const'] = len(self.times)
                result[self.wire_key(key)] = encoded
            return result
        if isinstance(value, list):
            return [self.encode(item) for item in value]
        return self.text(value) if isinstance(value, str) else value

    def decode(self, value):
        if isinstance(value, dict):
            result = {}
            for key, item in value.items():
                if key.endswith('_s') or (key == 'time_basis' and item != 'frame_sequence'):
                    raise ValueError('video-only model must use frame coordinates')
                original = 'video_duration_s' if key == 'total_frames' else 'time_s' if key == 'frame_seq' else key[:-10] + '_s' if key.endswith('_frame_seq') else key
                if key == 'total_frames':
                    if item != len(self.times):
                        raise ValueError('model changed total frame count')
                    result[original] = self.duration
                else:
                    result[original] = 'video_seconds' if key == 'time_basis' else self.timestamp(item) if (key == 'frame_seq' or key.endswith('_frame_seq')) and item is not None else self.decode(item)
            return result
        if isinstance(value, list):
            return [self.decode(item) for item in value]
        return value
