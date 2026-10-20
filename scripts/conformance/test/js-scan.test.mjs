import assert from 'node:assert/strict';
import { describe, it } from 'node:test';
import { migrateBodies, objectProperties, readJsxOpeningElement, tokenize } from '../lib/js-scan.mjs';
import { validate } from '../lib/json-schema.mjs';

describe('js-scan', () => {
  it('tokenizes strings, templates, comments, and regex literals', () => {
    const src = 'const a = "x // not a comment"; // comment\nconst r = /[:=]"/g; const t = `a ${b} c`; const d = 4 / 2;';
    const tokens = tokenize(src);
    assert.deepEqual(tokens.filter((t) => t.type === 'string').map((t) => t.value), ['x // not a comment']);
    assert.deepEqual(tokens.filter((t) => t.type === 'regex').map((t) => t.value), ['/[:=]"/g']);
    assert.equal(tokens.find((t) => t.type === 'template').hasExpressions, true);
    assert.equal(tokens.filter((t) => t.value === '/').length, 1);
    assert.equal(tokens.find((t) => t.value === 'r').line, 2);
  });

  it('splits migrate(up, down) and reads top-level object properties only', () => {
    const src = 'migrate((db) => { new Collection({ name: "a", schema: [{ name: "inner" }] }); }, (db) => { new Collection({ name: "b" }); });';
    const tokens = tokenize(src);
    const { up, down } = migrateBodies(tokens);
    const upNames = [];
    for (let i = up[0]; i < up[1]; i++) {
      if (tokens[i].value === 'Collection' && tokens[i + 2]?.value === '{') {
        const props = objectProperties(tokens, i + 2);
        upNames.push(tokens[props.get('name').valueStart].value);
      }
    }
    assert.deepEqual(upNames, ['a']);
    assert.ok(down[0] > up[1]);
  });

  it('reads literal JSX attributes past nested elements and JSX text with apostrophes', () => {
    const src = `<AppHeader
      eyebrow={<span title="inner">Don't <b>stop</b> {x > 1 ? <i /> : null}</span>}
      title="It's here"
      description={\`static\`}
      meta={\`dynamic \${y}\`}
      flag
      {...rest}
    />`;
    const el = readJsxOpeningElement(src, 0);
    assert.equal(el.name, 'AppHeader');
    assert.equal(el.selfClosing, true);
    const attrs = Object.fromEntries(el.attributes.map((a) => [a.name, [a.kind, a.literal]]));
    assert.deepEqual(attrs, {
      eyebrow: ['expression', null],
      title: ['string', "It's here"],
      description: ['string', 'static'],
      meta: ['expression', null],
      flag: ['none', null],
    });
  });

  it('validates the schema subset and refuses unknown keywords', () => {
    const schema = { type: 'object', required: ['a'], properties: { a: { type: 'string', pattern: '^x' } }, additionalProperties: false };
    assert.deepEqual(validate({ a: 'xy' }, schema), []);
    assert.deepEqual(validate({ a: 'y', b: 1 }, schema).map((e) => e.keyword).sort(), ['additionalProperties', 'pattern']);
    assert.deepEqual(validate({}, schema).map((e) => [e.keyword, e.property]), [['required', 'a']]);
    assert.throws(() => validate({}, { format: 'uri' }), /not supported/);
  });
});
