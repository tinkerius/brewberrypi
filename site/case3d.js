// Interactive 3D view of the case, from the STLs of brewberrypi-case (copied by tools/sync_assets.sh).

import * as THREE from "three";
import { STLLoader } from "./vendor/three/STLLoader.js";
import { OrbitControls } from "./vendor/three/OrbitControls.js";

// The STLs are in print orientation; these put each part back in its place in the case
// (inverse of the print transforms in brewberrypi-case/03-openscad/brewberrypi-case.scad).
const CASE_D = 160;      // case_d
const Z_DIV_TOP = 73;    // z_div_top
const H = 120;           // H, the lid seat
const LID_T = 3;         // lid_t
const EXPLODE = 55;      // mm per step when exploded (divider 1×, top lid 2×, bottom lid −1×)

const PARTS = [
  { name: "body", place: (m) => m, explode: 0 },
  { name: "divider", place: (m) => m.makeTranslation(0, CASE_D, Z_DIV_TOP).multiply(new THREE.Matrix4().makeRotationX(Math.PI)), explode: 1 },
  { name: "top_lid", place: (m) => m.makeTranslation(0, 0, H), explode: 2 },
  { name: "bottom_lid", place: (m) => m.makeTranslation(0, 0, -LID_T), explode: -1 },
];

function palette() {
  const theme = document.documentElement.dataset.theme ?? (matchMedia("(prefers-color-scheme: light)").matches ? "light" : "dark");
  const light = theme === "light";
  return {
    body: light ? "#f4eeea" : "#e9e0dc",
    divider: light ? "#c4821a" : "#e9b04f",
    top_lid: light ? "#8a2a4a" : "#93304f",
    bottom_lid: light ? "#6d2039" : "#8a2a4a",
  };
}

export async function mountCase(host, { reducedMotion = false } = {}) {
  const canvas = document.createElement("canvas");
  const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: true, powerPreference: "low-power" });
  renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  renderer.toneMapping = THREE.ACESFilmicToneMapping;

  const scene = new THREE.Scene();
  const camera = new THREE.PerspectiveCamera(30, 1, 1, 5000);

  // Light: soft sky, a warm key and a berry rim from behind.
  const hemi = new THREE.HemisphereLight(0xfff4ee, 0x2a1d22, 1.6);
  const key = new THREE.DirectionalLight(0xffffff, 2.4);
  key.position.set(300, 500, 400);
  const fill = new THREE.DirectionalLight(0xe9b04f, 0.8);
  fill.position.set(-400, 150, 200);
  const rim = new THREE.DirectionalLight(0xe0789a, 2.2);
  rim.position.set(-200, 200, -500);
  scene.add(hemi, key, fill, rim);

  // OpenSCAD is Z-up, three.js Y-up: turn the case so its front (−Y in OpenSCAD) faces the camera.
  const model = new THREE.Group();
  model.rotation.x = -Math.PI / 2;
  const pivot = new THREE.Group();
  pivot.add(model);
  scene.add(pivot);

  const loader = new STLLoader();
  const colours = palette();
  const meshes = await Promise.all(PARTS.map(async (part) => {
    const geometry = await loader.loadAsync(`models/case-${part.name}.stl`);
    geometry.applyMatrix4(part.place(new THREE.Matrix4()));
    geometry.computeVertexNormals();
    const material = new THREE.MeshStandardMaterial({ color: colours[part.name], roughness: 0.55, metalness: 0.05 });
    const mesh = new THREE.Mesh(geometry, material);
    mesh.userData = part;
    model.add(mesh);
    return mesh;
  }));

  // Centre the case on the pivot.
  const box = new THREE.Box3().setFromObject(model);
  const centre = box.getCenter(new THREE.Vector3());
  model.position.sub(centre);
  const size = box.getSize(new THREE.Vector3()).length();

  camera.position.set(size * 1.25, size * 0.85, size * 1.7);
  camera.lookAt(0, 0, 0);

  const controls = new OrbitControls(camera, canvas);
  controls.enableDamping = true;
  controls.enableZoom = false;
  controls.enablePan = false;
  controls.minPolarAngle = Math.PI * 0.15;
  controls.maxPolarAngle = Math.PI * 0.62;
  controls.autoRotate = !reducedMotion;
  controls.autoRotateSpeed = 1.1;

  // Replace the static render.
  host.querySelector(".case-fallback")?.remove();
  host.prepend(canvas);
  const button = host.querySelector("#case-explode");
  const hint = host.querySelector(".case-hint");
  button.hidden = false;
  hint.hidden = false;

  let exploded = 0;
  let explodeTarget = 0;
  button.addEventListener("click", () => {
    explodeTarget = explodeTarget ? 0 : 1;
    button.setAttribute("aria-pressed", String(Boolean(explodeTarget)));
    button.textContent = explodeTarget ? "Assemble" : "Explode";
    wake();
  });
  canvas.addEventListener("pointerdown", () => { controls.autoRotate = false; hint.hidden = true; wake(); });

  document.addEventListener("themechange", () => {
    const c = palette();
    for (const mesh of meshes) mesh.material.color.set(c[mesh.userData.name]);
    wake();
  });

  const resize = () => {
    const { clientWidth: w, clientHeight: h } = host;
    renderer.setSize(w, h, false);
    camera.aspect = w / h;
    // Fit the case on narrow screens.
    camera.zoom = Math.min(1, w / h / 1.1) * 1.05;
    camera.updateProjectionMatrix();
    wake();
  };
  new ResizeObserver(resize).observe(host);

  // Render only while visible and something moves.
  let visible = true;
  let frameId = 0;
  new IntersectionObserver(([entry]) => { visible = entry.isIntersecting; wake(); }).observe(host);
  function wake() { if (!frameId && visible) frameId = requestAnimationFrame(frame); }
  function frame() {
    frameId = 0;
    const step = reducedMotion ? 1 : 0.08;
    exploded += (explodeTarget - exploded) * step;
    if (Math.abs(explodeTarget - exploded) < 0.001) exploded = explodeTarget;
    for (const mesh of meshes) mesh.position.z = mesh.userData.explode * EXPLODE * exploded;
    const moving = controls.update() || controls.autoRotate || exploded !== explodeTarget;
    renderer.render(scene, camera);
    if (moving) wake();
  }
  resize();
}
