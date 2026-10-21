// The Legacy Artifact Snapshot materializer's core (ROUNDS-00A-L04).
//
// It takes the three values PocketBase reads from the caller's own records,
// the template id and design (a resume's own, or a variant's parent's) and
// the source's data, and returns either one snapshot's content or the reason
// none can be made. It never takes markup. React and the frontend's
// templates, shell, and empty-resume factory come in through
// createMaterializer, so the same core runs in the image's bundle
// (src/entry.mjs) and in the frontend's preview-parity test
// (frontend/test/materializerParity.test.tsx).
//
// The steps, in order, each a pure function of its input:
//
//   1. Resolve the template. An unknown id falls back to the registry's
//      first template, as templateById does, and says so in
//      template_fallback.
//   2. Validate the design against #2's Artifact Renderer Contract
//      (contracts/definitions/artifact-renderer.v1.schema.json, `overrides`)
//      on the six paths the templates read. Anything else there is
//      design_out_of_domain. Keys no template reads are dropped.
//   3. Normalize the data as the preview does, emptyResumeData() filling
//      missing sections and then the six hideable sections emptied when
//      hiddenSections lists them, and validate it against ResumeData, or
//      data_malformed.
//   4. Render the template to static markup inside the client export's
//      shell. Markup over 2 MiB is data_too_large.
//   5. Check the output (checkMarkup), or markup_unsafe.
//
// The same input always gives the same result, so the same source and
// materializer digest always give the same bytes.

import { createHash } from 'node:crypto';

// The output-check rules' version, stored on every snapshot. Raise it when
// checkMarkup changes what it accepts.
export const SANITIZER_VERSION = '1.0.0';

// A snapshot's markup may be at most this many bytes (UTF-8).
export const MAX_MARKUP_BYTES = 2 * 1024 * 1024;

export const INELIGIBLE_REASONS = Object.freeze([
  'design_out_of_domain',
  'data_malformed',
  'data_too_large',
  'markup_unsafe',
]);

// ---------------------------------------------------------------- design

// The grammar of artifact-renderer/v1's `overrides`, the only design values a
// user can set. The schema file is the source of truth; the materializer's
// tests check these lists against it.
export const FONT_IDS = Object.freeze([
  'inter',
  'playfair-display',
  'source-serif-pro',
  'source-sans-pro',
  'cmu-serif',
  'jetbrains-mono',
  'courier-prime',
]);
export const BULLET_STYLES = Object.freeze([
  'disc', 'circle', 'square', 'dot', 'dash', 'arrow', 'arrow-long', 'chevron', 'triangle', 'check',
  'star', 'star-outline', 'diamond', 'plus', 'asterisk', 'none',
]);
export const MARGIN_MM = Object.freeze({ min: 0, max: 30 });
export const BODY_SIZE = Object.freeze({ min: 9, max: 12 });
export const HEX_COLOR = /^#[0-9A-Fa-f]{6}$/;

// The font-family stack a template gets for each font id: the stack the
// templates themselves default to for that family.
export const FONT_STACKS = Object.freeze({
  inter: "'Inter', 'Helvetica Neue', system-ui, sans-serif",
  'playfair-display': "'Playfair Display', 'Georgia', serif",
  'source-serif-pro': "'Source Serif Pro', 'Georgia', 'Times New Roman', serif",
  'source-sans-pro': "'Source Sans Pro', 'Helvetica Neue', system-ui, sans-serif",
  'cmu-serif': "'CMU Serif', 'Latin Modern Roman', 'Source Serif Pro', 'Georgia', 'Times New Roman', serif",
  'jetbrains-mono': "'JetBrains Mono', 'IBM Plex Mono', 'Fira Code', 'Menlo', ui-monospace, monospace",
  'courier-prime': "'Courier Prime', 'Courier New', 'IBM Plex Mono', ui-monospace, monospace",
});

// The family name each font id renders as, lowercased, for font_families.
const FONT_NAMES = Object.freeze({
  inter: 'inter',
  'playfair display': 'playfair-display',
  'source serif pro': 'source-serif-pro',
  'source sans pro': 'source-sans-pro',
  'cmu serif': 'cmu-serif',
  'jetbrains mono': 'jetbrains-mono',
  'courier prime': 'courier-prime',
});

function isObject(value) {
  return value !== null && typeof value === 'object' && !Array.isArray(value);
}

// A nested design object: absent (undefined or null), an object, or invalid.
const INVALID = Symbol('invalid');
function branch(value) {
  if (value === undefined || value === null) return undefined;
  return isObject(value) ? value : INVALID;
}

function inRange(value, { min, max }) {
  return typeof value === 'number' && Number.isFinite(value) && value >= min && value <= max;
}

// Returns { ok: true, design } with only the contract's paths, or
// { ok: false }. undefined and null mean "not set", as they do for the
// templates, which read each value with `??`.
export function normalizeDesign(raw) {
  const source = raw === undefined || raw === null ? {} : raw;
  if (!isObject(source)) return { ok: false };
  const design = {};

  const spacing = branch(source.spacing);
  if (spacing === INVALID) return { ok: false };
  if (spacing && spacing.margin !== undefined && spacing.margin !== null) {
    if (!inRange(spacing.margin, MARGIN_MM)) return { ok: false };
    design.spacing = { margin: spacing.margin };
  }

  const typography = branch(source.typography);
  if (typography === INVALID) return { ok: false };
  if (typography) {
    const out = {};
    const body = branch(typography.body);
    const heading = branch(typography.heading);
    if (body === INVALID || heading === INVALID) return { ok: false };
    if (body) {
      const b = {};
      if (body.size !== undefined && body.size !== null) {
        if (!inRange(body.size, BODY_SIZE)) return { ok: false };
        b.size = body.size;
      }
      if (body.family !== undefined && body.family !== null) {
        if (!FONT_IDS.includes(body.family)) return { ok: false };
        b.family = body.family;
      }
      if (Object.keys(b).length) out.body = b;
    }
    if (heading && heading.family !== undefined && heading.family !== null) {
      if (!FONT_IDS.includes(heading.family)) return { ok: false };
      out.heading = { family: heading.family };
    }
    if (Object.keys(out).length) design.typography = out;
  }

  const colors = branch(source.colors);
  if (colors === INVALID) return { ok: false };
  if (colors && colors.primary !== undefined && colors.primary !== null) {
    if (typeof colors.primary !== 'string' || !HEX_COLOR.test(colors.primary)) return { ok: false };
    design.colors = { primary: colors.primary };
  }

  if (source.bulletStyle !== undefined && source.bulletStyle !== null) {
    if (!BULLET_STYLES.includes(source.bulletStyle)) return { ok: false };
    design.bulletStyle = source.bulletStyle;
  }
  return { ok: true, design };
}

// The TemplateConfig a template renders a normalized design with: font ids
// become their stacks, and an unset value stays unset so the template's own
// default applies.
export function templateConfig(design) {
  const config = {};
  if (design.spacing) config.spacing = { margin: design.spacing.margin };
  if (design.typography) {
    const typography = {};
    const { body, heading } = design.typography;
    if (body) {
      typography.body = {};
      if (body.size !== undefined) typography.body.size = body.size;
      if (body.family !== undefined) typography.body.family = FONT_STACKS[body.family];
    }
    if (heading) typography.heading = { family: FONT_STACKS[heading.family] };
    config.typography = typography;
  }
  if (design.colors) config.colors = { primary: design.colors.primary };
  if (design.bulletStyle) config.bulletStyle = design.bulletStyle;
  return config;
}

// ------------------------------------------------------------------ data

export const SECTION_KEYS = Object.freeze([
  'personal', 'experience', 'education', 'skills', 'projects', 'publications', 'profiles',
]);
// The sections hiddenSections empties, as PreviewPane and ZoomablePage do.
export const HIDEABLE_SECTIONS = Object.freeze([
  'experience', 'education', 'skills', 'projects', 'publications', 'profiles',
]);

// ResumeData (frontend/src/features/resume/types.ts), field by field, in the
// order the normalized data keeps. `text` is a string, `flag` a boolean, and
// `list` an array of strings. A required field must be present with its
// type; an optional one may also be absent or null, and a null is dropped,
// since every template reads it as unset. Fields ResumeData doesn't have are
// dropped, because no template reads them.
const PERSONAL = {
  required: { fullName: 'text' },
  optional: {
    email: 'text', phone: 'text', location: 'text', website: 'text', linkedin: 'text',
    github: 'text', title: 'text', subtitle: 'text', summary: 'text',
  },
};
const ENTRIES = {
  experience: {
    required: { id: 'text', company: 'text', position: 'text', highlights: 'list' },
    optional: { location: 'text', startDate: 'text', endDate: 'text', current: 'flag', description: 'text' },
  },
  education: {
    required: { id: 'text', institution: 'text' },
    optional: {
      degree: 'text', field: 'text', location: 'text', startDate: 'text', endDate: 'text',
      gpa: 'text', description: 'text',
    },
  },
  skills: {
    required: { id: 'text', category: 'text', items: 'list' },
    optional: {},
  },
  projects: {
    required: { id: 'text', name: 'text', technologies: 'list', highlights: 'list' },
    optional: { description: 'text', url: 'text', github: 'text', startDate: 'text', endDate: 'text' },
  },
  publications: {
    required: { id: 'text', title: 'text' },
    optional: { publisher: 'text', releaseDate: 'text', url: 'text', summary: 'text' },
  },
  profiles: {
    required: { id: 'text', network: 'text' },
    optional: { username: 'text', url: 'text' },
  },
};

function typed(value, type) {
  if (type === 'text') return typeof value === 'string';
  if (type === 'flag') return typeof value === 'boolean';
  return Array.isArray(value) && value.every((item) => typeof item === 'string');
}

// The record with only its spec's fields, or null when one fails.
function record(value, spec) {
  if (!isObject(value)) return null;
  const out = {};
  for (const [key, type] of Object.entries(spec.required)) {
    if (!typed(value[key], type)) return null;
    out[key] = type === 'list' ? [...value[key]] : value[key];
  }
  for (const [key, type] of Object.entries(spec.optional)) {
    const field = value[key];
    if (field === undefined || field === null) continue;
    if (!typed(field, type)) return null;
    out[key] = field;
  }
  return out;
}

function sectionKeys(value) {
  return Array.isArray(value) && value.every((key) => SECTION_KEYS.includes(key));
}

// Returns { ok: true, data } or { ok: false }.
export function normalizeData(raw, emptyResumeData) {
  const source = raw === undefined || raw === null ? {} : raw;
  if (!isObject(source)) return { ok: false };
  const filled = { ...emptyResumeData(), ...source };
  const hidden = Array.isArray(filled.hiddenSections) ? filled.hiddenSections : [];
  for (const key of HIDEABLE_SECTIONS) {
    if (hidden.includes(key)) filled[key] = [];
  }

  const personalInfo = record(filled.personalInfo, PERSONAL);
  if (!personalInfo) return { ok: false };
  const data = { personalInfo };
  for (const [key, spec] of Object.entries(ENTRIES)) {
    const list = filled[key];
    if (!Array.isArray(list)) return { ok: false };
    const entries = [];
    for (const entry of list) {
      const normalized = record(entry, spec);
      if (!normalized) return { ok: false };
      entries.push(normalized);
    }
    data[key] = entries;
  }
  for (const key of ['sectionOrder', 'hiddenSections']) {
    const value = filled[key];
    if (value === undefined || value === null) continue;
    if (!sectionKeys(value)) return { ok: false };
    data[key] = [...value];
  }
  return { ok: true, data };
}

// ---------------------------------------------------------- output checks

// Elements a snapshot may hold: the shell's, and inert structure and text.
// Anything else, a script, link, img, iframe, object, base, embed, svg, or
// form among them, fails the check.
const ELEMENTS = new Set([
  'html', 'head', 'meta', 'title', 'style', 'body',
  'a', 'abbr', 'address', 'article', 'aside', 'b', 'bdi', 'bdo', 'blockquote', 'br', 'caption', 'cite',
  'code', 'col', 'colgroup', 'data', 'dd', 'del', 'dfn', 'div', 'dl', 'dt', 'em', 'figcaption', 'figure',
  'footer', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'header', 'hgroup', 'hr', 'i', 'ins', 'kbd', 'li', 'main',
  'mark', 'nav', 'ol', 'p', 'pre', 'q', 's', 'samp', 'section', 'small', 'span', 'strong', 'sub', 'sup',
  'table', 'tbody', 'td', 'tfoot', 'th', 'thead', 'time', 'tr', 'u', 'ul', 'var', 'wbr',
]);
// Elements whose content is raw text up to their end tag.
const RAW_TEXT = new Set(['style', 'title']);
const ATTRIBUTES = new Set(['class', 'id', 'title', 'lang', 'dir', 'role', 'style', 'colspan', 'rowspan', 'datetime']);
const ELEMENT_ATTRIBUTES = {
  a: new Set(['href', 'target', 'rel']),
  meta: new Set(['charset', 'name', 'content']),
};
const INERT_ATTRIBUTE = /^(?:data|aria)-[a-z0-9-]+$/;
// The only character references React writes into an attribute value.
const ENTITIES = { '&amp;': '&', '&quot;': '"', '&#x27;': "'", '&lt;': '<', '&gt;': '>' };
const ENTITY = /&(?:amp|quot|#x27|lt|gt);/g;
// CSS that loads or runs something. url( and @import, plus the other ways a
// value can name a resource or script.
const CSS_LOADS = ['url(', '@import', 'image-set(', 'image(', 'cross-fade(', 'element(', 'expression(', '-moz-binding', 'behavior:'];
const HREF_SCHEMES = ['https:', 'mailto:'];

const DOCTYPE = '<!DOCTYPE html>';
// HTML tag-syntax whitespace is exactly these five characters. A browser's
// tokenizer does not treat U+00A0, U+FEFF, \v, or any other Unicode space
// as whitespace inside a tag, so neither may this one, or `\s` (which does)
// would let a construct hide: `<style >` would read as an element name
// of `style` here but as an unknown element in a browser, so live markup up
// to `</style` would be skipped as CSS text it never was.
const WSC = '\\t\\n\\f\\r ';
const WS = `[${WSC}]`;
const NAME_CHAR = `[^${WSC}"'<>/=]`;
const START_TAG = new RegExp(`<([a-zA-Z][a-zA-Z0-9-]*)((?:${WS}+${NAME_CHAR}+(?:${WS}*=${WS}*"[^"]*")?)*)${WS}*/?>`, 'y');
const END_TAG = new RegExp(`<\\/([a-zA-Z][a-zA-Z0-9-]*)${WS}*>`, 'y');
const ATTRIBUTE = new RegExp(`${WS}+(${NAME_CHAR}+)(?:${WS}*=${WS}*"([^"]*)")?`, 'y');

function decode(value) {
  // Any other `&` would be a character reference React never writes.
  const rest = value.replace(ENTITY, '');
  if (rest.includes('&')) return null;
  return value.replace(ENTITY, (m) => ENTITIES[m]);
}

function cssProblem(css, { comments }) {
  if (css.includes('\\')) return 'css-escape';
  let text = css;
  if (comments) {
    text = css.replace(/\/\*[\s\S]*?\*\//g, ' ');
    if (text.includes('/*')) return 'css-comment';
  } else if (css.includes('/*')) {
    return 'css-comment';
  }
  const lower = text.toLowerCase();
  if (lower.includes('url(')) return 'css-url';
  if (lower.includes('@import')) return 'css-import';
  if (CSS_LOADS.some((token) => lower.includes(token))) return 'css-load';
  return null;
}

function hrefAllowed(value) {
  // As a URL parser reads it: tabs and newlines anywhere are dropped, and
  // leading and trailing spaces and control characters are trimmed.
  const url = value.replace(/[\t\n\r]/g, '').replace(/^[\u0000- ]+|[\u0000- ]+$/g, '').toLowerCase();
  return HREF_SCHEMES.some((scheme) => url.startsWith(scheme));
}

// Checks rendered markup and returns { ok: true } or { ok: false, rule }.
// It reads the markup the way a browser tokenizes it, so a construct can't
// hide from it in text, an attribute, or a comment.
export function checkMarkup(markup) {
  const fail = (rule) => ({ ok: false, rule });
  if (typeof markup !== 'string') return fail('syntax');
  let i = markup.startsWith(DOCTYPE) ? DOCTYPE.length : 0;
  const n = markup.length;
  while (i < n) {
    const lt = markup.indexOf('<', i);
    if (lt === -1) break;
    i = lt;
    if (markup.startsWith('<!', i) || markup.startsWith('<?', i)) return fail('syntax');
    END_TAG.lastIndex = i;
    const end = END_TAG.exec(markup);
    if (end) {
      i = END_TAG.lastIndex;
      continue;
    }
    START_TAG.lastIndex = i;
    const start = START_TAG.exec(markup);
    if (!start) return fail('syntax');
    const name = start[1].toLowerCase();
    const attributes = [];
    ATTRIBUTE.lastIndex = 0;
    const source = start[2];
    for (let m = ATTRIBUTE.exec(source); m; m = ATTRIBUTE.exec(source)) {
      attributes.push({ name: m[1].toLowerCase(), raw: m[2] ?? '' });
    }
    if (attributes.some((a) => a.name.startsWith('on'))) return fail('event-handler');
    if (name === 'meta' && attributes.some((a) => a.name === 'http-equiv')) return fail('meta-http-equiv');
    if (!ELEMENTS.has(name)) return fail(`element:${name}`);
    for (const attribute of attributes) {
      const allowed = ATTRIBUTES.has(attribute.name) || INERT_ATTRIBUTE.test(attribute.name)
        || Boolean(ELEMENT_ATTRIBUTES[name]?.has(attribute.name));
      if (!allowed) return fail(`attribute:${attribute.name}`);
      const value = decode(attribute.raw);
      if (value === null) return fail('entity');
      if (attribute.name === 'style') {
        const problem = cssProblem(value, { comments: false });
        if (problem) return fail(problem);
      }
      if (attribute.name === 'href' && !hrefAllowed(value)) return fail('href-scheme');
    }
    i = START_TAG.lastIndex;
    if (RAW_TEXT.has(name)) {
      // A browser ends a raw-text element only at an appropriate end tag:
      // `</name` followed by tag whitespace, `/`, or `>`. `</namex>` does
      // not close it, so everything up to the real `</name>` is still raw
      // text, and the CSS there is still scanned.
      const closing = new RegExp(`</${name}(?=[${WSC}/>])`, 'ig');
      closing.lastIndex = i;
      const close = closing.exec(markup);
      if (!close) return fail('syntax');
      if (name === 'style') {
        const problem = cssProblem(markup.slice(i, close.index), { comments: true });
        if (problem) return fail(problem);
      }
      i = close.index;
    }
  }
  return { ok: true };
}

// ------------------------------------------------------------------ fonts

// The font ids the markup's font-family declarations name first, sorted.
export function fontFamilies(markup) {
  const found = new Set();
  const declarations = [];
  for (const m of markup.matchAll(/\sstyle="([^"]*)"/g)) declarations.push(decode(m[1]) ?? '');
  for (const m of markup.matchAll(/<style>([\s\S]*?)<\/style>/g)) declarations.push(m[1].replace(/\/\*[\s\S]*?\*\//g, ' '));
  for (const css of declarations) {
    for (const m of css.matchAll(/font-family\s*:\s*([^;}]+)/gi)) {
      const first = m[1].split(',')[0].trim().replace(/^['"]|['"]$/g, '').trim().toLowerCase();
      if (FONT_NAMES[first]) found.add(FONT_NAMES[first]);
    }
  }
  return [...found].sort();
}

// --------------------------------------------------------------- snapshot

function sha256(bytes) {
  return `sha256:${createHash('sha256').update(bytes).digest('hex')}`;
}

// Returns materialize({ template_id, design, data }), which answers
//   { status: 'ok', template_id, template_fallback, design, data, markup,
//     content_checksum, size_bytes, font_families, sanitizer_version }
// or { status: 'ineligible', reason, sanitizer_version }.
export function createMaterializer({ createElement, renderToStaticMarkup, templates, wrapStandaloneHtml, emptyResumeData }) {
  if (!Array.isArray(templates) || templates.length === 0) throw new Error('createMaterializer needs the template registry');
  const byId = new Map(templates.map((t) => [t.id, t]));
  const ineligible = (reason) => ({ status: 'ineligible', reason, sanitizer_version: SANITIZER_VERSION });

  return function materialize({ template_id: requested, design: rawDesign, data: rawData } = {}) {
    const template = (typeof requested === 'string' && byId.get(requested)) || templates[0];

    const design = normalizeDesign(rawDesign);
    if (!design.ok) return ineligible('design_out_of_domain');
    const data = normalizeData(rawData, emptyResumeData);
    if (!data.ok) return ineligible('data_malformed');

    let inner;
    try {
      inner = renderToStaticMarkup(createElement(template.component, {
        data: data.data,
        design: templateConfig(design.design),
      }));
    } catch {
      // A template can't render this data.
      return ineligible('data_malformed');
    }
    // Lone surrogates become U+FFFD here, as UTF-8 encoding would make them,
    // so the string and its bytes agree.
    const markup = wrapStandaloneHtml(inner).toWellFormed();
    const bytes = new TextEncoder().encode(markup);
    if (bytes.length > MAX_MARKUP_BYTES) return ineligible('data_too_large');
    if (!checkMarkup(markup).ok) return ineligible('markup_unsafe');

    return {
      status: 'ok',
      template_id: template.id,
      template_fallback: template.id !== requested,
      design: design.design,
      data: data.data,
      markup,
      content_checksum: sha256(bytes),
      size_bytes: bytes.length,
      font_families: fontFamilies(markup),
      sanitizer_version: SANITIZER_VERSION,
    };
  };
}
