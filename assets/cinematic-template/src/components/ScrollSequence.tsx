import { useEffect, useRef, useState, type ReactNode } from 'react';
import { gsap } from 'gsap';
import { ScrollTrigger } from 'gsap/ScrollTrigger';
import { prefersLightExperience } from '../lib/network';

gsap.registerPlugin(ScrollTrigger);

type Variant = { count: number; width: number; height: number; pattern: string; poster: string };
export type FrameManifest = { desktop: Variant; mobile: Variant; indexPadding: number };

/** Texte superposé visible entre deux positions de progression (0 → 1). */
export type Beat = { from: number; to: number; content: ReactNode; position?: 'start' | 'center' | 'end' };

type Props = {
  /** manifest.json produit par scripts/video_to_frames.py */
  manifestUrl: string;
  /** Description de la séquence pour les lecteurs d'écran et la version légère */
  alt: string;
  /** Longueur de défilement en hauteurs d'écran (3 à 6 selon le nombre de temps forts) */
  scrollLength?: number;
  beats?: Beat[];
  fit?: 'cover' | 'contain';
  /** Image affichée si le manifest ne charge pas */
  fallbackPoster?: string;
};

const MOBILE_QUERY = '(max-width: 768px), (orientation: portrait) and (max-width: 1024px)';
const CONCURRENCY = 6;
const FADE = 0.04;

export function ScrollSequence({ manifestUrl, alt, scrollLength = 4, beats = [], fit = 'cover', fallbackPoster }: Props) {
  const sectionRef = useRef<HTMLElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const beatRefs = useRef<(HTMLDivElement | null)[]>([]);
  const beatsRef = useRef(beats);
  beatsRef.current = beats;

  const [manifest, setManifest] = useState<FrameManifest | null>(null);
  const [light, setLight] = useState(false);
  const [isMobile, setIsMobile] = useState(false);
  const [firstFrameReady, setFirstFrameReady] = useState(false);

  useEffect(() => {
    setLight(prefersLightExperience());
    const mq = window.matchMedia(MOBILE_QUERY);
    setIsMobile(mq.matches);
    const onChange = (event: MediaQueryListEvent) => setIsMobile(event.matches);
    mq.addEventListener('change', onChange);

    let cancelled = false;
    fetch(manifestUrl)
      .then((res) => (res.ok ? res.json() : Promise.reject(new Error(String(res.status)))))
      .then((data: FrameManifest) => { if (!cancelled) setManifest(data); })
      .catch(() => { if (!cancelled) setLight(true); });

    return () => {
      cancelled = true;
      mq.removeEventListener('change', onChange);
    };
  }, [manifestUrl]);

  useEffect(() => {
    if (!manifest || light) return;
    const variant = isMobile ? manifest.mobile : manifest.desktop;
    const section = sectionRef.current;
    const canvas = canvasRef.current;
    const ctx = canvas?.getContext('2d');
    if (!section || !canvas || !ctx) return;

    const frames: (HTMLImageElement | undefined)[] = new Array(variant.count);
    let current = 0;
    let rafId = 0;
    let disposed = false;
    setFirstFrameReady(false);

    const src = (i: number) =>
      variant.pattern.replace('{index}', String(i + 1).padStart(manifest.indexPadding, '0'));

    const nearestLoaded = (i: number) => {
      if (frames[i]) return frames[i];
      for (let d = 1; d < variant.count; d++) {
        const found = frames[i - d] ?? frames[i + d];
        if (found) return found;
      }
      return undefined;
    };

    const draw = (i: number) => {
      const img = nearestLoaded(i);
      if (!img) return;
      const { width: cw, height: ch } = canvas;
      const ratio = fit === 'cover'
        ? Math.max(cw / img.naturalWidth, ch / img.naturalHeight)
        : Math.min(cw / img.naturalWidth, ch / img.naturalHeight);
      const w = img.naturalWidth * ratio;
      const h = img.naturalHeight * ratio;
      ctx.clearRect(0, 0, cw, ch);
      ctx.drawImage(img, (cw - w) / 2, (ch - h) / 2, w, h);
    };

    const schedule = (i: number) => {
      current = i;
      if (rafId) return;
      rafId = requestAnimationFrame(() => {
        rafId = 0;
        draw(current);
      });
    };

    const resize = () => {
      const dpr = Math.min(window.devicePixelRatio || 1, 2);
      canvas.width = Math.round(canvas.clientWidth * dpr);
      canvas.height = Math.round(canvas.clientHeight * dpr);
      draw(current);
    };

    const updateBeats = (progress: number) => {
      beatsRef.current.forEach((beat, index) => {
        const el = beatRefs.current[index];
        if (!el) return;
        // Le premier temps fort est visible dès l'arrivée, le dernier reste affiché jusqu'à la fin
        const fadeIn = beat.from <= 0 ? 1 : (progress - beat.from) / FADE;
        const fadeOut = beat.to >= 1 ? 1 : (beat.to - progress) / FADE;
        const opacity = Math.max(0, Math.min(1, fadeIn, fadeOut));
        el.style.opacity = String(opacity);
        el.style.transform = `translate3d(0, ${(1 - opacity) * 14}px, 0)`;
      });
    };

    // Chargement progressif : une image sur 16, puis sur 8, 4, 2, 1.
    // Le défilement est fluide très tôt, la précision arrive ensuite.
    const order: number[] = [];
    const queued = new Set<number>();
    for (const step of [16, 8, 4, 2, 1]) {
      for (let i = 0; i < variant.count; i += step) {
        if (!queued.has(i)) {
          queued.add(i);
          order.push(i);
        }
      }
    }
    let cursor = 0;
    const worker = async () => {
      while (!disposed && cursor < order.length) {
        const index = order[cursor++];
        const img = new Image();
        img.decoding = 'async';
        img.src = src(index);
        try {
          await img.decode();
        } catch {
          continue;
        }
        if (disposed) return;
        frames[index] = img;
        if (index === 0) setFirstFrameReady(true);
        if (Math.abs(index - current) <= 16) schedule(current);
      }
    };
    for (let k = 0; k < CONCURRENCY; k++) void worker();

    const trigger = ScrollTrigger.create({
      trigger: section,
      start: 'top top',
      end: 'bottom bottom',
      onUpdate: (self) => {
        schedule(Math.min(variant.count - 1, Math.round(self.progress * (variant.count - 1))));
        updateBeats(self.progress);
      },
    });

    resize();
    updateBeats(trigger.progress);
    window.addEventListener('resize', resize);

    return () => {
      disposed = true;
      trigger.kill();
      cancelAnimationFrame(rafId);
      window.removeEventListener('resize', resize);
    };
  }, [manifest, light, isMobile, fit]);

  const variant = manifest ? (isMobile ? manifest.mobile : manifest.desktop) : null;
  const poster = variant?.poster ?? fallbackPoster;

  if (light) {
    return (
      <section className="sequence sequence--light">
        {poster && <img className="sequence__poster-static" src={poster} alt={alt} />}
        <div className="sequence__beats-static">
          {beats.map((beat, i) => (
            <div key={i} className="beat-static">{beat.content}</div>
          ))}
        </div>
      </section>
    );
  }

  return (
    <section ref={sectionRef} className="sequence" style={{ height: `${(scrollLength + 1) * 100}svh` }}>
      <div className="sequence__stage">
        {poster && (
          <img
            className="sequence__poster"
            src={poster}
            alt=""
            aria-hidden="true"
            fetchPriority="high"
            style={{ opacity: firstFrameReady ? 0 : 1 }}
          />
        )}
        <canvas ref={canvasRef} className="sequence__canvas" role="img" aria-label={alt} />
        <div className="sequence__beats">
          {beats.map((beat, i) => (
            <div
              key={i}
              ref={(el) => { beatRefs.current[i] = el; }}
              className={`beat beat--${beat.position ?? 'start'}`}
              style={{ opacity: 0 }}
            >
              {beat.content}
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
