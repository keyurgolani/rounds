// The materializer bundle's entry (ROUNDS-00A-L04). build.mjs bundles this,
// the core, React 18.3.1, and the frontend's templates, types, utils, and
// export shell into dist/materialize.mjs, and the server hashes that one
// file into materializer_digest, which is the template version: a change to
// any of them changes the digest.
//
// react-dom/server.browser is the same renderToStaticMarkup as the Node
// build, without the Node stream modules an ESM bundle can't require.

import { createElement } from 'react';
import { renderToStaticMarkup } from 'react-dom/server.browser';

import { TEMPLATES } from '../../../frontend/src/features/resume/templates/registry';
import { emptyResumeData } from '../../../frontend/src/features/resume/types';
import { wrapStandaloneHtml } from '../../../frontend/src/features/resume/export/shell';
import { checkMarkup, createMaterializer, fontFamilies, SANITIZER_VERSION } from './core.mjs';

export { checkMarkup, fontFamilies, SANITIZER_VERSION, wrapStandaloneHtml };

export const TEMPLATE_IDS = Object.freeze(TEMPLATES.map((t) => t.id));

export const materialize = createMaterializer({
  createElement,
  renderToStaticMarkup,
  templates: TEMPLATES,
  wrapStandaloneHtml,
  emptyResumeData,
});
