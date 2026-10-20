// A small JSON Schema (2020-12) validator for the subset the conformance
// schemas use: type, enum, const, required, properties, additionalProperties,
// items, minItems, maxItems, uniqueItems, minLength, maxLength, pattern,
// minimum, maximum, $ref to "#/$defs/...", anyOf, oneOf, allOf, not, and
// if/then/else. Anything else in a schema is an error, so a schema can't
// silently rely on a keyword this validator ignores.

const KNOWN = new Set([
  '$schema', '$id', '$comment', '$defs', 'title', 'description', 'examples', 'default',
  'type', 'enum', 'const', 'required', 'properties', 'additionalProperties', 'items',
  'minItems', 'maxItems', 'uniqueItems', 'minLength', 'maxLength', 'pattern', 'minimum',
  'maximum', '$ref', 'anyOf', 'oneOf', 'allOf', 'not', 'if', 'then', 'else',
]);

function typeOf(value) {
  if (value === null) return 'null';
  if (Array.isArray(value)) return 'array';
  if (Number.isInteger(value)) return 'integer';
  return typeof value;
}

function typeMatches(value, type) {
  const actual = typeOf(value);
  if (type === 'number') return actual === 'number' || actual === 'integer';
  return actual === type;
}

function pointer(parts) {
  return parts.length ? `/${parts.map((p) => String(p).replace(/~/g, '~0').replace(/\//g, '~1')).join('/')}` : '';
}

function resolveRef(root, ref) {
  if (!ref.startsWith('#/')) throw new Error(`unsupported $ref ${ref}`);
  let node = root;
  for (const part of ref.slice(2).split('/')) node = node?.[part.replace(/~1/g, '/').replace(/~0/g, '~')];
  if (!node) throw new Error(`unresolved $ref ${ref}`);
  return node;
}

function equal(a, b) {
  return JSON.stringify(a) === JSON.stringify(b);
}

// Returns a list of { pointer, keyword, message, property? } errors.
export function validate(value, schema, root = schema, at = []) {
  const errors = [];
  if (schema === true) return errors;
  if (schema === false) return [{ pointer: pointer(at), keyword: 'false', message: 'no value is allowed here' }];
  for (const key of Object.keys(schema)) {
    if (!KNOWN.has(key)) throw new Error(`schema keyword "${key}" is not supported (at ${pointer(at) || '/'})`);
  }
  const push = (keyword, message, extra = {}) => errors.push({ pointer: pointer(at), keyword, message, ...extra });

  if (schema.$ref) errors.push(...validate(value, resolveRef(root, schema.$ref), root, at));
  if (schema.type) {
    const types = Array.isArray(schema.type) ? schema.type : [schema.type];
    if (!types.some((t) => typeMatches(value, t))) {
      push('type', `expected ${types.join(' or ')}, got ${typeOf(value)}`);
      return errors;
    }
  }
  if (schema.enum && !schema.enum.some((v) => equal(v, value))) push('enum', `must be one of ${schema.enum.map((v) => JSON.stringify(v)).join(', ')}`);
  if (Object.prototype.hasOwnProperty.call(schema, 'const') && !equal(schema.const, value)) push('const', `must equal ${JSON.stringify(schema.const)}`);

  if (typeOf(value) === 'string') {
    const length = [...value].length;
    if (schema.minLength !== undefined && length < schema.minLength) push('minLength', `must be at least ${schema.minLength} characters`);
    if (schema.maxLength !== undefined && length > schema.maxLength) push('maxLength', `must be at most ${schema.maxLength} characters`);
    if (schema.pattern && !new RegExp(schema.pattern, 'u').test(value)) push('pattern', `must match ${schema.pattern}`);
  }
  if (typeOf(value) === 'integer' || typeOf(value) === 'number') {
    if (schema.minimum !== undefined && value < schema.minimum) push('minimum', `must be >= ${schema.minimum}`);
    if (schema.maximum !== undefined && value > schema.maximum) push('maximum', `must be <= ${schema.maximum}`);
  }
  if (Array.isArray(value)) {
    if (schema.minItems !== undefined && value.length < schema.minItems) push('minItems', `must have at least ${schema.minItems} items`);
    if (schema.maxItems !== undefined && value.length > schema.maxItems) push('maxItems', `must have at most ${schema.maxItems} items`);
    if (schema.uniqueItems) {
      const seen = new Set();
      value.forEach((item) => {
        const key = JSON.stringify(item);
        if (seen.has(key)) push('uniqueItems', `duplicate item ${key}`);
        seen.add(key);
      });
    }
    if (schema.items !== undefined) value.forEach((item, i) => errors.push(...validate(item, schema.items, root, [...at, i])));
  }
  if (typeOf(value) === 'object') {
    for (const name of schema.required || []) {
      if (!Object.prototype.hasOwnProperty.call(value, name)) push('required', `missing required field "${name}"`, { property: name });
    }
    const props = schema.properties || {};
    for (const [name, sub] of Object.entries(props)) {
      if (Object.prototype.hasOwnProperty.call(value, name)) errors.push(...validate(value[name], sub, root, [...at, name]));
    }
    if (schema.additionalProperties !== undefined) {
      for (const name of Object.keys(value)) {
        if (Object.prototype.hasOwnProperty.call(props, name)) continue;
        if (schema.additionalProperties === false) push('additionalProperties', `unknown field "${name}"`, { property: name });
        else errors.push(...validate(value[name], schema.additionalProperties, root, [...at, name]));
      }
    }
  }
  if (schema.allOf) for (const sub of schema.allOf) errors.push(...validate(value, sub, root, at));
  if (schema.anyOf && !schema.anyOf.some((sub) => validate(value, sub, root, at).length === 0)) {
    const branches = schema.anyOf.map((sub) => validate(value, sub, root, at));
    const missing = branches.flat().filter((e) => e.keyword === 'required');
    push('anyOf', 'does not match any allowed shape', missing.length ? { property: missing[0].property, branches } : { branches });
  }
  if (schema.oneOf) {
    const matches = schema.oneOf.filter((sub) => validate(value, sub, root, at).length === 0).length;
    if (matches !== 1) push('oneOf', `must match exactly one allowed shape (matched ${matches})`);
  }
  if (schema.not && validate(value, schema.not, root, at).length === 0) push('not', 'matches a disallowed shape');
  if (schema.if) {
    const branch = validate(value, schema.if, root, at).length === 0 ? schema.then : schema.else;
    if (branch !== undefined) errors.push(...validate(value, branch, root, at));
  }
  return errors;
}
