"""Evaluate local trigger discovery without feeding expected labels to the detector.

python -m backend.verify_local_triggers --input vlm/data
"""
from __future__ import annotations

import argparse
import hashlib
import json
import time
from dataclasses import asdict
from pathlib import Path

from backend.config import get_settings
from backend.services.candidate_detection import DetectionConfig, detect_candidates
from backend.services.log_normalization import normalize_log
from backend.services.synchronization import TimeAnchor, align
from backend.services.video import VideoService


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input',type=Path,default=Path('vlm/data'))
    parser.add_argument('--output',type=Path,default=Path('backend/data/trigger-verification'))
    args = parser.parse_args()
    settings = get_settings()
    service = VideoService(settings.ffprobe_bin,settings.ffmpeg_bin,frame_max_width=640)
    reports = []
    for video in sorted(args.input.glob('*.mp4')):
        csv = video.with_suffix('.csv')
        if not csv.is_file():
            continue
        out = args.output/video.stem
        out.mkdir(parents=True,exist_ok=True)
        metadata = service.probe(video).as_dict()
        anchors = []
        if video.stem == 'nearmiss_20261011_133619_sudden_obstacle':
            # Known mapping from the source README, previously archived in F4D's manifest.
            provenance = 'vlm/data/README.md frame mapping; archived INC-5F8C76DF9F4D/input/manifest.json'
            anchors = [TimeAnchor(-58.458,0.,provenance),TimeAnchor(metadata['duration']-58.458,metadata['duration'],provenance)]
            service.write_json(out/'sync-metadata.json',{'anchors':[asdict(a) for a in anchors]})
        began = time.perf_counter()
        log = normalize_log(csv)
        mapping = align(metadata,log,anchors)
        candidates = detect_candidates(log,mapping,DetectionConfig(video.stem,metadata['duration'],fps=metadata['fps']))
        elapsed = time.perf_counter()-began
        service.write_json(out/'log-triggers.json',candidates.log_trigger_data)
        clips = []
        for index,candidate in enumerate(candidates.candidates):
            clip = out/f'candidate-{index}.mp4'
            service.extract_clip(video,candidate.start_s,candidate.end_s,clip)
            clip_metadata = service.probe(clip).as_dict()
            if abs(clip_metadata['duration']-(candidate.end_s-candidate.start_s)) > .2:
                raise ValueError('extracted clip duration mismatch')
            frame = out/f'candidate-{index}-peak.jpg'
            service.extract_frame(video,candidate.critical_s,frame)
            clips.append({'candidate':asdict(candidate),'clip':str(clip),'clip_metadata':clip_metadata,'peak_frame':str(frame)})
        # Full-video review samples do not assume missing log/video synchronization.
        for index in range(4):
            at = min(metadata['duration']*index/3,metadata['duration']-1.5/metadata['fps'])
            service.extract_frame(video,at,out/f'review-{index}.jpg')
        # References loaded only AFTER detection and extraction; never influence triggers.
        expected_path = video.with_suffix('.expected.json')
        expected = json.loads(expected_path.read_text(encoding='utf-8')) if expected_path.exists() else {}
        reference_time = expected.get('critical_moment',{}).get('reaction_s')
        events = candidates.log_trigger_data['triggers']
        near_reaction = [e for e in events if reference_time is not None and e['log_start_s']-.5 <= reference_time <= e['log_end_s']+.5]
        with csv.open('rb') as stream:
            csv_hash = hashlib.file_digest(stream,'sha256').hexdigest()
        report = {'video':video.name,'csv_sha256':csv_hash,'metadata':metadata,'rows':log.metadata.row_count,'detector_elapsed_s':elapsed,'alignment':asdict(mapping),'triggers':events,'clips':clips,'reference_review':{'reference_verified_by':expected.get('verified_by'),'reaction_s':reference_time,'trigger_neighborhood_matches':len(near_reaction),'tolerance_s':.5,'collision_sensor_trigger':any('COLLISION_SENSOR' in e['reasons'] for e in events)},'limitations':['Triggers are suspicion, not incident confirmation. Expected labels are automatic and unverified.','Unsynchronized videos retain log-clock triggers; no precise clip timing is guessed.','No native Qwen result is claimed by this detector/extraction verification.']}
        service.write_json(out/'verification.json',report)
        reports.append(report)
        print(video.name,'rows',report['rows'],'triggers',len(events),'sync',mapping.quality,'seconds',round(elapsed,4),flush=True)
    service.write_json(args.output/'summary.json',reports)


if __name__ == '__main__':
    main()
