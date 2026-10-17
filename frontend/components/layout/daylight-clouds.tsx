import type { CSSProperties } from "react";

export function DaylightClouds({ thin = false }: { thin?: boolean }) {
  return <div className={`daylight-clouds${thin ? " daylight-clouds-thin" : ""}`} aria-hidden="true">{Array.from({ length: 6 }, (_, index) => <div className="daylight-cloud" key={index} style={{ top: `${[9, 30, 57, 79, 18, 69][index]}%`, width: `${[410, 290, 490, 350, 240, 380][index]}px`, animationDuration: `${[105, 137, 119, 153, 169, 143][index]}s`, animationDelay: `${[-18, -91, -48, -126, -145, -65][index]}s`, "--cloud-height": `${[108, 76, 115, 85, 64, 90][index]}px` } as CSSProperties}>{Array.from({ length: 11 }, (_, puff) => <i key={puff} style={{ left: `${puff * 7.2}%`, bottom: `${[2, 9, 16, 24, 29, 20, 26, 17, 12, 5, 0][puff]}%`, width: `${[25, 28, 30, 26, 29, 34, 28, 31, 25, 24, 22][puff]}%`, height: `${[36, 48, 60, 68, 75, 66, 73, 59, 51, 39, 30][puff]}%` }} />)}<b /></div>)}</div>;
}
