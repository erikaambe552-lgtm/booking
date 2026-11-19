import type { Category } from "../lib/types";
import { mediaUrl } from "../lib/api";

export function LogoMark({ size = 40 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 128 128" aria-hidden="true">
      <defs>
        <linearGradient id="lm-bg" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stopColor="#1b2a4a" /><stop offset="1" stopColor="#0b1220" /></linearGradient>
        <linearGradient id="lm-fl" x1="0" y1="1" x2="0" y2="0"><stop offset="0" stopColor="#ff5a1f" /><stop offset="1" stopColor="#ffb347" /></linearGradient>
      </defs>
      <rect width="128" height="128" rx="28" fill="url(#lm-bg)" />
      <path d="M74 30 L106 84 H52 Z" fill="#8b7cf6" />
      <path d="M50 22 L88 84 H12 Z" fill="#f6efe6" />
      <path d="M50 52 L62 84 H38 Z" fill="url(#lm-fl)" />
      <path d="M50 60 L55 84 H45 Z" fill="#fff3d6" opacity=".7" />
      <path d="M16 96 q8 -7 16 0 t16 0 t16 0 t16 0 t16 0 t16 0" fill="none" stroke="#22b8cf" strokeWidth="6" strokeLinecap="round" />
      <path d="M26 108 q8 -7 16 0 t16 0 t16 0 t16 0 t16 0" fill="none" stroke="#22b8cf" strokeWidth="5" strokeLinecap="round" opacity=".55" />
    </svg>
  );
}

export function Wordmark({ size = 40 }: { size?: number }) {
  return (
    <span className="wordmark">
      <LogoMark size={size} />
      <span className="wordmark-text">CAMP<b>BLAZER</b></span>
    </span>
  );
}

/** Illustrated artwork used ONLY when no licensed photo has been added yet.
 *  It is clearly labelled as an illustration — never presented as a real photo. */
export function PlaceholderArt({ category, seed = 0 }: { category: Category; seed?: number }) {
  const skies = [["#1b2a4a", "#ff7a3d"], ["#13203a", "#ffb347"], ["#22183f", "#ff8f6b"], ["#0f2740", "#f6a35b"]];
  const [top, bottom] = skies[seed % skies.length];
  const id = `pa-${category}-${seed}`;
  return (
    <svg className="placeholder-art" viewBox="0 0 400 300" preserveAspectRatio="xMidYMid slice" aria-hidden="true">
      <defs>
        <linearGradient id={id} x1="0" y1="0" x2="0" y2="1"><stop offset="0" stopColor={top} /><stop offset="1" stopColor={bottom} /></linearGradient>
      </defs>
      <rect width="400" height="300" fill={`url(#${id})`} />
      <circle cx={120 + (seed * 47) % 180} cy={category === "BEACH" ? 175 : 120} r="34" fill="#ffd9a0" opacity=".85" />
      {category === "MOUNTAIN" ? (
        <>
          <path d="M0 260 L90 120 L150 200 L230 90 L310 190 L360 140 L400 180 V300 H0Z" fill="#2a2350" />
          <path d="M0 300 L70 200 L140 250 L220 170 L300 245 L400 200 V300Z" fill="#141b33" />
          <path d="M230 90 L250 120 L238 116 L230 128 L220 114 L212 118Z" fill="#f6efe6" opacity=".55" />
        </>
      ) : (
        <>
          <path d="M0 190 H400 V300 H0Z" fill="#1d4e74" />
          <path d="M0 205 q25 -8 50 0 t50 0 t50 0 t50 0 t50 0 t50 0 t50 0 t50 0" stroke="#22b8cf" strokeWidth="3" fill="none" opacity=".6" />
          <path d="M0 240 q25 -8 50 0 t50 0 t50 0 t50 0 t50 0 t50 0 t50 0 t50 0" stroke="#22b8cf" strokeWidth="3" fill="none" opacity=".35" />
          <path d="M220 192 q70 -40 150 0Z" fill="#0f1830" />
          <path d="M0 300 L0 262 Q120 240 240 268 T400 262 V300Z" fill="#e9d3b4" />
        </>
      )}
    </svg>
  );
}

export function PhotoFrame({ photo, category, seed, alt, className = "" }: {
  photo: { url: string; credit: string } | null; category: Category; seed?: number; alt: string; className?: string;
}) {
  return (
    <div className={`photo-frame ${className}`}>
      {photo ? (
        <>
          <img src={mediaUrl(photo.url)} alt={alt} loading="lazy" />
          <span className="photo-credit">Photo: {photo.credit}</span>
        </>
      ) : (
        <>
          <PlaceholderArt category={category} seed={seed} />
          <span className="photo-credit">Illustration · authentic photo pending</span>
        </>
      )}
    </div>
  );
}
