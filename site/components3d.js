// Bought components for the 3D case view: simplified models of the parts in brewberrypi-case/01-requirements/inputs/
// (C1–C8), at the positions of the case spec (02-specification/spec.md, F3–F14). Same coordinates as the STLs:
// mm, origin at the front-left-bottom outer corner, +X right, +Y back, +Z up.

import * as THREE from "three";

const HV_H = 70;                 // hv_h: divider underside
const Z_DIV_TOP = 73;            // z_div_top
const CASE_D = 160;              // case_d: outer face of the back wall
const PI_POS = [40, 37.5];       // pi_pos: corner of the Pi's footprint (56 × 85)
const PI_TOP = Z_DIV_TOP + 10 + 1.6;   // 10 mm brass standoffs, 1.6 mm board

function makeMaterials() {
  const m = (color, roughness = 0.55, metalness = 0, extra = {}) =>
    new THREE.MeshStandardMaterial({ color, roughness, metalness, ...extra });
  return {
    pcbPi: m(0x1e7a46, 0.5),
    pcbRelay: m(0xc4262e, 0.5),
    relay: m(0x2c63c9, 0.4),
    terminal: m(0x2f72dc, 0.45),
    plastic: m(0x2a2a2e, 0.5),
    hole: m(0x0b0b0d, 0.8),
    chip: m(0x1b1b1d, 0.35),
    // Low metalness: the scene has no environment map to reflect, so real metal values would render dark.
    metal: m(0xd5d9dd, 0.35, 0.35),
    brass: m(0xd2a84e, 0.35, 0.4),
    gold: m(0xe0bc62, 0.3, 0.45),
    white: m(0xe9e3d5, 0.6),
    yellow: m(0xf0c419, 0.5),
    rocker: m(0x3fd463, 0.25, 0, { emissive: 0x1d9c3a, emissiveIntensity: 0.7 }),
    mark: m(0xf4fff4, 0.4, 0, { emissive: 0xb8ffc8, emissiveIntensity: 0.5 }),
    brown: m(0x7a4a24, 0.5),
    blue: m(0x2d5fb0, 0.5),
    copper: m(0xc87533, 0.3, 0.9),
  };
}

// ---------- Shapes ----------

/** A box from its corner (x0, y0, z0) and size. */
function box(mat, [x0, y0, z0], [sx, sy, sz]) {
  const mesh = new THREE.Mesh(new THREE.BoxGeometry(sx, sy, sz), mat);
  mesh.position.set(x0 + sx / 2, y0 + sy / 2, z0 + sz / 2);
  return mesh;
}

/** A cylinder around its centre, along Y (front to back) unless axis is "x" or "z". */
function cyl(mat, [x, y, z], d, length, { axis = "y", sides = 32 } = {}) {
  const mesh = new THREE.Mesh(new THREE.CylinderGeometry(d / 2, d / 2, length, sides), mat);
  if (axis === "z") mesh.rotation.x = Math.PI / 2;
  if (axis === "x") mesh.rotation.z = Math.PI / 2;
  mesh.position.set(x, y, z);
  return mesh;
}

function roundedRect(w, h, r) {
  const s = new THREE.Shape();
  const x = -w / 2, y = -h / 2;
  s.moveTo(x + r, y);
  s.lineTo(x + w - r, y); s.quadraticCurveTo(x + w, y, x + w, y + r);
  s.lineTo(x + w, y + h - r); s.quadraticCurveTo(x + w, y + h, x + w - r, y + h);
  s.lineTo(x + r, y + h); s.quadraticCurveTo(x, y + h, x, y + h - r);
  s.lineTo(x, y + r); s.quadraticCurveTo(x, y, x + r, y);
  return s;
}

function polygon(points) {
  const s = new THREE.Shape();
  points.forEach(([x, y], i) => (i ? s.lineTo(x, y) : s.moveTo(x, y)));
  s.closePath();
  return s;
}

/** A 2D shape in the X-Z plane, centred at (cx, cz), extruded from y0 to y0 + depth. */
function panel(mat, shape, cx, y0, cz, depth) {
  const geometry = new THREE.ExtrudeGeometry(shape, { depth, bevelEnabled: false, curveSegments: 8 });
  geometry.rotateX(Math.PI / 2);   // shape y → z, extrusion → −y
  const mesh = new THREE.Mesh(geometry, mat);
  mesh.position.set(cx, y0 + depth, cz);
  return mesh;
}

function tube(mat, points, radius) {
  const curve = new THREE.CatmullRomCurve3(points.map((p) => new THREE.Vector3(...p)));
  return new THREE.Mesh(new THREE.TubeGeometry(curve, 64, radius, 10), mat);
}

// ---------- On the divider (move with it) ----------

/** C8: Raspberry Pi 3 B, GPIO header to the left wall, USB/Ethernet to the back, power to the feed-through (F11). */
function raspberryPi(M) {
  const g = new THREE.Group();
  // Board coordinates: x along the 85 mm edge (→ case +Y), y along the 56 mm edge (GPIO side → case −X), z up from the board.
  const at = (x, y) => [PI_POS[0] + 56 - y, PI_POS[1] + x];
  const b = (mat, [x, y, z], [sx, sy, sz]) => g.add(box(mat, [PI_POS[0] + 56 - y - sy, PI_POS[1] + x, PI_TOP + z], [sy, sx, sz]));

  b(M.pcbPi, [0, 0, -1.6], [85, 56, 1.6]);
  for (const [x, y] of [[3.5, 3.5], [61.5, 3.5], [3.5, 52.5], [61.5, 52.5]]) {
    const [cx, cy] = at(x, y);
    g.add(cyl(M.brass, [cx, cy, Z_DIV_TOP + 5], 5.5, 10, { axis: "z", sides: 6 }));
  }
  // GPIO header: 2 × 20 pins
  b(M.chip, [7.1, 49.9, 0], [50.8, 5.1, 2.5]);
  const pins = new THREE.InstancedMesh(new THREE.BoxGeometry(0.64, 0.64, 6), M.gold, 40);
  const pose = new THREE.Matrix4();
  for (let i = 0; i < 40; i++) {
    const [cx, cy] = at(8.37 + Math.floor(i / 2) * 2.54, 51.17 + (i % 2) * 2.54);
    pins.setMatrixAt(i, pose.makeTranslation(cx, cy, PI_TOP + 5.5));
  }
  g.add(pins);
  // Back edge: Ethernet and 2 × 2 USB
  b(M.metal, [65.5, 2.25, 0], [21.5, 16, 13.5]);
  b(M.hole, [86.95, 4.25, 1.5], [0.2, 12, 9.5]);
  for (const y of [22.4, 40.4]) {
    b(M.metal, [69.5, y, 0], [17.5, 13.2, 15.6]);
    b(M.hole, [86.95, y + 1.4, 2.4], [0.2, 10.4, 4.6]);
    b(M.hole, [86.95, y + 1.4, 9.8], [0.2, 10.4, 4.6]);
  }
  // Power edge: micro-USB, HDMI, audio
  b(M.metal, [6.9, -1.2, 0], [7.5, 5.6, 2.6]);
  b(M.metal, [24.5, -1.5, 0], [15, 11.5, 6.5]);
  b(M.chip, [50, -2, 0], [7, 12.5, 6]);
  // Camera and display connectors, SoC, USB/LAN chip, microSD card underneath
  b(M.white, [44, 1.5, 0], [3, 21, 5.5]);
  b(M.white, [1.5, 17, 0], [3, 21, 5.5]);
  b(M.metal, [16, 25, 0], [14, 14, 1.3]);
  b(M.chip, [55, 27, 0], [8, 8, 1]);
  b(M.metal, [0.5, 21.5, -3], [12, 12, 1.4]);
  b(M.chip, [-2.5, 22.5, -2.8], [6, 10, 0.8]);
  return g;
}

/** C1: 4-channel relay board, relays facing down, relay terminals to the back (F12). */
function relayBoard(M) {
  const g = new THREE.Group();
  const z = HV_H - 10 - 1.6;   // PCB underside, on 10 mm standoffs
  g.add(box(M.pcbRelay, [27, 54, z], [75, 52, 1.6]));
  for (let i = 0; i < 4; i++) {
    const x = 31 + i * 17.2;
    g.add(box(M.relay, [x, 74, z - 15.3], [15.5, 19, 15.3]));
    g.add(box(M.terminal, [x, 96, z - 10], [15, 8, 10]));
    for (let k = 0; k < 3; k++) g.add(cyl(M.metal, [x + 2.5 + k * 5, 100, z - 10.2], 3, 0.4, { axis: "z", sides: 16 }));
    g.add(box(M.chip, [x + 4.5, 66, z - 2.5], [6, 4, 2.5]));
  }
  g.add(box(M.terminal, [30, 55, z - 10], [30, 8, 10]));
  for (let k = 0; k < 6; k++) g.add(cyl(M.metal, [32.5 + k * 5, 59, z - 10.2], 3, 0.4, { axis: "z", sides: 16 }));
  g.add(box(M.yellow, [84, 56, z - 6], [12, 5, 6]));
  return g;
}

/** C2: USB-C power adapter, port face down, mains leads from the side towards the feed-through (F14). */
function adapter(M) {
  const g = new THREE.Group();
  const [w, d, h, c] = [51, 49, 27, 7];
  const profile = polygon([[-w / 2, -h / 2], [w / 2, -h / 2], [w / 2, h / 2 - c], [w / 2 - c, h / 2], [-w / 2 + c, h / 2], [-w / 2, h / 2 - c]]);
  g.add(panel(M.plastic, profile, 123 + w / 2, 61, 37 + h / 2, d));
  g.add(box(M.hole, [144, 98.4, 36.8], [9, 3.2, 0.3]));          // USB-C port
  g.add(cyl(M.plastic, [120.5, 70, 50], 6, 5, { axis: "x" }));      // cable grommet
  g.add(tube(M.brown, [[118, 69, 50.5], [111, 68, 46], [108, 70, 34], [110, 74, 24]], 1.1));
  g.add(tube(M.blue, [[118, 71, 49.5], [112, 72, 45], [110, 75, 33], [113, 78, 24]], 1.1));
  return g;
}

/** USB cable from the adapter, through the feed-through (F13), to the Pi's power socket. */
function usbCable(M) {
  const g = new THREE.Group();
  g.add(box(M.plastic, [144.5, 97.5, 26], [8, 5, 10.8]));          // USB-C plug
  g.add(box(M.plastic, [97.5, 44.6, 83.6], [9, 7, 4.6]));          // micro-USB plug
  g.add(tube(M.plastic, [[148.5, 100, 26], [147, 100, 18], [132, 96, 14], [115, 90, 20], [111, 86, 45], [111, 82, 70],
    [111, 72, 84], [110, 56, 89], [106.5, 48.1, 85.9]], 1.7));
  return g;
}

// ---------- In the body ----------

const BAR = new THREE.BoxGeometry(1, 0.3, 5);              // rocker symbols "I"
const RING = new THREE.TorusGeometry(2, 0.45, 8, 24);       // and "O"

/** C6 / C7: illuminated rocker switch, front panel (F3). */
function rockerSwitch(M, x, main) {
  const g = new THREE.Group();
  const z = 40;
  const [bw, bh] = main ? [25.5, 34.5] : [25.7, 34.5];
  const [w, h] = main ? [21, 25] : [21.5, 27];
  const depth = main ? 15.1 : 21;
  g.add(panel(M.plastic, roundedRect(bw, bh, 2.5), x, -4, z, 4));
  const rocker = panel(M.rocker, roundedRect(bw - 5, bh - 6, 4), 0, -3, 0, 3);
  rocker.position.set(x, -4, z);
  rocker.rotation.x = main ? 0.12 : 0;
  // Symbols on the rocker: I / O, and I / O / II on the 3-position switches
  const symbol = (geometry, dx, dz) => {
    const mesh = new THREE.Mesh(geometry, M.mark);
    mesh.position.set(dx, -3.1, dz);
    if (geometry === RING) mesh.rotation.x = Math.PI / 2;
    rocker.add(mesh);
  };
  if (main) { symbol(BAR, 0, 8); symbol(RING, 0, -8); }
  else { symbol(BAR, 0, 9); symbol(RING, 0, 0); symbol(BAR, -1.2, -9); symbol(BAR, 1.2, -9); }
  g.add(rocker);
  g.add(box(M.plastic, [x - w / 2, 0, z - h / 2], [w, depth, h]));
  const rows = main ? [-5, 5] : [-8, 0, 8];
  for (const dz of rows) for (const dx of [-5.5, 5.5]) g.add(box(M.metal, [x + dx - 3.15, depth, z + dz - 0.4], [6.3, 9.5, 0.8]));
  return g;
}

/** C5: earthed panel socket with hinged cover, back panel (F7). */
function powerSocket(M, x) {
  const g = new THREE.Group();
  const z = 38;
  g.add(cyl(M.plastic, [x, CASE_D - 13, z], 43, 26));
  g.add(panel(M.plastic, roundedRect(50, 50, 6), x, CASE_D, z, 3));
  for (const dx of [-19, 19]) for (const dz of [-19, 19]) g.add(cyl(M.metal, [x + dx, CASE_D + 3.4, z + dz], 6.5, 0.8));
  g.add(panel(M.plastic, roundedRect(42, 50, 15), x, CASE_D + 3, z - 1, 16));
  g.add(box(M.plastic, [x - 12.5, CASE_D + 3, z + 21], [25, 13, 16]));      // hinge, up to 62 mm overall
  g.add(cyl(M.plastic, [x, CASE_D + 12, z + 30], 7, 25, { axis: "x" }));
  g.add(box(M.hole, [x - 11, CASE_D + 19, z - 9], [22, 0.3, 13]));          // label field
  return g;
}

/** C4: IEC C14 inlet with fuse drawer, back panel (F6). */
function iecInlet(M) {
  const g = new THREE.Group();
  const [x, z] = [35, 38];
  g.add(panel(M.plastic, roundedRect(27, 31, 1), x, CASE_D - 27.6, z, 27.6));
  const flange = polygon([[-21.9, -7], [-13.5, -16.4], [13.5, -16.4], [21.9, -7], [21.9, 7], [13.5, 16.4], [-13.5, 16.4], [-21.9, 7]]);
  g.add(panel(M.plastic, flange, x, CASE_D, z, 3.1));
  g.add(panel(M.hole, polygon([[-12, 7], [12, 7], [12, -1], [8, -6], [-8, -6], [-12, -1]]), x, CASE_D + 3.1, z + 4, 0.2));
  for (const [dx, dz, w, hh] of [[-6.5, 2, 1.2, 4.5], [6.5, 2, 1.2, 4.5], [0, 7.5, 4.5, 1.2]]) {
    g.add(box(M.metal, [x + dx - w / 2, CASE_D + 3.15, z + dz - hh / 2], [w, 0.6, hh]));
  }
  g.add(box(M.chip, [x - 9, CASE_D + 3.1, z - 13], [18, 1, 6]));            // fuse drawer
  for (const dx of [-18, 18]) g.add(cyl(M.metal, [x + dx, CASE_D + 3.5, z], 5.5, 0.8));
  return g;
}

/** C3: 3.5 mm jack for the temperature probe, back panel above the inlet (F8). */
function jack(M) {
  const g = new THREE.Group();
  const [x, z] = [35, 98];
  g.add(cyl(M.plastic, [x, CASE_D + 1.5, z], 10, 3));
  g.add(cyl(M.gold, [x, CASE_D + 3.05, z], 5, 0.2));
  g.add(cyl(M.hole, [x, CASE_D + 3.15, z], 3.5, 0.2));
  g.add(cyl(M.metal, [x, CASE_D - 2.6, z], 12.5, 2, { sides: 6 }));       // hex nut, in its pocket
  g.add(cyl(M.plastic, [x, CASE_D - 9.1, z], 9, 11));
  for (const dz of [-2.5, 2.5]) g.add(box(M.metal, [x - 1, CASE_D - 19, z + dz - 0.2], [2, 4.5, 0.4]));
  return g;
}

/**
 * The components in two groups: `divider` (Pi, relay board, adapter, USB cable: they move with the divider)
 * and `body` (switches, sockets, inlet, jack). `materials` lists every material, for fading.
 */
export function buildComponents() {
  const M = makeMaterials();
  const divider = new THREE.Group();
  divider.add(raspberryPi(M), relayBoard(M), adapter(M), usbCable(M));
  const body = new THREE.Group();
  body.add(rockerSwitch(M, 40, true), rockerSwitch(M, 115, false), rockerSwitch(M, 150, false));
  body.add(powerSocket(M, 90), powerSocket(M, 145), iecInlet(M), jack(M));
  return { divider, body, materials: Object.values(M) };
}
