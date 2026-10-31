import { useEffect, useMemo, useRef, useState } from "react";
import type { ReactNode } from "react";
import * as THREE from "three";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";
import type { TrajectoryFile } from "../types";
import SeriesChart from "./SeriesChart";

const SIM_MIN_PER_SEC = 120; // full 3-day run in ~36 s at 1x
const LIVE = new THREE.Color(0x7c3aed);
const DEAD = new THREE.Color(0xf43f5e);
const BG = 0xe9edfb;

const VIEWS: { label: string; name: string; pos: [number, number, number] }[] = [
  { label: "Vista", name: "libre", pos: [70, 65, 168] },
  { label: "Vista", name: "cenital", pos: [0, 225, 55] },
  { label: "Vista", name: "lateral", pos: [195, 28, 40] },
];

function Icon({ d, filled = false }: { d: string; filled?: boolean }) {
  return (
    <svg
      className="tool-svg"
      viewBox="0 0 24 24"
      width="17"
      height="17"
      fill={filled ? "currentColor" : "none"}
      stroke={filled ? "none" : "currentColor"}
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d={d} />
    </svg>
  );
}

const PATH_ROTATE = "M20 12a8 8 0 1 1-2.34-5.66M20 4v5h-5";
const PATH_ZOOM = "M11 17a6 6 0 1 0 0-12 6 6 0 0 0 0 12zm5 0l4 4M8.5 11h5M11 8.5v5";
const PATH_EYE = "M2 12s3.5-6 10-6 10 6 10 6-3.5 6-10 6-10-6-10-6zm10 2.5a2.5 2.5 0 1 0 0-5 2.5 2.5 0 0 0 0 5z";
const PATH_PAUSE = "M9 5v14M15 5v14";
const PATH_PLAY = "M8 5l11 7-11 7V5z";
const PATH_FULL = "M4 9V4h5M20 9V4h-5M4 15v5h5M20 15v5h-5";
const PATH_UNFULL = "M9 4v5H4M15 4v5h5M9 20v-5H4M15 20v-5h5";

const prefersReducedMotion = () =>
  typeof window !== "undefined" &&
  typeof window.matchMedia === "function" &&
  window.matchMedia("(prefers-reduced-motion: reduce)").matches;

const isFinitePos = (c: TrajectoryFile["frames"][number]["cells"][number]) =>
  Number.isFinite(c.x_um) && Number.isFinite(c.y_um) && Number.isFinite(c.z_um);

export function frameStats(cells: TrajectoryFile["frames"][number]["cells"]) {
  let live = 0;
  let cx = 0;
  let cy = 0;
  let cz = 0;
  let valid = 0;
  for (const c of cells) {
    if (!isFinitePos(c)) continue;
    if (!c.dead) live++;
    cx += c.x_um;
    cy += c.y_um;
    cz += c.z_um;
    valid++;
  }
  const n = Math.max(1, valid);
  cx /= n;
  cy /= n;
  cz /= n;
  let radius = 0;
  for (const c of cells) {
    if (!isFinitePos(c)) continue;
    radius = Math.max(radius, Math.hypot(c.x_um - cx, c.y_um - cy, c.z_um - cz));
  }
  return { live, dead: valid - live, radius };
}

function fmtT(min: number, totalMin: number): string {
  if (totalMin >= 1440) return `${(min / 1440).toFixed(2)} d`;
  if (totalMin >= 120) return `${(min / 60).toFixed(1)} h`;
  return `${min.toFixed(1)} min`;
}

export default function CellViewer({
  data,
  yMax,
  badge,
  showChart = true,
  autoRotate = false,
}: {
  data: TrajectoryFile;
  yMax?: number;
  /** Top-left overlay badge (live run vs honest preview label). */
  badge?: ReactNode;
  /** Hide the series chart for compact layouts. */
  showChart?: boolean;
  /** Slow camera spin until the user grabs the camera (off under reduced motion). */
  autoRotate?: boolean;
}) {
  const mountRef = useRef<HTMLDivElement | null>(null);
  const rigRef = useRef<{ camera: THREE.PerspectiveCamera; controls: OrbitControls } | null>(null);
  const [frame, setFrame] = useState(0);
  const [playing, setPlaying] = useState(() => !prefersReducedMotion());
  const [speed, setSpeed] = useState(1);
  const [spin, setSpin] = useState(() => autoRotate && !prefersReducedMotion());
  const [zoomed, setZoomed] = useState(false);
  const [viewIdx, setViewIdx] = useState(0);
  const [isFull, setIsFull] = useState(false);
  const [glDead, setGlDead] = useState(false);
  const reducedMotion = useMemo(() => prefersReducedMotion(), []);
  const live = useRef({ playing: !prefersReducedMotion(), speed: 1, simMin: 0, seek: -1 });
  const spinRef = useRef(autoRotate && !prefersReducedMotion());
  const dirtyRef = useRef(true);

  const n = data.frames.length;
  const rawDt = n > 1 ? data.meta.duration_min / (n - 1) : 1;
  const frameDt = Number.isFinite(rawDt) && rawDt > 0 ? rawDt : 1;
  const maxCells = useMemo(
    () => Math.max(1, ...data.frames.map((f) => f.cells.length)),
    [data],
  );
  const totalMin = data.meta.duration_min;

  useEffect(() => {
    live.current.playing = playing;
    live.current.speed = speed;
  }, [playing, speed]);

  // Reset per-frame state when a new trajectory arrives.
  useEffect(() => {
    setFrame(0);
    setZoomed(false);
    setViewIdx(0);
    live.current.simMin = 0;
    live.current.seek = -1;
  }, [data]);

  useEffect(() => {
    const mount = mountRef.current;
    if (!mount) return;
    // Fixed assay cell radius: XML volume 4188.79 um^3 => r ~= 10 um.
    // cell_radius_um is rejected by the API (never silently ignored).
    const radius = 10;

    const scene = new THREE.Scene();
    scene.background = new THREE.Color(BG);
    scene.fog = new THREE.Fog(BG, 320, 750);

    const camera = new THREE.PerspectiveCamera(45, 1, 0.5, 2500);
    camera.position.set(...VIEWS[0].pos);

    const renderer = new THREE.WebGLRenderer({ antialias: true, powerPreference: "low-power" });
    // Old phones: cap DPR — halves GPU fill cost, still crisp on small screens.
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 1.5));
    renderer.toneMapping = THREE.ACESFilmicToneMapping;
    renderer.toneMappingExposure = 1.0;
    mount.appendChild(renderer.domElement);

    const controls = new OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;
    controls.dampingFactor = 0.08;
    controls.minDistance = 30;
    controls.maxDistance = 450;
    controls.autoRotate = autoRotate && !prefersReducedMotion();
    controls.autoRotateSpeed = 1.0;
    rigRef.current = { camera, controls };
    const stopSpin = () => {
      controls.autoRotate = false;
      spinRef.current = false;
      setSpin(false);
    };
    controls.addEventListener("start", stopSpin);
    const markDirty = () => {
      dirtyRef.current = true;
    };
    controls.addEventListener("change", markDirty);

    scene.add(new THREE.HemisphereLight(0xffffff, 0xcfc9ee, 0.75));
    const key = new THREE.DirectionalLight(0xffffff, 1.6);
    key.position.set(70, 110, 50);
    scene.add(key);
    const fill = new THREE.DirectionalLight(0xdde4ff, 0.45);
    fill.position.set(-90, 30, -60);
    scene.add(fill);
    const rim = new THREE.DirectionalLight(0xffffff, 0.5);
    rim.position.set(-20, 60, -120);
    scene.add(rim);

    const grid = new THREE.GridHelper(320, 16, 0xb9c0e6, 0xd3d8f2);
    grid.position.y = -80;
    scene.add(grid);

    const mesh = new THREE.InstancedMesh(
      // 16x12 segments: ~40% fewer triangles than 24x16, same look at cell scale.
      new THREE.SphereGeometry(radius, 16, 12),
      new THREE.MeshStandardMaterial({ roughness: 0.3, metalness: 0.0 }),
      maxCells,
    );
    // Deterministic per-cell tint so the cluster reads as glossy individuals,
    // not one flat blob. Same id => same tint, every frame (data untouched).
    const tint = new THREE.Color();
    const tintFor = (id: string, dead: boolean) => {
      let h = 0;
      for (let i = 0; i < id.length; i++) h = (h * 31 + id.charCodeAt(i)) | 0;
      const j = ((h % 1000) / 1000 - 0.5) * 0.16;
      tint.copy(dead ? DEAD : LIVE);
      tint.offsetHSL(dead ? j * 0.5 : j * 0.3, 0.02, j);
      return tint;
    };
    mesh.instanceMatrix.setUsage(THREE.DynamicDrawUsage);
    mesh.frustumCulled = false;
    for (let i = 0; i < maxCells; i++) mesh.setColorAt(i, LIVE);
    if (n === 0) mesh.count = 0;
    scene.add(mesh);
    const dummy = new THREE.Object3D();

    const applyFrame = (idx: number) => {
      const cells = data.frames[idx]?.cells ?? [];
      let w = 0;
      for (let i = 0; i < cells.length; i++) {
        const c = cells[i];
        if (!isFinitePos(c)) continue;
        dummy.position.set(c.x_um, c.y_um, c.z_um);
        dummy.updateMatrix();
        mesh.setMatrixAt(w, dummy.matrix);
        mesh.setColorAt(w, tintFor(c.id, c.dead ?? false));
        w++;
      }
      mesh.count = w;
      mesh.instanceMatrix.needsUpdate = true;
      if (mesh.instanceColor) mesh.instanceColor.needsUpdate = true;
    };

    const st = live.current;
    st.simMin = 0;
    st.seek = -1;
    const duration = data.meta.duration_min;
    let last = performance.now();
    let lastIdx = -1;
    let raf = 0;
    const tick = (now: number) => {
      raf = requestAnimationFrame(tick);
      // Hidden tab: skip GPU work entirely (old phones overheat otherwise).
      if (document.hidden) {
        last = now;
        return;
      }
      const dtWall = Math.min((now - last) / 1000, 0.1);
      last = now;
      const animating = st.playing || spinRef.current;
      if (n <= 0) {
        if (animating || dirtyRef.current) {
          dirtyRef.current = false;
          controls.update();
          renderer.render(scene, camera);
        }
        return;
      }
      if (st.seek >= 0) {
        st.simMin = st.seek * frameDt;
        st.seek = -1;
      } else if (st.playing) {
        st.simMin += dtWall * SIM_MIN_PER_SEC * st.speed;
        if (st.simMin > duration) st.simMin = 0;
      }
      const idx = Math.min(n - 1, Math.max(0, Math.floor(st.simMin / frameDt)));
      if (idx !== lastIdx) {
        lastIdx = idx;
        applyFrame(idx);
        dirtyRef.current = true;
        setFrame(idx);
      }
      // Paused and untouched: skip GPU work (render on demand only).
      if (!animating && !dirtyRef.current) return;
      dirtyRef.current = false;
      controls.update();
      renderer.render(scene, camera);
    };
    raf = requestAnimationFrame(tick);

    const onContextLost = (e: Event) => {
      e.preventDefault();
      cancelAnimationFrame(raf);
      setGlDead(true);
    };
    renderer.domElement.addEventListener("webglcontextlost", onContextLost);

    const resize = () => {
      const w = mount.clientWidth;
      const h = mount.clientHeight;
      if (w === 0 || h === 0) return;
      camera.aspect = w / h;
      camera.updateProjectionMatrix();
      renderer.setSize(w, h);
      dirtyRef.current = true;
    };
    resize();
    const ro = new ResizeObserver(resize);
    ro.observe(mount);

    return () => {
      cancelAnimationFrame(raf);
      ro.disconnect();
      rigRef.current = null;
      controls.removeEventListener("start", stopSpin);
      controls.removeEventListener("change", markDirty);
      renderer.domElement.removeEventListener("webglcontextlost", onContextLost);
      controls.dispose();
      scene.traverse((obj) => {
        const anyObj = obj as unknown as {
          geometry?: THREE.BufferGeometry;
          material?: THREE.Material | THREE.Material[];
        };
        anyObj.geometry?.dispose();
        if (Array.isArray(anyObj.material)) anyObj.material.forEach((m) => m.dispose());
        else anyObj.material?.dispose();
      });
      renderer.dispose();
      mount.removeChild(renderer.domElement);
    };
  }, [data, n, frameDt, maxCells, autoRotate]);

  const seek = (idx: number) => {
    const clamped = n > 0 ? Math.min(n - 1, Math.max(0, idx)) : 0;
    live.current.seek = clamped;
    setFrame(clamped);
  };

  const toggleSpin = () => {
    const rig = rigRef.current;
    const next = !spin;
    spinRef.current = next;
    setSpin(next);
    dirtyRef.current = true;
    if (rig) rig.controls.autoRotate = next;
  };

  const toggleZoom = () => {
    const rig = rigRef.current;
    if (!rig) return;
    const { camera, controls } = rig;
    const off = camera.position.clone().sub(controls.target);
    const next = zoomed ? off.length() / 0.55 : off.length() * 0.55;
    off.setLength(Math.min(controls.maxDistance, Math.max(controls.minDistance, next)));
    camera.position.copy(controls.target).add(off);
    setZoomed(!zoomed);
  };

  const cycleView = () => {
    const rig = rigRef.current;
    const next = (viewIdx + 1) % VIEWS.length;
    setViewIdx(next);
    if (rig) {
      rig.camera.position.set(...VIEWS[next].pos);
      rig.controls.target.set(0, 0, 0);
    }
  };

  const toggleFullscreen = async () => {
    const el = mountRef.current;
    if (!el) return;
    try {
      if (document.fullscreenElement) {
        await document.exitFullscreen();
      } else {
        await el.requestFullscreen();
      }
    } catch {
      // Fullscreen unavailable (iframe/permissions): stay inline.
    }
  };

  useEffect(() => {
    const onChange = () => setIsFull(document.fullscreenElement === mountRef.current);
    document.addEventListener("fullscreenchange", onChange);
    return () => document.removeEventListener("fullscreenchange", onChange);
  }, []);

  const safeFrame = n > 0 ? Math.min(frame, n - 1) : 0;
  const f = data.frames[safeFrame] ?? {
    t_min: 0,
    contact: false,
    cells: [] as TrajectoryFile["frames"][number]["cells"],
  };
  const stats = frameStats(f.cells ?? []);
  const tLabel = fmtT(f.t_min, totalMin);
  const totalLabel = fmtT(totalMin, totalMin);

  return (
    <div className="viewer">
      <div
        className="canvas-wrap"
        ref={mountRef}
        role="img"
        aria-label={`Esferoide 3D, ${stats.live} vivas, ${stats.dead} muertas, t ${tLabel}`}
      >
        {glDead && (
          <div className="viewer-fallback" role="alert">
            <p>Tu dispositivo no pudo mostrar el 3D (WebGL no disponible).</p>
            <p>Los números de abajo y la gráfica siguen siendo los calculados por el motor.</p>
          </div>
        )}
        {badge && <div className="viewer-badge">{badge}</div>}
        <div className="viewer-toolbar" role="group" aria-label="herramientas de vista">
          <button
            type="button"
            className={spin ? "tool is-on" : "tool"}
            aria-pressed={spin}
            onClick={toggleSpin}
            disabled={reducedMotion}
            title={reducedMotion ? "Rotación desactivada (movimiento reducido)" : "Rotar cámara"}
          >
            <Icon d={PATH_ROTATE} />
            Rotar
          </button>
          <button
            type="button"
            className={zoomed ? "tool is-on" : "tool"}
            aria-pressed={zoomed}
            onClick={toggleZoom}
            title="Acercar / alejar"
          >
            <Icon d={PATH_ZOOM} />
            Zoom
          </button>
          <button type="button" className="tool" onClick={cycleView} title={`Vista actual: ${VIEWS[viewIdx].name}`}>
            <Icon d={PATH_EYE} />
            Vista
          </button>
        </div>
        <div className="player" role="group" aria-label="reproductor">
          <button
            type="button"
            className="player-play"
            onClick={() => setPlaying((p) => !p)}
            aria-label={playing ? "Pausar" : "Reproducir"}
          >
            {playing ? <Icon d={PATH_PAUSE} /> : <Icon d={PATH_PLAY} filled />}
          </button>
          <input
            type="range"
            className="player-slider"
            min={0}
            max={Math.max(0, n - 1)}
            value={safeFrame}
            onChange={(e) => seek(Number(e.target.value))}
            aria-label="fotograma"
            aria-valuetext={`fotograma ${n === 0 ? 0 : safeFrame + 1} de ${n}, t ${tLabel}`}
          />
          <span className="player-time">
            Tiempo {tLabel} / {totalLabel}
          </span>
          <div className="speed-seg" role="group" aria-label="velocidad">
            {[0.5, 1, 2, 4].map((v) => (
              <button
                key={v}
                type="button"
                className={speed === v ? "seg-btn is-on" : "seg-btn"}
                aria-pressed={speed === v}
                onClick={() => setSpeed(v)}
              >
                {v}x
              </button>
            ))}
          </div>
          <button
            type="button"
            className="player-full"
            onClick={toggleFullscreen}
            aria-label={isFull ? "Salir de pantalla completa" : "Pantalla completa"}
            title={isFull ? "Salir de pantalla completa" : "Pantalla completa"}
          >
            <Icon d={isFull ? PATH_UNFULL : PATH_FULL} />
          </button>
        </div>
      </div>
      <p className="viewer-caption">
        <span className="cap-live">{stats.live} vivas</span> ·{" "}
        <span className="cap-dead">{stats.dead} muertas</span> · r {stats.radius.toFixed(0)} µm · t {tLabel}
      </p>
      <p className="viewer-src">
        {data.meta.engine_id} v{data.meta.engine_version} · semilla {data.meta.seed}
      </p>
      {showChart && <SeriesChart data={data} frame={safeFrame} onSeek={seek} yMax={yMax} />}
    </div>
  );
}
