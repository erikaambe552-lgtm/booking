import { useEffect, useRef } from "react";

/**
 * Animated line-drawn 3D terrain for the hero (inspired by the user's sample design).
 * The landscape is stylised on Biliran: three summits like Tres Marias plus a
 * lone cone like Panamao. Pure canvas, no libraries.
 */
const PEAKS: [number, number, number, number][] = [
  // x, z, height, spread
  [0.15, 3.3, 1.55, 0.32],
  [0.55, 3.6, 1.35, 0.3],
  [0.95, 3.9, 1.15, 0.3],
  [-0.65, 4.4, 0.95, 0.38],
];

function height(x: number, z: number, t: number) {
  let h = 0;
  for (const [px, pz, a, s] of PEAKS) {
    const d2 = (x - px) ** 2 + ((z - pz) * 0.7) ** 2;
    h += a * Math.exp(-d2 / (2 * s * s));
  }
  h += 0.06 * Math.sin(x * 7 + z * 3) + 0.04 * Math.sin(x * 13 - z * 5);
  h += 0.025 * Math.sin(t * 0.6 + x * 4 + z * 2);
  return Math.max(0, h);
}

export default function WireTerrain() {
  const ref = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = ref.current!;
    const ctx = canvas.getContext("2d")!;
    const reduce = window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;
    let w = 0, h = 0, raf = 0, visible = true;
    const t0 = performance.now();

    const resize = () => {
      const dpr = Math.min(window.devicePixelRatio || 1, 2);
      w = canvas.clientWidth; h = canvas.clientHeight;
      canvas.width = w * dpr; canvas.height = h * dpr;
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    };

    const ROWS = 54, COLS = 90, zNear = 1.6, zFar = 6.2;
    const draw = (now: number) => {
      const t = (now - t0) / 1000;
      const reveal = reduce ? 1 : Math.min(1, t / 2.6);
      const ease = 1 - Math.pow(1 - reveal, 3);
      ctx.clearRect(0, 0, w, h);
      const mobile = w < 760;
      const cx = mobile ? w * 0.5 : w * 0.7;
      const focal = Math.min(w, h * 1.5) * (mobile ? 0.34 : 0.44);
      const horizon = h * (mobile ? 0.9 : 0.52);
      const scan = (t * 0.45) % 1; // orange band sweeping toward the viewer
      const yaw = reduce ? 0 : Math.sin(t * 0.12) * 0.12;

      const grid: [number, number, number][][] = [];
      for (let r = 0; r < ROWS; r++) {
        const zf = r / (ROWS - 1);
        const z = zFar - (zFar - zNear) * zf;
        const row: [number, number, number][] = [];
        for (let c = 0; c < COLS; c++) {
          const x0 = (c / (COLS - 1) - 0.5) * 4.4;
          const x = x0 * Math.cos(yaw) - (z - 3.6) * Math.sin(yaw);
          const zz = x0 * Math.sin(yaw) + (z - 3.6) * Math.cos(yaw) + 3.6;
          const hh = height(x, zz, t) * ease;
          const f = focal / z;
          row.push([cx + x0 * f, horizon + (0.9 - hh * 0.8) * f, hh]);
        }
        grid.push(row);
      }

      ctx.lineWidth = 1;
      for (let r = 0; r < ROWS; r++) {
        const zf = r / (ROWS - 1);
        const fade = (0.15 + 0.65 * zf) * reveal;
        const nearScan = Math.max(0, 1 - Math.abs(zf - scan) * 9);
        ctx.beginPath();
        grid[r].forEach(([x, y], i) => (i ? ctx.lineTo(x, y) : ctx.moveTo(x, y)));
        const avgH = grid[r].reduce((a, p) => a + p[2], 0) / COLS;
        ctx.strokeStyle = nearScan > 0.05
          ? `rgba(255,122,61,${(0.25 + 0.6 * nearScan) * reveal})`
          : `rgba(${150 + avgH * 60},${200 + avgH * 30},230,${fade * 0.55})`;
        ctx.stroke();
      }
      // longitudinal lines give the mesh its sculpted look
      for (let c = 0; c < COLS; c += 2) {
        ctx.beginPath();
        for (let r = 0; r < ROWS; r++) {
          const [x, y] = grid[r][c];
          r ? ctx.lineTo(x, y) : ctx.moveTo(x, y);
        }
        ctx.strokeStyle = `rgba(34,184,207,${0.14 * reveal})`;
        ctx.stroke();
      }
      // summit glints
      for (const [px, pz] of PEAKS.slice(0, 3)) {
        const f = focal / pz;
        const y = horizon + (0.9 - height(px, pz, t) * ease * 0.8) * f;
        ctx.fillStyle = `rgba(255,179,71,${0.85 * reveal})`;
        ctx.beginPath(); ctx.arc(cx + px * f, y, 2.4, 0, Math.PI * 2); ctx.fill();
      }
      if (!reduce && visible) raf = requestAnimationFrame(draw);
    };

    resize();
    const io = new IntersectionObserver(([e]) => {
      visible = e.isIntersecting;
      if (visible && !reduce) { cancelAnimationFrame(raf); raf = requestAnimationFrame(draw); }
    });
    io.observe(canvas);
    window.addEventListener("resize", resize);
    raf = requestAnimationFrame(draw);
    return () => { cancelAnimationFrame(raf); io.disconnect(); window.removeEventListener("resize", resize); };
  }, []);

  return <canvas ref={ref} aria-hidden="true" />;
}
