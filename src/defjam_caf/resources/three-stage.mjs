/** Shared scene lifecycle; page-specific posing and lighting controls stay with their workflow. */
export function createStage({ THREE, OrbitControls, viewport, fov = 32, far = 1000 }) {
  const scene = new THREE.Scene(),
    camera = new THREE.PerspectiveCamera(fov, 1, 0.01, far);
  const renderer = new THREE.WebGLRenderer({ alpha: true, antialias: true });
  renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
  renderer.setClearColor(0, 0);
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  viewport.append(renderer.domElement);
  const controls = new OrbitControls(camera, renderer.domElement);
  controls.enableDamping = true;
  const observer = new ResizeObserver(() => {
    renderer.setSize(viewport.clientWidth, viewport.clientHeight, false);
    camera.aspect = viewport.clientWidth / Math.max(1, viewport.clientHeight);
    camera.updateProjectionMatrix();
  });
  observer.observe(viewport);
  return { scene, camera, renderer, controls, observer };
}

export function disposeModel(model) {
  for (const child of [...model.children]) {
    child.traverse?.((part) => {
      part.geometry?.dispose();
      const materials = Array.isArray(part.material) ? part.material : [part.material];
      for (const material of materials) material?.dispose();
      part.skeleton?.dispose();
    });
    model.remove(child);
  }
}

export function frameStage({
  THREE,
  camera,
  controls,
  bounds,
  view = "fit",
  factor = 1.98,
  lift = 0.03,
  near = 0.001,
}) {
  if (!bounds) return;
  const [lo, hi] = bounds,
    center = new THREE.Vector3(...lo).add(new THREE.Vector3(...hi)).multiplyScalar(0.5);
  const height = Math.max(hi[1] - lo[1], 0.001),
    face = view === "face";
  const target = face ? new THREE.Vector3(center.x, hi[1] - height * 0.12, center.z) : center;
  const distance = height * (face ? 0.61 : factor);
  controls.target.copy(target);
  camera.position.set(
    target.x,
    target.y + (face ? 0 : height * lift),
    target.z + (view === "back" ? -distance : distance),
  );
  camera.near = Math.max(near, height * 0.001);
  camera.far = height * 100;
  camera.updateProjectionMatrix();
  controls.update();
}
