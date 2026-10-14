"use client";

import { useEffect, useRef } from "react";

type GalaxyCanvasProps = {
  onReady?: () => void;
  onUnavailable?: () => void;
};

const vertexSource = `
attribute vec2 a_position;
void main() { gl_Position = vec4(a_position, 0.0, 1.0); }
`;

// One full-screen pass: analytically shaded sphere and projected orbit paths.
// The canvas stays transparent so the permanent SVG scene supplies the baseline.
const fragmentSource = `
#ifdef GL_FRAGMENT_PRECISION_HIGH
precision highp float;
#else
precision mediump float;
#endif
uniform vec2 u_resolution;
uniform float u_time;
uniform float u_day;
float hash(vec2 p) { return fract(sin(dot(p, vec2(127.1,311.7))) * 43758.5453); }
float noise(vec2 p) {
  vec2 i=floor(p), f=fract(p); f=f*f*(3.0-2.0*f);
  return mix(mix(hash(i),hash(i+vec2(1.,0.)),f.x),mix(hash(i+vec2(0.,1.)),hash(i+vec2(1.)),f.x),f.y);
}
float cloud(vec2 p) { return noise(p)*.58+noise(p*2.03)*.28+noise(p*4.01)*.14; }
void main() {
  vec2 p=(gl_FragCoord.xy-u_resolution*vec2(.52,.50))/min(u_resolution.x,u_resolution.y);
  float t=u_time;
  vec3 cyan=vec3(.08,.76,1.0), violet=vec3(.42,.20,1.0);
  float r=length(p), sr=.19;
  vec2 drift=vec2(t*.007,-t*.005);
  vec2 warp=vec2(noise(p*4.+drift),noise(p*4.-drift+13.));
  float nebula=cloud(p*6.+warp*1.4+drift);
  float envelope=exp(-dot(p*vec2(.85,1.25),p*vec2(.85,1.25))*7.);
  vec3 col=mix(violet,cyan,smoothstep(.25,.78,noise(p*3.+warp)))*envelope*pow(nebula,2.5)*.34;
  // Sparse dust, with tiny restrained twinkle rather than rapidly flashing stars.
  vec2 cells=p*92.; vec2 cell=floor(cells); vec2 local=fract(cells)-.5;
  float seed=hash(cell);
  float star=step(.986,seed)*exp(-dot(local,local)*180.);
  col+=mix(vec3(.50,.38,.86),vec3(.62,.88,1.),seed)*star*(.42+.12*sin(t*.35+seed*30.));
  vec3 foreground=vec3(0.);
  // Inclined ellipses. Depth brightens the near segment and softens the far arc.
  for(int i=0;i<3;i++) {
    float fi=float(i); float angle=-.36+fi*.43;
    mat2 rot=mat2(cos(angle),-sin(angle),sin(angle),cos(angle));
    vec2 q=rot*p; float radius=.36+fi*.033;
    vec2 e=vec2(q.x,q.y/(.37+fi*.085));
    float d=abs(length(e)-radius);
    float front=1.-smoothstep(-.045,.045,q.y);
    float visible=1.;
    if(r<sr && q.y>0.) visible=0.;
    vec3 ringColor=mix(mix(violet,cyan,fi*.32),vec3(.70,.57,.34),u_day*.62);
    vec3 orbit=ringColor*(exp(-d*220.)*.31+exp(-d*55.)*.047)*(.32+.68*front)*visible;
    col+=orbit;
    if(r<sr && q.y<0.) foreground+=orbit;
    float phase=t*(.15-fi*.028)+fi*2.1;
    vec2 spot=vec2(cos(phase)*radius,sin(phase)*radius*(.37+fi*.085));
    float light=exp(-length(q-spot)*310.);
    float spotVisible=(length(spot)>sr || spot.y<0.)?1.:0.;
    vec3 node=ringColor*light*1.65*spotVisible;
    col+=node;
    if(r<sr && spot.y<0.) foreground+=node;
  }
  // Sphere normal provides terminator, rim and specular; the plasma is material,
  // not a flat radial gradient. Perspective contours follow its surface normal.
  float halo=exp(-abs(r-sr)*31.);
  vec3 atmosphere=mix(violet,cyan,smoothstep(-.20,.17,p.x+p.y));
  col+=mix(atmosphere,vec3(1.,.60,.18),u_day)*(halo*mix(.08,.38,u_day)+exp(-abs(r-sr)*115.)*mix(.08,.50,u_day));
  if(r<sr) {
    vec2 xy=p/sr; float z=sqrt(max(0.,1.-dot(xy,xy)));
    vec3 normal=vec3(xy,z);
    vec3 light=normalize(vec3(-.72,.55,.65));
    float diffuse=max(0.,dot(normal,light));
    float rim=pow(1.-z,2.8);
    // Rotate the surface coordinates, not the light: continents move while the
    // terminator stays spatially stable, making the center read as a real sphere.
    float spin=t*.15;
    vec3 surface=vec3(normal.x*cos(spin)+normal.z*sin(spin),normal.y,
      normal.z*cos(spin)-normal.x*sin(spin));
    vec2 uv=vec2(surface.x*2.4+surface.z*.75,surface.y*2.4+surface.z*.40);
    vec2 currents=vec2(cloud(uv*1.5+3.),cloud(uv*1.5+17.));
    float plasma=cloud(uv*3.1+currents*2.8);
    float detail=noise(uv*12.+currents*4.);
    float continents=smoothstep(.38,.66,plasma);
    float filaments=1.-smoothstep(.012,.065,abs(plasma-.53));
    vec3 material=mix(vec3(.055,.035,.22),vec3(.13,.54,.67),continents);
    material=mix(material,vec3(.42,.17,.64),smoothstep(.59,.78,plasma)*.65);
    material+=vec3(.11,.25,.34)*detail*continents;
    float spec=pow(max(0.,dot(reflect(-light,normal),vec3(0.,0.,1.))),18.);
    float terminator=1.-smoothstep(.03,.35,diffuse);
    vec3 sphere=material*(.32+diffuse*1.18)+cyan*filaments*(.08+.21*diffuse);
    sphere+=violet*terminator*.10;
    sphere+=atmosphere*rim*.90+vec3(.67,.92,1.)*spec*.32;
        // Silver lunar maria and crater rims at night; glowing convection by day.
    vec2 lunarUV=vec2(atan(surface.x,surface.z),asin(clamp(surface.y,-1.,1.)))*2.;
    float grain=cloud(lunarUV*14.);
    float maria=smoothstep(.3,.7,cloud(lunarUV*2.2+7.));
    vec3 moon=mix(vec3(.48,.50,.54),vec3(.72,.73,.75),maria);
    moon*=.94+grain*.12;
    vec2 craterUV=lunarUV*4.;
    vec2 craterCell=floor(craterUV), craterLocal=fract(craterUV);
    float craterSeed=hash(craterCell);
    vec2 center=vec2(.3+hash(craterCell+7.)*.4,.3+hash(craterCell+19.)*.4);
    float craterRadius=.055+craterSeed*.10;
    float craterDistance=length(craterLocal-center);
    float craterMask=step(.68,craterSeed);
    moon-=vec3(.065)*(1.-smoothstep(craterRadius*.6,craterRadius,craterDistance))*craterMask;
    moon+=vec3(.055)*exp(-abs(craterDistance-craterRadius)*90.)*craterMask;
    moon*=.38+diffuse*.75;
    moon+=vec3(.63,.70,.83)*rim*.055;    float convection=cloud(uv*7.+currents+vec2(t*.018,0.));
    vec3 sun=mix(vec3(.94,.38,.045),vec3(1.,.85,.42),convection);
    sun*=.77+z*.25;
    sun+=vec3(.15,.07,.0)*filaments;
    sphere=mix(moon,sun,u_day);
    col=mix(col,sphere,1.-smoothstep(sr-.002,sr,r));
  }
  col+=foreground;
  float edge=1.-smoothstep(.43,.69,r);
  col*=edge;
  // Premultiplied translucent light overlays the persistent fallback artwork.
  float alpha=clamp(max(max(col.r,col.g),col.b)*1.5,0.,.92);
  // Opaque surface coverage prevents the SVG texture showing through the dark
  // hemisphere; only the atmospheric outskirts blend with the baseline scene.
  alpha=max(alpha,(1.-smoothstep(sr-.002,sr,r))*.98);
  gl_FragColor=vec4(col*alpha,alpha);
}
`;

export default function GalaxyCanvas({ onReady, onUnavailable }: GalaxyCanvasProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const callbacks = useRef({ onReady, onUnavailable });
  callbacks.current = { onReady, onUnavailable };

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    let disposed = false;
    let failed = false;
    let frameId = 0;
    let frameCount = 0;
    let visible = true;
    let activeTime = 0;
    let previousTime = 0;
    let lastDraw = 0;
    const motion = window.matchMedia("(prefers-reduced-motion: reduce)");
    const coarse = window.matchMedia("(pointer: coarse)");
    const gl = canvas.getContext("webgl", {
      alpha: true, antialias: false, depth: false, stencil: false,
      premultipliedAlpha: true, preserveDrawingBuffer: false, powerPreference: "low-power",
    });
    const unavailable = () => {
      if (failed || disposed) return;
      failed = true;
      cancelAnimationFrame(frameId);
      canvas.dataset.renderState = "fallback";
      callbacks.current.onUnavailable?.();
    };
    if (!gl) { unavailable(); return; }
    const shaders: WebGLShader[] = [];
    const compile = (type: number, source: string) => {
      const shader = gl.createShader(type);
      if (!shader) return null;
      shaders.push(shader);
      gl.shaderSource(shader, source);
      gl.compileShader(shader);
      return gl.getShaderParameter(shader, gl.COMPILE_STATUS) ? shader : null;
    };
    const vertex = compile(gl.VERTEX_SHADER, vertexSource);
    const fragment = compile(gl.FRAGMENT_SHADER, fragmentSource);
    const program = gl.createProgram();
    const buffer = gl.createBuffer();
    const release = () => {
      if (buffer) gl.deleteBuffer(buffer);
      if (program) gl.deleteProgram(program);
      shaders.forEach((shader) => gl.deleteShader(shader));
    };
    if (!vertex || !fragment || !program || !buffer) {
      unavailable(); release(); return;
    }
    gl.attachShader(program, vertex);
    gl.attachShader(program, fragment);
    gl.linkProgram(program);
    if (!gl.getProgramParameter(program, gl.LINK_STATUS)) {
      unavailable(); release(); return;
    }
    gl.useProgram(program);
    gl.bindBuffer(gl.ARRAY_BUFFER, buffer);
    gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([-1,-1,1,-1,-1,1,-1,1,1,-1,1,1]), gl.STATIC_DRAW);
    const position = gl.getAttribLocation(program, "a_position");
    if (position < 0) { unavailable(); release(); return; }
    gl.enableVertexAttribArray(position);
    gl.vertexAttribPointer(position, 2, gl.FLOAT, false, 0, 0);
    const resolution = gl.getUniformLocation(program, "u_resolution");
    const time = gl.getUniformLocation(program, "u_time");
    const day = gl.getUniformLocation(program, "u_day");
    const draw = () => {
      if (disposed || failed || !canvas.width || !canvas.height) return;
      gl.viewport(0, 0, canvas.width, canvas.height);
      gl.uniform2f(resolution, canvas.width, canvas.height);
      gl.uniform1f(time, activeTime);
      gl.uniform1f(day, document.documentElement.dataset.theme === "light" ? 1 : 0);
      gl.drawArrays(gl.TRIANGLES, 0, 6);
      frameCount += 1;
      canvas.dataset.frame = String(frameCount);
      canvas.dataset.renderState = motion.matches ? "paused" : "ready";
      if (frameCount === 1) callbacks.current.onReady?.();
    };
    const running = () => visible && !document.hidden && !motion.matches && !failed && !disposed;
    const tick = (stamp: number) => {
      if (!running()) { previousTime = 0; return; }
      if (previousTime) activeTime += Math.min((stamp-previousTime)/1000, .1);
      previousTime = stamp;
      if (stamp-lastDraw >= 1000/(coarse.matches ? 20 : 30)) { draw(); lastDraw = stamp; }
      frameId = requestAnimationFrame(tick);
    };
    const resume = () => {
      cancelAnimationFrame(frameId);
      previousTime = 0;
      if (running()) frameId = requestAnimationFrame(tick);
      else if (!failed) canvas.dataset.renderState = "paused";
    };
    const resize = () => {
      const bounds = canvas.getBoundingClientRect();
      if (bounds.width <= 0 || bounds.height <= 0) return;
      const ratio = Math.min(window.devicePixelRatio || 1, coarse.matches ? 1 : 1.25, 960/bounds.width);
      canvas.width = Math.max(1, Math.round(bounds.width*ratio));
      canvas.height = Math.max(1, Math.round(bounds.height*ratio));
      draw();
    };
    const themeObserver = new MutationObserver(() => draw());
    themeObserver.observe(document.documentElement, { attributes: true, attributeFilter: ["data-theme"] });
    const observer = new ResizeObserver(resize);
    observer.observe(canvas);
    const intersection = new IntersectionObserver(([entry]) => {
      visible = entry.isIntersecting;
      resume();
    });
    intersection.observe(canvas);
    const motionChange = () => { if (motion.matches) draw(); resume(); };
    const pointerChange = () => { resize(); resume(); };
    const contextLost = (event: Event) => { event.preventDefault(); unavailable(); };
    canvas.addEventListener("webglcontextlost", contextLost);
    document.addEventListener("visibilitychange", resume);
    motion.addEventListener("change", motionChange);
    coarse.addEventListener("change", pointerChange);
    resize();
    resume();
    return () => {
      disposed = true;
      cancelAnimationFrame(frameId);
      observer.disconnect();
      themeObserver.disconnect();
      intersection.disconnect();
      canvas.removeEventListener("webglcontextlost", contextLost);
      document.removeEventListener("visibilitychange", resume);
      motion.removeEventListener("change", motionChange);
      coarse.removeEventListener("change", pointerChange);
      release();
    };
  }, []);

  return <canvas ref={canvasRef} className="lp-galaxy-canvas" aria-hidden="true" data-render-state="paused" data-frame="0" />;
}
