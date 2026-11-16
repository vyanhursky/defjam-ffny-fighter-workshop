const littleEndian = new Uint8Array(new Uint16Array([1]).buffer)[0] === 1;
const types = {
  f32le: [Float32Array, 4, "getFloat32"],
  u16le: [Uint16Array, 2, "getUint16"],
  u32le: [Uint32Array, 4, "getUint32"],
};

export function decodeAttribute(spec) {
  const type = types[spec.kind];
  if (
    !type ||
    !Number.isSafeInteger(spec.count) ||
    spec.count < 0 ||
    spec.count * type[1] > 32 * 1024 ** 2 ||
    ![1, 2, 3].includes(spec.components) ||
    spec.count % spec.components ||
    typeof spec.data !== "string" ||
    spec.data.length > 4 * Math.ceil((32 * 1024 ** 2) / 3)
  )
    throw new Error("Invalid preview attribute");
  const raw = atob(spec.data),
    [ArrayType, width, getter] = type;
  if (raw.length !== spec.count * width) throw new Error("Truncated preview attribute");
  const bytes = Uint8Array.from(raw, (c) => c.charCodeAt(0));
  let values;
  if (littleEndian) values = new ArrayType(bytes.buffer);
  else {
    const view = new DataView(bytes.buffer);
    values = new ArrayType(spec.count);
    for (let i = 0; i < values.length; i++) values[i] = view[getter](i * width, true);
  }
  if (spec.kind === "f32le" && !values.every(Number.isFinite)) throw new Error("Non-finite preview attribute");
  return values;
}

function rows(values, width) {
  return Array.from({ length: values.length / width }, (_, i) =>
    Array.from(values.subarray(i * width, (i + 1) * width)),
  );
}

export function unpackPreview(value) {
  if (!value?.meshes) return value;
  return {
    ...value,
    meshes: value.meshes.map((part) => {
      if (!part.geometry) return part;
      if (part.geometry.encoding !== "typed-geometry-1") throw new Error("Unsupported preview geometry");
      const source = part.geometry.attributes,
        attributes = {};
      for (const [key, width] of [
        ["positions", 3],
        ["normals", 3],
        ["uv", 2],
        ["indices", 1],
      ]) {
        if (source[key]?.components !== width) throw new Error("Invalid preview attribute dimensions");
        if (key === "indices" ? !["u16le", "u32le"].includes(source[key].kind) : source[key].kind !== "f32le")
          throw new Error("Invalid preview attribute type");
        attributes[key] = decodeAttribute(source[key]);
      }
      const count = attributes.positions.length / 3;
      if (
        attributes.normals.length !== count * 3 ||
        attributes.uv.length !== count * 2 ||
        !attributes.indices.every((index) => index < count)
      )
        throw new Error("Invalid preview vertex references");
      return {
        ...part,
        positions: rows(attributes.positions, 3),
        normals: rows(attributes.normals, 3),
        uv: rows(attributes.uv, 2),
        indices: Array.from(attributes.indices),
        _attributes: attributes,
      };
    }),
  };
}

export function geometryFor(THREE, part) {
  const geometry = new THREE.BufferGeometry(),
    arrays = part._attributes;
  for (const [name, key, width] of [
    ["position", "positions", 3],
    ["normal", "normals", 3],
    ["uv", "uv", 2],
  ]) {
    geometry.setAttribute(name, new THREE.BufferAttribute(arrays?.[key] || new Float32Array(part[key].flat()), width));
  }
  if (arrays) geometry.setIndex(new THREE.BufferAttribute(arrays.indices, 1));
  else geometry.setIndex(part.indices);
  return geometry;
}
