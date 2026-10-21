// The materializer bundle (ROUNDS-00A-L04), in the image the way CI's
// materializer job runs it:
//
//   finch build -f backend/materializer/Dockerfile -t rounds-materializer:test .
//   finch run --rm --network none --read-only \
//     -v "$PWD/backend/materializer/test:/app/test:ro" \
//     -v "$PWD/tests/conformance/rd_02:/tests/conformance/rd_02:ro" \
//     rounds-materializer:test node --test 'test/*.test.mjs'

import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { describe, it } from 'node:test';

import {
  checkMarkup,
  materialize,
  SANITIZER_VERSION,
  TEMPLATE_IDS,
  wrapStandaloneHtml,
} from '../dist/materialize.mjs';
import { DESIGN, HIDDEN, RICH, SECTION_MARKERS } from './fixtures.mjs';

const clone = (value) => structuredClone(value);

// The article inside a snapshot's shell.
function article(markup) {
  const start = markup.indexOf('<article data-resume-page');
  const end = markup.lastIndexOf('</article>') + '</article>'.length;
  return markup.slice(start, end);
}

describe('materializer: snapshots', () => {
  it('ships the 19 templates of the renderer contract', () => {
    assert.equal(TEMPLATE_IDS.length, 19);
    assert.equal(new Set(TEMPLATE_IDS).size, 19);
    assert.equal(TEMPLATE_IDS[0], 'modern');
  });

  for (const id of TEMPLATE_IDS) {
    it(`materializes ${id} twice to the same bytes, inside the client export's shell`, () => {
      const first = materialize({ template_id: id, design: clone(DESIGN), data: clone(RICH) });
      const second = materialize({ template_id: id, design: clone(DESIGN), data: clone(RICH) });
      assert.equal(first.status, 'ok');
      assert.deepEqual(second, first);
      assert.equal(first.template_id, id);
      assert.equal(first.template_fallback, false);
      assert.equal(first.markup, wrapStandaloneHtml(article(first.markup)));
      const bytes = Buffer.from(first.markup, 'utf8');
      assert.equal(first.size_bytes, bytes.length);
      assert.equal(first.content_checksum, `sha256:${createHash('sha256').update(bytes).digest('hex')}`);
      assert.equal(first.sanitizer_version, SANITIZER_VERSION);
      assert.deepEqual(checkMarkup(first.markup), { ok: true });
      assert.ok(first.font_families.length >= 1, 'every template names a packaged font first');
    });

    it(`renders ${id}'s markup-like text as text`, () => {
      const data = clone(RICH);
      data.personalInfo.fullName = 'Ada <b onclick="x()">Lovelace</b>';
      const result = materialize({ template_id: id, design: {}, data });
      assert.equal(result.status, 'ok');
      // Two templates print the name in capitals.
      assert.ok(result.markup.toLowerCase().includes('ada &lt;b onclick=&quot;x()&quot;&gt;lovelace&lt;/b&gt;'));
      assert.ok(!/<b[\s>]/i.test(result.markup) && !result.markup.includes('<tags>') && !result.markup.includes('<Engine>'));
    });

    it(`renders ${id} without the six hidden sections`, () => {
      const shown = materialize({ template_id: id, design: clone(DESIGN), data: clone(RICH) });
      const hidden = materialize({ template_id: id, design: clone(DESIGN), data: clone(HIDDEN) });
      assert.equal(hidden.status, 'ok');
      // Some templates print names in capitals or lowercase.
      const shownText = shown.markup.toLowerCase();
      const hiddenText = hidden.markup.toLowerCase();
      for (const [section, marker] of Object.entries(SECTION_MARKERS)) {
        assert.ok(shownText.includes(marker.toLowerCase()), `${section} shows when listed`);
        assert.ok(!hiddenText.includes(marker.toLowerCase()), `${section} is gone when hidden`);
      }
      assert.ok(hiddenText.includes('ada lovelace'));
      for (const section of Object.keys(SECTION_MARKERS)) assert.deepEqual(hidden.data[section], []);
    });
  }

  it('resolves an unknown template to the first one and says so', () => {
    const named = materialize({ template_id: 'modern', design: {}, data: clone(RICH) });
    for (const template_id of ['no-such-template', '', null, '__proto__']) {
      const fallback = materialize({ template_id, design: {}, data: clone(RICH) });
      assert.equal(fallback.template_id, 'modern');
      assert.equal(fallback.template_fallback, true);
      assert.equal(fallback.markup, named.markup);
    }
  });

  it('keeps only the contract paths of the design and renders font ids as their stacks', () => {
    const result = materialize({
      template_id: 'executive',
      design: {
        layout: 'two-column',
        colors: { primary: '#1f3b56', secondary: '#ffffff', accent: null },
        typography: { body: { size: 11, family: 'source-serif-pro', lineHeight: 2 }, heading: { family: 'inter', weight: 900 } },
        spacing: { margin: 20, padding: 4 },
        style: { shadow: 'none' },
        showPhoto: true,
        bulletStyle: 'check',
      },
      data: clone(RICH),
    });
    assert.equal(result.status, 'ok');
    assert.deepEqual(result.design, {
      spacing: { margin: 20 },
      typography: { body: { size: 11, family: 'source-serif-pro' }, heading: { family: 'inter' } },
      colors: { primary: '#1f3b56' },
      bulletStyle: 'check',
    });
    assert.ok(result.markup.includes('font-family:&#x27;Source Serif Pro&#x27;'));
    assert.deepEqual(result.font_families, ['inter', 'source-serif-pro']);
    assert.ok(result.markup.includes('data-bullet-style="check"'));
  });

  it('treats null and absent design values alike', () => {
    const absent = materialize({ template_id: 'modern', design: {}, data: clone(RICH) });
    const nulls = materialize({
      template_id: 'modern',
      design: { colors: { primary: null }, spacing: null, typography: { body: { size: null } }, bulletStyle: null },
      data: clone(RICH),
    });
    assert.equal(nulls.status, 'ok');
    assert.deepEqual(nulls.design, {});
    assert.equal(nulls.markup, absent.markup);
    assert.equal(materialize({ template_id: 'modern', design: null, data: clone(RICH) }).markup, absent.markup);
  });

  it('fills missing sections, drops null optional fields and unknown keys, and keeps the rest', () => {
    const result = materialize({
      template_id: 'modern',
      design: {},
      data: {
        personalInfo: { fullName: 'Grace Hopper', email: null, nickname: 'Amazing Grace' },
        experience: [{ id: 'x', company: 'Navy', position: 'Officer', highlights: [], endDate: null, extra: 1 }],
        awards: ['unused'],
        sectionOrder: ['personal', 'skills', 'experience', 'education', 'projects', 'publications', 'profiles'],
      },
    });
    assert.equal(result.status, 'ok');
    assert.deepEqual(result.data, {
      personalInfo: { fullName: 'Grace Hopper' },
      experience: [{ id: 'x', company: 'Navy', position: 'Officer', highlights: [] }],
      education: [],
      skills: [],
      projects: [],
      publications: [],
      profiles: [],
      sectionOrder: ['personal', 'skills', 'experience', 'education', 'projects', 'publications', 'profiles'],
    });
    assert.deepEqual(materialize({ template_id: 'modern', design: {}, data: null }).data.personalInfo, { fullName: '' });
  });
});

describe('materializer: ineligible inputs', () => {
  const data = () => clone(RICH);
  const cases = [
    ['design_out_of_domain', 'CSS in the accent color', { design: { colors: { primary: 'red;background:url(https://rd02.invalid/a)' } } }],
    ['design_out_of_domain', 'a named color', { design: { colors: { primary: 'red' } } }],
    ['design_out_of_domain', 'a short hex color', { design: { colors: { primary: '#fff' } } }],
    ['design_out_of_domain', 'CSS in a body font family', { design: { typography: { body: { family: "x;background:url('https://rd02.invalid/f')" } } } }],
    ['design_out_of_domain', 'an unlisted heading font', { design: { typography: { heading: { family: 'Comic Sans MS' } } } }],
    ['design_out_of_domain', 'a font stack instead of a font id', { design: { typography: { body: { family: "'Inter', sans-serif" } } } }],
    ['design_out_of_domain', 'a body size under 9', { design: { typography: { body: { size: 8.5 } } } }],
    ['design_out_of_domain', 'a body size over 12', { design: { typography: { body: { size: 12.5 } } } }],
    ['design_out_of_domain', 'a body size as text', { design: { typography: { body: { size: '11' } } } }],
    ['design_out_of_domain', 'a margin over 30', { design: { spacing: { margin: 31 } } }],
    ['design_out_of_domain', 'a negative margin', { design: { spacing: { margin: -1 } } }],
    ['design_out_of_domain', 'a margin as text', { design: { spacing: { margin: '0;background:red' } } }],
    ['design_out_of_domain', 'an unknown bullet', { design: { bulletStyle: 'heart' } }],
    ['design_out_of_domain', 'a design that is a list', { design: [] }],
    ['design_out_of_domain', 'a design that is text', { design: 'modern' }],
    ['design_out_of_domain', 'colors that are text', { design: { colors: 'red' } }],
    ['data_malformed', 'data that is a list', { data: [] }],
    ['data_malformed', 'a section that is not a list', { data: { ...data(), experience: 'Navy' } }],
    ['data_malformed', 'an entry missing its highlights', { data: { ...data(), experience: [{ id: 'x', company: 'Navy', position: 'Officer' }] } }],
    ['data_malformed', 'a highlight that is a number', { data: { ...data(), projects: [{ id: 'p', name: 'n', technologies: [], highlights: [7] }] } }],
    ['data_malformed', 'a GPA that is a number', { data: { ...data(), education: [{ id: 'e', institution: 'MIT', gpa: 3.9 }] } }],
    ['data_malformed', 'personal info missing the name', { data: { ...data(), personalInfo: { email: 'a@example.test' } } }],
    ['data_malformed', 'personal info that is text', { data: { ...data(), personalInfo: 'Ada' } }],
    ['data_malformed', 'an unknown section in the order', { data: { ...data(), sectionOrder: ['personal', '<script>'] } }],
    ['data_malformed', 'hidden sections as text', { data: { ...data(), hiddenSections: 'experience' } }],
    ['data_malformed', 'a null section', { data: { ...data(), skills: null } }],
  ];

  for (const [reason, what, input] of cases) {
    it(`answers ${reason} for ${what}, the same way twice`, () => {
      const request = () => ({ template_id: 'modern', design: clone(DESIGN), data: data(), ...clone(input) });
      const first = materialize(request());
      assert.deepEqual(first, { status: 'ineligible', reason, sanitizer_version: SANITIZER_VERSION });
      assert.deepEqual(materialize(request()), first);
    });
  }

  it('answers data_malformed when a hidden section is malformed only after it is shown', () => {
    const hiddenBad = { ...clone(RICH), experience: 'not a list', hiddenSections: ['experience'] };
    assert.equal(materialize({ template_id: 'modern', design: {}, data: hiddenBad }).status, 'ok');
    const shownBad = { ...clone(RICH), experience: 'not a list' };
    assert.equal(materialize({ template_id: 'modern', design: {}, data: shownBad }).reason, 'data_malformed');
  });

  it('answers data_too_large for markup over 2 MiB, the same way twice', () => {
    const highlights = Array.from({ length: 6000 }, (_, i) => `Highlight ${i} ${'x'.repeat(300)}`);
    const big = { ...clone(RICH), experience: [{ id: 'big', company: 'Big', position: 'Big', highlights }] };
    const first = materialize({ template_id: 'modern', design: {}, data: big });
    assert.deepEqual(first, { status: 'ineligible', reason: 'data_too_large', sanitizer_version: SANITIZER_VERSION });
    assert.deepEqual(materialize({ template_id: 'modern', design: {}, data: big }), first);
  });
});

describe('materializer: output checks', () => {
  const shell = (inner) => wrapStandaloneHtml(`<article data-resume-page="true" style="width:210mm">${inner}</article>`);

  it('accepts a template article in the shell', () => {
    assert.deepEqual(checkMarkup(shell('<div data-page-block="true"><h2>Experience</h2><ul><li>One &amp; two</li></ul></div>')), { ok: true });
    assert.deepEqual(checkMarkup(shell('<a href="https://example.test/x" target="_blank" rel="noreferrer">x</a><a href="mailto:a@example.test">m</a>')), { ok: true });
    assert.deepEqual(checkMarkup(shell('<p>&lt;script&gt;alert(1)&lt;/script&gt; url( @import</p>')), { ok: true });
  });

  const rejected = [
    ['element:script', '<script>alert(1)</script>'],
    ['element:script', '<SCRIPT>alert(1)</SCRIPT>'],
    ['event-handler', '<div onclick="x()">x</div>'],
    ['event-handler', '<span onMouseOver="x()">x</span>'],
    ['css-url', '<div style="background:url(https://rd02.invalid/x)">x</div>'],
    ['css-url', '<div style="background:URL(&quot;https://rd02.invalid/x&quot;)">x</div>'],
    ['css-import', '<style>@import "https://rd02.invalid/x.css";</style>'],
    ['css-url', '<style>/* ok */ div { background: url(x) }</style>'],
    ['css-load', '<div style="background-image:image-set(&quot;x.png&quot; 1x)">x</div>'],
    ['css-escape', '<div style="background:\\75 rl(x)">x</div>'],
    ['css-comment', '<div style="background:u/**/rl(x)">x</div>'],
    ['element:link', '<link rel="stylesheet" href="https://rd02.invalid/x.css">'],
    ['element:img', '<img src="https://rd02.invalid/x.png">'],
    ['element:iframe', '<iframe src="https://rd02.invalid/"></iframe>'],
    ['element:object', '<object data="https://rd02.invalid/x"></object>'],
    ['element:base', '<base href="https://rd02.invalid/">'],
    ['element:embed', '<embed src="https://rd02.invalid/x">'],
    ['element:svg', '<svg><use href="https://rd02.invalid/x#y"></use></svg>'],
    ['element:form', '<form action="https://rd02.invalid/"><button>x</button></form>'],
    ['meta-http-equiv', '<meta http-equiv="refresh" content="0;url=https://rd02.invalid/">'],
    ['href-scheme', '<a href="javascript:alert(1)">x</a>'],
    ['href-scheme', '<a href=" JaVa\tScRiPt:alert(1)">x</a>'],
    ['href-scheme', '<a href="http://example.test/">x</a>'],
    ['href-scheme', '<a href="data:text/html,x">x</a>'],
    ['href-scheme', '<a href="/relative">x</a>'],
    ['attribute:src', '<div src="https://rd02.invalid/x">x</div>'],
    ['attribute:srcset', '<span srcset="x 1x">x</span>'],
    ['attribute:xlink:href', '<span xlink:href="https://rd02.invalid/">x</span>'],
    ['entity', '<a href="javascript&colon;alert(1)">x</a>'],
    ['syntax', '<!-- <script>alert(1)</script> -->'],
    ['syntax', '<div style=unquoted>x</div>'],
    ['syntax', '<style>div{color:red}'],
    // ROUNDS-00A-L08 review: tokenize tags like a browser. Only HTML
    // whitespace [\t\n\f\r ] ends a tag name; a Unicode space (U+00A0,
    // \v, U+FEFF) does not, so a tag using one is unparseable here rather
    // than a shorter element that hides live markup as raw text.
    ['syntax', '<style >a{color:red}</style>'],
    ['syntax', '<div class="x">hidden<img src="https://rd02.invalid/x"></div>'],
    ['syntax', '<div\u000bclass="x">x</div>'],
    ['syntax', '<div﻿class="x">x</div>'],
    // A raw-text element closes only at an appropriate end tag, so a
    // lookalike (</stylex>) does not end it and the CSS after it, up to the
    // real </style>, is still scanned.
    ['css-url', '<style>a{color:red}</stylex>b{background:url(https://rd02.invalid/x)}</style>'],
  ];
  for (const [rule, inner] of rejected) {
    it(`rejects ${inner.slice(0, 48)} (${rule})`, () => {
      assert.deepEqual(checkMarkup(shell(inner)), { ok: false, rule });
    });
  }
});
