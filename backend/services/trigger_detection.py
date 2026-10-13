"""One-pass log-clock triggers; synchronization is separate from detection."""
from __future__ import annotations

import math
from dataclasses import dataclass

from backend.services.telemetry import TelemetryError


@dataclass(frozen=True)
class TriggerConfig:
    pre_s: float = 5.
    post_s: float = 3.
    merge_gap_s: float = 1.
    brake_threshold: float = .8
    brake_rate: float = 1.5
    deceleration: float = 6.
    steering_rate: float = .8
    yaw_rate_deg_s: float = 20.
    lateral_acceleration: float = 2.
    vertical_acceleration: float = 3.
    vertical_imu_residual: float = 2.
    min_turn_speed: float = 3.
    max_derivative_gap_s: float = 2.
    ewma_tau_s: float = 1.
    ewma_sigma: float = 6.
    warmup_s: float = 1.
    max_triggers: int = 100
    max_flags: int = 32
    min_priority: int = 1

    def __post_init__(self):
        for key, value in vars(self).items():
            if not math.isfinite(value) or value < 0 or (key not in {'pre_s','post_s','merge_gap_s','warmup_s'} and value == 0):
                raise ValueError(f'invalid trigger budget/threshold: {key}')
        if not isinstance(self.max_triggers,int) or not isinstance(self.max_flags,int):
            raise ValueError('trigger budgets must be integers')


def find_log_triggers(log, *, config=None, alignment=None, video_metadata=None, signal_thresholds=None, delta_thresholds=None, guard=None):
    """O(n) with fixed signal count; bounded samples and event storage.

    Times describe telemetry excursions, not confirmed incident onset/outcome.
    All rows are scanned even when output budgets are exceeded.
    """
    cfg = config or TriggerConfig()
    thresholds, deltas = signal_thresholds or {}, delta_thresholds or {}
    metadata = video_metadata or {}
    synced = alignment is not None and alignment.quality == 'VERIFIED'
    fps = metadata.get('fps',24.)
    if not math.isfinite(fps) or fps <= 0:
        raise ValueError('positive video FPS required')
    rows = dropped = bad_dt = 0
    events = []
    current = previous = previous_velocity = None
    ewma = {}
    started = None
    unknowns = []
    def finish():
        nonlocal current, dropped
        if current is None:
            return
        event = current
        event['reasons'] = sorted(event['reasons'])
        for part in ('start','peak','end'):
            at = alignment.to_video_seconds(event[f'log_{part}_s']) if synced else None
            event[f'video_{part}_s'] = at
            frame = max(0, round(at*fps)) if at is not None and 0 <= at < metadata.get('duration',math.inf) else None
            if frame is not None and math.isfinite(metadata.get('duration',math.inf)):
                frame = min(frame,max(0,math.ceil(metadata['duration']*fps)-1))
            event[f'frame_{part}'] = frame
        event['sync_status'] = 'VERIFIED' if synced else 'UNKNOWN'
        event['fps'] = fps
        start, end = event['video_start_s'], event['video_end_s']
        event['clip_start_s'] = max(0.,start-cfg.pre_s) if start is not None else None
        event['clip_end_s'] = min(metadata.get('duration',math.inf),end+cfg.post_s) if end is not None else None
        if len(events) < cfg.max_triggers:
            events.append(event)
        else:
            dropped += 1
        current = None
    for row in log.iter_rows():
        if guard is not None and rows % 1000 == 0:
            guard()
        rows += 1
        at = row['time_s']
        values = {}
        for key in {'speed','brake','steer','acceleration','accel_y','accel_z','loc_x','loc_y','loc_z','compass_deg','collision_intensity','jerk',*thresholds,*deltas}:
            if row.get(key) not in (None,''):
                try:
                    value = float(row[key])
                except (ValueError,TypeError) as exc:
                    raise TelemetryError(f'{key} must be numeric') from exc
                if not math.isfinite(value):
                    raise TelemetryError(f'{key} must be finite')
                values[key] = value
        flags = []
        def flag(reason, signal, value, threshold):
            priority = 5 if reason == 'COLLISION_SENSOR' else 4 if reason == 'DECELERATION' or (reason == 'SIGNAL_THRESHOLD' and signal == 'acceleration') else 3 if reason in {'SHARP_TURN','VERTICAL_SHOCK'} else 1 if reason == 'EWMA_ANOMALY' else 2
            flags.append({'log_time_s':at,'signal':signal,'value':value,'threshold':threshold,'reason':reason,'score':abs(value)/threshold if threshold > 0 else 1.,'priority':priority})
        if values.get('brake',0.) >= cfg.brake_threshold:
            flag('HARD_BRAKING','brake',values['brake'],cfg.brake_threshold)
        if values.get('acceleration',0.) <= -cfg.deceleration:
            flag('DECELERATION','acceleration',values['acceleration'],cfg.deceleration)
        if values.get('collision_intensity',0.) > 0:
            flag('COLLISION_SENSOR','collision_intensity',values['collision_intensity'],1.)
        for signal, threshold in thresholds.items():
            if abs(values.get(signal,0.)) >= threshold:
                flag('SIGNAL_THRESHOLD',signal,values[signal],threshold)
        dt = at-previous[0] if previous else None
        derivative_ok = dt is not None and 1e-6 < dt <= cfg.max_derivative_gap_s
        velocity = None
        if derivative_ok:
            old = previous[1]
            rates = {key:(value-old[key])/dt for key,value in values.items() if key in old}
            if values.get('brake',0.) >= .3 and rates.get('brake',0.) >= cfg.brake_rate:
                flag('BRAKE_RISE','brake_rate',rates['brake'],cfg.brake_rate)
            yaw = abs((values['compass_deg']-old['compass_deg']+180.) % 360.-180.)/dt if 'compass_deg' in values and 'compass_deg' in old else 0.
            if all(key in rates for key in ('loc_x','loc_y')):
                velocity = (rates['loc_x'],rates['loc_y'],rates.get('loc_z'))
                if previous_velocity and math.hypot(*velocity[:2]) >= cfg.min_turn_speed and math.hypot(*previous_velocity[:2]) >= cfg.min_turn_speed:
                    before = math.atan2(previous_velocity[1],previous_velocity[0])
                    after = math.atan2(velocity[1],velocity[0])
                    yaw = max(yaw,abs(math.degrees((after-before+math.pi) % (2*math.pi)-math.pi))/dt)
            if values.get('speed',0.) >= cfg.min_turn_speed and (yaw >= cfg.yaw_rate_deg_s or abs(rates.get('steer',0.)) >= cfg.steering_rate) and abs(values.get('accel_y',0.)) >= cfg.lateral_acceleration:
                flag('SHARP_TURN','yaw_rate' if yaw >= cfg.yaw_rate_deg_s else 'steer_rate',yaw if yaw >= cfg.yaw_rate_deg_s else rates['steer'],cfg.yaw_rate_deg_s if yaw >= cfg.yaw_rate_deg_s else cfg.steering_rate)
            vz = rates.get('loc_z')
            old_vz = previous_velocity[2] if previous_velocity else None
            z_baseline = ewma.get('accel_z',(values.get('accel_z',9.81),0.))[0]
            if vz is not None and old_vz is not None and abs((vz-old_vz)/dt) >= cfg.vertical_acceleration and abs(values.get('accel_z',z_baseline)-z_baseline) >= cfg.vertical_imu_residual:
                flag('VERTICAL_SHOCK','loc_z_acceleration',(vz-old_vz)/dt,cfg.vertical_acceleration)
            if velocity is None and vz is not None:
                velocity = (0.,0.,vz)
            for signal, threshold in deltas.items():
                if signal in values and signal in old and abs(values[signal]-old[signal]) >= threshold:
                    flag('SIGNAL_DELTA',signal,values[signal]-old[signal],threshold)
            if previous[2] != row.get('mode') and row.get('mode') == 'MANUAL':
                flag('DISENGAGEMENT','mode_change',1.,1.)
        elif previous:
            bad_dt += 1
            ewma.clear()
            started = at
        if started is None:
            started = at
        alpha = 1.-math.exp(-dt/cfg.ewma_tau_s) if derivative_ok else 0.
        floors = {'brake':.1,'acceleration':1.,'accel_y':.5,'accel_z':.5,'steer':.1}
        for key,floor in floors.items():
            if key not in values:
                continue
            value = values[key]
            mean, variance = ewma.get(key,(value,0.))
            error = value-mean
            limit = max(floor,cfg.ewma_sigma*math.sqrt(max(0.,variance)))
            if at-started >= cfg.warmup_s and abs(error) >= limit and (key == 'accel_z' or abs(value) >= floor):
                flag('EWMA_ANOMALY',key,error,limit)
            ewma[key] = (mean+alpha*error,(1.-alpha)*(variance+alpha*error*error))
        flags = [item for item in flags if item['priority'] >= cfg.min_priority]
        if flags:
            if current and at > current['log_end_s']+cfg.merge_gap_s:
                finish()
            best = max(flags,key=lambda item:(item['priority'],item['score']))
            if current is None:
                current = {'log_start_s':at,'log_peak_s':at,'log_end_s':at,'peak_score':best['score'],'peak_priority':best['priority'],'reasons':set(),'flags':[],'flag_count':0,'omitted_flags':0}
            current['log_end_s'] = at
            current['reasons'].update(item['reason'] for item in flags)
            if (best['priority'],best['score']) > (current['peak_priority'],current['peak_score']):
                current['peak_priority'],current['peak_score'],current['log_peak_s'] = best['priority'],best['score'],at
            for item in flags:
                current['flag_count'] += 1
                if len(current['flags']) < cfg.max_flags:
                    current['flags'].append(item)
                else:
                    current['omitted_flags'] += 1
                    if (item['priority'],item['score']) > (current['flags'][-1]['priority'],current['flags'][-1]['score']):
                        current['flags'][-1] = item
        previous, previous_velocity = (at,values,row.get('mode')),velocity
    finish()
    if not synced:
        unknowns.append('Triggers located in log clock; video time/frame/clip mapping UNKNOWN until synchronization is supplied.')
    if dropped:
        unknowns.append(f'{dropped} merged trigger intervals exceed the output budget; remaining log coverage requires review.')
    if bad_dt:
        unknowns.append(f'Derivatives/EWMA reset at {bad_dt} duplicate timestamps or gaps; no nominal FPS substituted for CSV time.')
    return {'schema_version':'log_triggers_v1','rows':rows,'triggers':events,'overflow_triggers':dropped,'unknowns':unknowns}
