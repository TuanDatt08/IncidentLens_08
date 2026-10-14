const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const ts = require('typescript');

const slots = []; let cursor = 0; let effects = []; let tree;
const ref = { current: null };
const jsx = (type, props) => ({ type, props });
const react = {
  forwardRef: fn => fn,
  useState(initial) { const i = cursor++; if (!(i in slots)) slots[i] = initial; return [slots[i], value => { slots[i] = value; }]; },
  useRef(initial) { const i = cursor++; return slots[i] ||= { current: initial }; },
  useCallback(fn, deps) { const i = cursor++; if (!slots[i] || deps.some((d, j) => d !== slots[i].deps[j])) slots[i] = { fn, deps }; return slots[i].fn; },
  useEffect(fn, deps) { const i = cursor++; if (!slots[i] || deps.some((d, j) => d !== slots[i].deps[j])) { slots[i]?.cleanup?.(); slots[i] = { deps }; effects.push(() => { slots[i].cleanup = fn(); }); } },
  useImperativeHandle(target, fn) { target.current = fn(); },
};
const listeners = new Map();
const documentMock = { fullscreenElement: null, addEventListener(name, fn) { listeners.set(name, fn); }, removeEventListener(name) { listeners.delete(name); }, async exitFullscreen() { this.fullscreenElement = null; listeners.get('fullscreenchange')?.(); } };
const moduleMock = { exports: {} };
vm.runInNewContext(ts.transpileModule(fs.readFileSync('components/review/video-player.tsx', 'utf8'), { compilerOptions: { module: ts.ModuleKind.CommonJS, jsx: ts.JsxEmit.ReactJSX } }).outputText, {
  exports: moduleMock.exports, module: moduleMock, Error, document: documentMock,
  require(name) { if (name === 'react') return react; if (name === 'react/jsx-runtime') return { jsx, jsxs: jsx }; if (name.includes('icons')) return { Play: 'PlayIcon', Pause: 'PauseIcon' }; if (name.includes('button')) return { Button: 'Button' }; return { formatSeconds: String }; },
});
const playbackUpdates = [];
assert.match(moduleMock.exports.mediaFailureMessage(4), /unsupported/);
assert.match(moduleMock.exports.mediaFailureMessage(3), /decode/);
assert.match(moduleMock.exports.mediaFailureMessage(2), /downloaded/);
let props = { src: 'video.mp4', start: null, critical: null, end: null, onPlaybackChange: value => playbackUpdates.push(value) };
function render() { cursor = 0; tree = moduleMock.exports.VideoPlayer(props, ref); effects.splice(0).forEach(fn => fn()); return tree; }
function all(node = tree) { if (!node || typeof node !== 'object') return []; return [node, ...[node.props?.children].flat(Infinity).filter(Boolean).flatMap(child => all(child))]; }
function videoNode() { return all().find(n => n.type === 'video'); }
function event(name) { videoNode().props[name]({ currentTarget: media }); render(); }
function button(label) { return all().find(n => n.props?.['aria-label'] === label); }
let resolvePlay, rejectPlay, calls = 0, loads = 0;
const media = { readyState: 0, duration: 10, paused: true, error: null, currentTime: 0, volume: 1, muted: false, playbackRate: 1, buffered: { length: 1, start: () => 0, end: () => 7 },
  play() { calls++; this.paused = false; return new Promise((resolve, reject) => { resolvePlay = resolve; rejectPlay = reject; }); },
  pause() { this.paused = true; event('onPause'); },
  load() { loads++; this.error = null; this.readyState = 0; event('onEmptied'); },
};
async function run() {
  render(); videoNode().props.ref.current = media; render();
  ref.current.seekTo(20); render(); assert.equal(calls, 0); assert.equal(media.currentTime, 0);
  media.readyState = 1; event('onLoadedMetadata'); assert.equal(media.currentTime, 10); assert.equal(calls, 1);
  const overlay = button('Play incident video');
  const focusContainer = { focus(options) { documentMock.activeElement = focusContainer; assert.equal(options.preventScroll, true); } };
  all().find(n => n.props?.['aria-label'] === 'Video player').props.ref.current = focusContainer;
  const overlayElement = {}; overlay.props.ref.current = overlayElement; documentMock.activeElement = overlayElement;
  event('onPlay'); assert.ok(button('Pause video')); assert.equal(button('Play video'), undefined); assert.equal(documentMock.activeElement, focusContainer);
  resolvePlay(); await new Promise(setImmediate); render(); assert.ok(button('Pause video'));
  event('onPlaying'); assert.ok(button('Pause video')); videoNode().props.onWaiting?.(); render(); assert.ok(!all().some(n => n.props?.role === 'status'));
  media.paused = true; event('onEnded'); assert.ok(button('Play video'));
  button('Play video').props.onClick(); const blocked = new Error('blocked'); blocked.name = 'NotAllowedError'; rejectPlay(blocked); media.paused = true; await new Promise(setImmediate); render();
  assert.ok(button('Play video')); assert.ok(all().some(n => n.props?.role === 'alert' && /blocked/.test(n.props.children)));
  button('Play video').props.onClick(); resolvePlay(); await new Promise(setImmediate); event('onPlaying'); assert.ok(button('Pause video'));
  media.error = {}; event('onError'); assert.equal(button('Pause video'), undefined); assert.equal(button('Play video').props.disabled, true);
  const before = calls; ref.current.seekTo(6); render(); assert.equal(calls, before);
  all().find(n => n.type === 'Button' && n.props.children === 'Retry video').props.onClick(); render(); assert.equal(loads, 1);
  media.readyState = 1; event('onLoadedMetadata'); assert.equal(media.currentTime, 6); assert.equal(calls, before + 1);
  resolvePlay(); await new Promise(setImmediate); event('onPlaying'); assert.ok(button('Pause video')); assert.ok(!all().some(n => n.props?.role === 'alert'));
  media.paused = true; event('onPause'); button('Play video').props.onClick(); const staleReject = rejectPlay;
  props = { ...props, src: 'other.mp4' }; render(); render(); staleReject(new Error('old failure')); await new Promise(setImmediate); render();
  assert.ok(button('Play video')); assert.ok(!all().some(n => n.props?.role === 'alert'));
  media.readyState = 1; media.duration = 10; event('onLoadedMetadata');
  assert.equal(button('Video timeline').props.max, 10);
  ref.current.pause(); render();
  ref.current.seekTo(4, false); render(); assert.equal(media.currentTime, 4); assert.equal(media.paused, true);
  assert.equal(playbackUpdates.at(-1).currentTime, 4); assert.equal(playbackUpdates.at(-1).ready, true);
  media.currentTime = 7; event('onTimeUpdate'); assert.equal(playbackUpdates.at(-1).currentTime, 7);
  media.currentTime = 0; event('onTimeUpdate');
  const region = all().find(n => n.props?.['aria-label'] === 'Video player');
  let prevented = 0;
  const key = (value, tagName = 'DIV') => region.props.onKeyDown({ key: value, target: { tagName, isContentEditable: false }, preventDefault() { prevented++; } });
  key('l'); assert.equal(media.currentTime, 10); key('j'); assert.equal(media.currentTime, 0);
  key('l', 'TEXTAREA'); key('l', 'SELECT'); key('l', 'INPUT'); key(' ', 'BUTTON'); assert.equal(media.currentTime, 0); assert.equal(prevented, 2);
  button('Video volume').props.onChange({ target: { value: '0.35' } }); render(); assert.equal(media.volume, 0.35);
  button('Mute video').props.onClick(); render(); assert.equal(media.muted, true); assert.ok(button('Unmute video'));
  button('Playback speed').props.onChange({ target: { value: '1.5' } }); render(); assert.equal(media.playbackRate, 1.5);
  const currentRegion = all().find(n => n.props?.['aria-label'] === 'Video player');
  const container = { async requestFullscreen() { documentMock.fullscreenElement = container; listeners.get('fullscreenchange')?.(); } };
  currentRegion.props.ref.current = container;
  await button('Enter fullscreen').props.onClick(); await new Promise(setImmediate); render(); assert.ok(button('Exit fullscreen'));
  await button('Exit fullscreen').props.onClick(); await new Promise(setImmediate); render(); assert.ok(button('Enter fullscreen'));
  media.duration = NaN; event('onDurationChange'); assert.equal(button('Video timeline').props.max, 0); assert.equal(button('Video timeline').props.disabled, true);
  slots.forEach(slot => slot?.cleanup?.());
  assert.equal(listeners.has('fullscreenchange'), false);
  console.log('PASS: deferred seek, actual playing, buffering, ended, rejected play/retry, media error/timestamp/reload, stale source response, passive seek, bounded shortcuts, audio, speed, fullscreen, unknown duration');
}
run().catch(error => { console.error(error); process.exitCode = 1; });
