// The share links dialog (ROUNDS-00B-L04): a link's secret is shown once,
// in the show-once panel, which copies nothing for you and closes only
// through "I saved this link"; a clipboard failure leaves the link
// selectable; the secret is gone once the panel closes; one key per create
// form and per Rotate click; rows show their state, and only live rows
// can be rotated or revoked; the panel is the dialog, traps focus, and
// gives it back; and with the gate closed one line replaces the create.
//
// Older links (ROUNDS-00B-L06): only this resume's, each saying why it's
// off; "Get a new link" only where one can be made, one key per press,
// into the show-once panel; a resume that can't be shared says why until
// the dialog closes; a server not ready says "yet"; and nothing in the
// section opens, copies, or deletes a link.

import { act, render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

vi.mock('../../../../lib/pocketbase', () => ({
  pb: { authStore: { token: 'account-token-placeholder', isValid: true, record: null } },
}));

const gate = { value: 'enabled' };
vi.mock('../../../../lib/gates', () => ({
  gateValue: (name: string) => (name === 'SHARE_CAPABILITY_RESOLUTION' ? gate.value : 'enabled'),
}));

import { UUID_V7_PATTERN } from '../../../../lib/idempotency';
import ShareDialog from '../ShareDialog';
import ShareLinksDialog, {
  ALREADY_ISSUED_TEXT,
  ALREADY_REPLACED_TEXT,
  COPY_FAILED_TEXT,
  OLDER_INTRO_OFF_TEXT,
  OLDER_INTRO_TEXT,
  REPLACE_LATER_TEXT,
  REVOKE_CONFIRM_TEXT,
  ROTATE_CONFIRM_TEXT,
  SAVED_LABEL,
  SHARING_OFF_TEXT,
  SHOW_ONCE_TEXT,
} from '../ShareLinksDialog';
import {
  buildCapabilityUrl,
  capabilityState,
  expiryDay,
  olderLinkState,
  type OlderLink,
  type ShareCapability,
} from '../client';

const RESUME = 'resumeaaaaaaaa1';
const TOKEN = 'sd1_AbCdEfGhIjKlMnOpQrStUv';
const NEW_TOKEN = 'sd1_ZyXwVuTsRqPoNmLkJiHgFe';
const DAY = 86_400_000;

function pbDate(ms: number): string {
  return new Date(ms).toISOString().replace('T', ' ');
}

function row(id: string, over: Partial<ShareCapability> = {}): ShareCapability {
  return {
    id,
    status: 'active',
    revoked_reason: '',
    purpose: 'Ada’s resume',
    expires_at: pbDate(Date.now() + 30 * DAY),
    created: pbDate(Date.now() - DAY),
    revoked_at: '',
    capability_version: 1,
    password_set: false,
    ...over,
  };
}

function issued(id: string, token: string | null, version = 1) {
  const body: Record<string, unknown> = {
    capability_id: id,
    scope: { target_kind: 'legacy_artifact_snapshot', resume_id: RESUME, projection_version: 1 },
    state: 'active',
    expires_at: pbDate(Date.now() + 90 * DAY),
    capability_version: version,
    secret_delivery: token ? 'issued' : 'already-issued',
  };
  if (token) body.token = token;
  return body;
}

type Call = { url: string; method: string; body: unknown; key: string | null };

function older(id: string, over: Partial<OlderLink> = {}): OlderLink {
  return {
    id,
    status: 'migrated',
    reason: 'eligible',
    created: pbDate(Date.UTC(2024, 0, 2, 10)),
    turned_off_at: pbDate(Date.UTC(2026, 10, 11, 12)),
    replaced_by: '',
    replaced_at: '',
    target: 'resume',
    resume_id: RESUME,
    variant_id: '',
    root_resume_id: RESUME,
    variant_name: '',
    ...over,
  };
}

class FakeRunner {
  calls: Call[] = [];
  list: ShareCapability[] = [];
  older: OlderLink[] = [];
  // Answers for the older links' list, in turn; then `older`.
  olderAnswers: Array<() => Response> = [];
  answers: Array<(call: Call) => Response> = [];

  fetch = vi.fn(async (url: string, init: RequestInit = {}) => {
    const headers = new Headers(init.headers);
    const call: Call = {
      url,
      method: init.method ?? 'GET',
      body: init.body ? JSON.parse(init.body as string) : undefined,
      key: headers.get('Idempotency-Key'),
    };
    this.calls.push(call);
    if (call.method === 'GET' && url === '/api/share/capabilities') return json(200, this.list);
    if (call.method === 'GET' && url === '/api/share') {
      const next = this.olderAnswers.shift();
      return next ? next() : json(200, { legacy: this.older });
    }
    const next = this.answers.shift();
    if (!next) throw new Error(`no answer for ${call.method} ${url}`);
    return next(call);
  });

  writes(): Call[] {
    return this.calls.filter((c) => c.method === 'POST');
  }
}

function json(status: number, body: unknown, headers: Record<string, string> = {}) {
  return new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json', ...headers } });
}

function typed(status: number, code: string) {
  return json(status, { detail: 'Server detail that is never shown', code, correlation_id: '0'.repeat(32) });
}

let runner: FakeRunner;
let writeText: ReturnType<typeof vi.fn>;

beforeEach(() => {
  gate.value = 'enabled';
  runner = new FakeRunner();
  vi.stubGlobal('fetch', runner.fetch);
  writeText = vi.fn().mockResolvedValue(undefined);
});

// user-event puts its own clipboard on navigator at setup; this one counts
// every write.
function setupUser() {
  const user = userEvent.setup();
  Object.defineProperty(navigator, 'clipboard', { value: { writeText }, configurable: true });
  return user;
}

afterEach(() => {
  vi.unstubAllGlobals();
});

function openDialog(onClose = vi.fn()) {
  const view = render(<ShareLinksDialog open onClose={onClose} resumeId={RESUME} />);
  return { ...view, onClose };
}

async function makeLink(user: ReturnType<typeof setupUser>) {
  await user.click(screen.getByRole('button', { name: 'Create link' }));
  return (await screen.findByLabelText('Share link')) as HTMLInputElement;
}

describe('the show-once panel', () => {
  it('shows a new link once, copies nothing by itself, and leaves only through "I saved this link"', async () => {
    const user = setupUser();
    runner.answers.push(() => json(201, issued('capnew000000001', TOKEN)));
    const { container, onClose } = openDialog();
    const field = await makeLink(user);

    expect(field.value).toBe(`${window.location.origin}/r#${TOKEN}`);
    expect(field.readOnly).toBe(true);
    expect(screen.getByText(SHOW_ONCE_TEXT)).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'Copy your link' })).toBeInTheDocument();
    expect(writeText).not.toHaveBeenCalled();
    // No other way out: no close button, and neither Escape nor the backdrop closes it.
    expect(screen.queryByRole('button', { name: 'Close' })).toBeNull();
    await user.keyboard('{Escape}');
    await user.click(container.querySelector('[aria-hidden="true"]') as HTMLElement);
    expect(onClose).not.toHaveBeenCalled();
    expect(screen.getByLabelText('Share link')).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: 'Copy link' }));
    expect(writeText).toHaveBeenCalledWith(`${window.location.origin}/r#${TOKEN}`);
    expect(screen.getByText('Copied.')).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: SAVED_LABEL }));
    expect(screen.queryByLabelText('Share link')).toBeNull();
    expect(document.body.innerHTML).not.toContain(TOKEN);
    expect(screen.getByRole('heading', { name: 'Share links' })).toBeInTheDocument();
  });

  it('keeps the link selectable when the clipboard fails', async () => {
    const user = setupUser();
    writeText.mockRejectedValue(new Error('denied'));
    runner.answers.push(() => json(201, issued('capnew000000001', TOKEN)));
    openDialog();
    const field = await makeLink(user);
    await user.click(screen.getByRole('button', { name: 'Copy link' }));
    expect(await screen.findByText(COPY_FAILED_TEXT)).toBeInTheDocument();
    expect(field).toHaveFocus();
    expect([field.selectionStart, field.selectionEnd]).toEqual([0, field.value.length]);
  });

  it('drops the secret when the dialog closes', async () => {
    const user = setupUser();
    runner.answers.push(() => json(201, issued('capnew000000001', TOKEN)));
    const { rerender } = openDialog();
    await makeLink(user);
    rerender(<ShareLinksDialog open={false} onClose={vi.fn()} resumeId={RESUME} />);
    expect(document.body.innerHTML).not.toContain(TOKEN);
    rerender(<ShareLinksDialog open onClose={vi.fn()} resumeId={RESUME} />);
    expect(document.body.innerHTML).not.toContain(TOKEN);
    expect(screen.getByRole('button', { name: 'Create link' })).toBeInTheDocument();
  });
});

describe('the create form', () => {
  it('sends the chosen expiry under one key and no password unless asked', async () => {
    const user = setupUser();
    runner.answers.push(() => json(201, issued('capnew000000001', TOKEN)));
    openDialog();
    await user.selectOptions(screen.getByLabelText('Expires'), '30');
    await makeLink(user);
    const [create] = runner.writes();
    expect(create.url).toBe('/api/share');
    expect(create.body).toEqual({ resume_id: RESUME, expires_at: expiryDay(30) });
    expect(create.key).toMatch(UUID_V7_PATTERN);
  });

  it('retries the same form under the same key, and takes a fresh key after an edit', async () => {
    const user = setupUser();
    runner.answers.push(() => typed(503, 'shares_unavailable'), () => typed(503, 'shares_unavailable'),
      () => typed(503, 'shares_unavailable'));
    openDialog();
    const create = screen.getByRole('button', { name: 'Create link' });
    await user.click(create);
    expect(await screen.findByRole('alert')).toHaveTextContent('Links can’t be made right now. Try again shortly.');
    await user.click(create);
    await waitFor(() => expect(runner.writes()).toHaveLength(2));
    await user.selectOptions(screen.getByLabelText('Expires'), '7');
    await user.click(create);
    await waitFor(() => expect(runner.writes()).toHaveLength(3));
    const [first, retry, edited] = runner.writes();
    expect(retry.key).toBe(first.key);
    expect(edited.key).not.toBe(first.key);
    // Never the server's text.
    expect(document.body.textContent).not.toContain('Server detail');
  });

  it('mints a new key after the source changed under the first one', async () => {
    const user = setupUser();
    runner.answers.push(() => typed(409, 'snapshot_conflict'), () => json(201, issued('capnew000000001', TOKEN)));
    openDialog();
    await user.click(screen.getByRole('button', { name: 'Create link' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('This resume changed');
    await makeLink(user);
    const [first, again] = runner.writes();
    expect(again.key).not.toBe(first.key);
  });

  it('asks for 8 to 128 characters and sends the password only in the body', async () => {
    const user = setupUser();
    runner.answers.push(() => json(201, issued('capnew000000001', TOKEN)));
    openDialog();
    await user.click(screen.getByLabelText('Require a password'));
    const field = screen.getByLabelText('Password') as HTMLInputElement;
    expect(field.type).toBe('password');
    await user.type(field, 'short');
    await user.click(screen.getByRole('button', { name: 'Create link' }));
    expect(screen.getByRole('alert')).toHaveTextContent('Use 8 to 128 characters for the password.');
    expect(runner.writes()).toHaveLength(0);
    await user.type(field, ' enough now');
    await makeLink(user);
    const [create] = runner.writes();
    expect(create.body).toEqual({ resume_id: RESUME, expires_at: expiryDay(90), password: 'short enough now' });
    expect(create.url).not.toContain('short');
    expect(screen.getByText('Send the password separately from the link.')).toBeInTheDocument();
  });

  it('offers Rotate when the link was already made, and shows the new one once', async () => {
    const user = setupUser();
    runner.answers.push(
      () => json(200, issued('capnew000000001', null, 1)),
      () => json(200, { ...issued('capnew000000001', NEW_TOKEN, 2), scope: undefined }),
    );
    openDialog();
    await user.click(screen.getByRole('button', { name: 'Create link' }));
    expect(await screen.findByText(ALREADY_ISSUED_TEXT)).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'Rotate' }));
    const field = (await screen.findByLabelText('Share link')) as HTMLInputElement;
    expect(field.value).toBe(`${window.location.origin}/r#${NEW_TOKEN}`);
    expect(screen.getByRole('heading', { name: 'Copy your new link' })).toBeInTheDocument();
    const rotate = runner.writes()[1];
    expect(rotate.url).toBe('/api/share/capabilities/capnew000000001/rotate');
    expect(rotate.body).toEqual({ expected_capability_version: 1 });
  });

  it.each([
    ['demo_account', 'The demo account can’t share links.'],
    ['data_too_large', 'This resume is too large to share.'],
    ['markup_unsafe', 'This resume can’t be shared right now.'],
  ])('says why a %s resume can’t be shared, inline', async (reason, text) => {
    const user = setupUser();
    runner.answers.push(() => json(200, { status: 'ineligible', reason }));
    openDialog();
    await user.click(screen.getByRole('button', { name: 'Create link' }));
    expect(await screen.findByRole('alert')).toHaveTextContent(text);
    expect(screen.queryByLabelText('Share link')).toBeNull();
  });
});

describe('the list', () => {
  function rows() {
    return [
      row('capliveaaaaaaa1', { password_set: true, purpose: 'Live link' }),
      row('capexpiredaaaa1', { expires_at: pbDate(Date.now() - DAY), purpose: 'Old link' }),
      row('caprevokedaaaa1', {
        status: 'revoked', revoked_reason: 'owner', revoked_at: pbDate(Date.now() - DAY), purpose: 'Revoked link',
      }),
      row('capdeletedaaaa1', { status: 'revoked', revoked_reason: 'source_deleted', purpose: 'Deleted source' }),
    ];
  }

  function item(name: string): HTMLElement {
    return screen.getByText(name).closest('li') as HTMLElement;
  }

  it('shows each row’s state, and offers Rotate and Revoke for live rows alone', async () => {
    runner.list = rows();
    openDialog();
    await screen.findByText('Live link');
    expect(within(item('Live link')).getByText(/^Expires /)).toBeInTheDocument();
    expect(within(item('Live link')).getByText('Password')).toBeInTheDocument();
    expect(within(item('Old link')).getByText('Expired')).toBeInTheDocument();
    expect(within(item('Revoked link')).getByText(/^Revoked [A-Z]/)).toBeInTheDocument();
    expect(within(item('Deleted source')).getByText('Source deleted')).toBeInTheDocument();
    expect(within(item('Live link')).getByRole('button', { name: 'Rotate' })).toBeInTheDocument();
    expect(within(item('Live link')).getByRole('button', { name: 'Revoke' })).toBeInTheDocument();
    for (const name of ['Old link', 'Revoked link', 'Deleted source']) {
      expect(within(item(name)).queryByRole('button')).toBeNull();
    }
    // No row shows a link, a copy, or an open action.
    expect(screen.queryByText(/\/r#/)).toBeNull();
    expect(screen.queryByRole('link')).toBeNull();
  });

  it('rotates after a confirm, one key per click, and shows the new link once', async () => {
    const user = setupUser();
    runner.list = [row('capliveaaaaaaa1', { capability_version: 3, password_set: true, purpose: 'Live link' })];
    runner.answers.push(() => json(200, { ...issued('capliveaaaaaaa1', NEW_TOKEN, 4), scope: undefined }));
    openDialog();
    await user.click(await within(await screen.findByRole('list')).findByRole('button', { name: 'Rotate' }));
    expect(screen.getByText(ROTATE_CONFIRM_TEXT)).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'Rotate link' }));
    const field = (await screen.findByLabelText('Share link')) as HTMLInputElement;
    expect(field.value).toBe(`${window.location.origin}/r#${NEW_TOKEN}`);
    expect(screen.getByText('The password stays the same.')).toBeInTheDocument();
    const [rotate] = runner.writes();
    expect(rotate.body).toEqual({ expected_capability_version: 3 });
    expect(rotate.key).toMatch(UUID_V7_PATTERN);
  });

  it.each([
    ['capability_version_conflict', 'This link changed since the list loaded.'],
    ['capability_revoked', 'This link was revoked.'],
    ['capability_expired', 'This link has expired.'],
  ])('answers a %s rotation in the row and reloads the list', async (code, text) => {
    const user = setupUser();
    runner.list = [row('capliveaaaaaaa1', { purpose: 'Live link' })];
    runner.answers.push(() => typed(409, code));
    openDialog();
    await user.click(await within(await screen.findByRole('list')).findByRole('button', { name: 'Rotate' }));
    await user.click(screen.getByRole('button', { name: 'Rotate link' }));
    expect(await screen.findByRole('alert')).toHaveTextContent(text);
    const lists = runner.calls.filter((c) => c.method === 'GET');
    await waitFor(() => expect(runner.calls.filter((c) => c.method === 'GET').length).toBeGreaterThan(1));
    expect(lists.length).toBeGreaterThanOrEqual(1);
  });

  it('revokes after a confirm and reloads the list', async () => {
    const user = setupUser();
    runner.list = [row('capliveaaaaaaa1', { purpose: 'Live link' })];
    runner.answers.push(() => {
      runner.list = [row('capliveaaaaaaa1', { purpose: 'Live link', status: 'revoked', revoked_reason: 'owner',
        revoked_at: pbDate(Date.now()) })];
      return json(200, runner.list[0]);
    });
    openDialog();
    await user.click(await within(await screen.findByRole('list')).findByRole('button', { name: 'Revoke' }));
    expect(screen.getByText(REVOKE_CONFIRM_TEXT)).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'Revoke link' }));
    expect(await within(item('Live link')).findByText(/^Revoked [A-Z]/)).toBeInTheDocument();
    expect(runner.writes()[0].url).toBe('/api/share/capabilities/capliveaaaaaaa1/revoke');
  });

  it('says when there are no links yet', async () => {
    openDialog();
    expect(await screen.findByText(/No links yet/)).toBeInTheDocument();
  });
});

describe('the dialog', () => {
  it('is the panel, named by its heading, traps focus, and gives it back', async () => {
    const user = setupUser();
    const outside = document.createElement('button');
    outside.textContent = 'Share';
    document.body.appendChild(outside);
    outside.focus();
    const onClose = vi.fn();
    const view = render(<ShareLinksDialog open onClose={onClose} resumeId={RESUME} />);
    const dialog = screen.getByRole('dialog');
    expect(dialog).toHaveAttribute('aria-modal', 'true');
    expect(dialog).toHaveAccessibleName('Share links');
    await waitFor(() => expect(screen.getByLabelText('Expires')).toHaveFocus());
    await screen.findByText(/No links yet/);
    // Shift+Tab from the first control wraps to the last, Tab wraps back.
    screen.getByRole('button', { name: 'Close' }).focus();
    await user.tab({ shift: true });
    expect(dialog.contains(document.activeElement)).toBe(true);
    await user.keyboard('{Escape}');
    expect(onClose).toHaveBeenCalledTimes(1);
    view.unmount();
    expect(outside).toHaveFocus();
    outside.remove();
  });

  it('says sharing is off and offers no create while the gate is closed', async () => {
    gate.value = 'disabled';
    render(<ShareDialog open onClose={vi.fn()} resumeId={RESUME} />);
    expect(screen.getByText(SHARING_OFF_TEXT)).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Create link' })).toBeNull();
    expect(screen.queryByLabelText('Expires')).toBeNull();
    await waitFor(() => expect(screen.getByRole('button', { name: 'Close' })).toHaveFocus());
    expect(await screen.findByText('No links yet.')).toBeInTheDocument();
    expect(runner.writes()).toEqual([]);
  });

  it('shows the share links dialog while the gate is open', async () => {
    render(<ShareDialog open onClose={vi.fn()} resumeId={RESUME} />);
    expect(await screen.findByRole('button', { name: 'Create link' })).toBeInTheDocument();
    await act(async () => {});
  });
});

describe('a gate flip', () => {
  it('a runner that reads the gate as closed refuses the create, and the dialog says sharing is off', async () => {
    const user = setupUser();
    runner.answers.push(() => typed(503, 'route_disabled'));
    openDialog();
    await user.click(await screen.findByRole('button', { name: 'Create link' }));
    expect(await screen.findByRole('alert')).toHaveTextContent(SHARING_OFF_TEXT);
    expect(screen.queryByLabelText('Share link')).toBeNull();
    expect(document.body.textContent).not.toContain('Server detail');
    expect(writeText).not.toHaveBeenCalled();
  });
});

describe('older links', () => {
  const OTHER_RESUME = 'resumebbbbbbbb1';

  function rows(): OlderLink[] {
    return [
      older('lnkturnedoffaa1'),
      older('lnkdemoaaaaaaa1', { status: 'revoked_demo', reason: 'demo_account' }),
      older('lnkunverified01', { status: 'revoked_unverified', reason: 'token_format' }),
      older('lnkreplacedaaa1', { replaced_by: 'capnew000000009', replaced_at: pbDate(Date.UTC(2026, 10, 12, 9)) }),
      older('lnkvariantaaaa1', {
        target: 'variant', resume_id: '', variant_id: 'variantaaaaaaa1', variant_name: 'For Acme',
      }),
      older('lnkotherresume1', { resume_id: OTHER_RESUME, root_resume_id: OTHER_RESUME }),
    ];
  }

  async function section(): Promise<HTMLElement> {
    return (await screen.findByRole('heading', { name: 'Older links' })).closest('section') as HTMLElement;
  }

  function row(name: RegExp): HTMLElement {
    return screen.getByRole('listitem', { name });
  }

  it('lists only this resume’s older links, each named by what it shared and why it’s off', async () => {
    runner.older = rows();
    openDialog();
    const area = await section();
    expect(within(area).getByText(OLDER_INTRO_TEXT)).toBeInTheDocument();
    expect(within(area).getAllByRole('listitem')).toHaveLength(5);
    expect(row(/^This resume Turned off on [A-Z][a-z]{2} \d{1,2}, \d{4}$/)).toBeInTheDocument();
    expect(row(/^This resume Turned off: demo account$/)).toBeInTheDocument();
    expect(row(/^This resume Turned off: couldn’t verify$/)).toBeInTheDocument();
    expect(row(/^This resume Replaced on [A-Z][a-z]{2} \d{1,2}, \d{4}$/)).toBeInTheDocument();
    expect(row(/^For Acme Turned off on /)).toBeInTheDocument();
    expect(within(row(/^This resume Turned off on /)).getByText(/^Created [A-Z][a-z]{2} \d{1,2}, 2024$/)).toBeInTheDocument();
  });

  it('offers Get a new link only where one can be made, and nothing that opens, copies, or deletes a link', async () => {
    runner.older = rows();
    openDialog();
    const area = await section();
    for (const name of [/^This resume Turned off on /, /^For Acme Turned off on /]) {
      expect(within(row(name)).getByRole('button', { name: 'Get a new link' })).toBeInTheDocument();
    }
    for (const name of [/Turned off: demo account$/, /Turned off: couldn’t verify$/, /Replaced on /]) {
      expect(within(row(name)).queryByRole('button')).toBeNull();
    }
    expect(within(area).getAllByRole('button').map((b) => b.textContent)).toEqual(['Get a new link', 'Get a new link']);
    expect(within(area).queryByRole('link')).toBeNull();
    expect(area.textContent).not.toMatch(/\/r\/|Copy|Open|Delete/);
  });

  it('shows no section when this resume has no older links', async () => {
    runner.older = [older('lnkotherresume1', { resume_id: OTHER_RESUME, root_resume_id: OTHER_RESUME })];
    openDialog();
    await screen.findByText(/No links yet/);
    await waitFor(() => expect(runner.calls.some((c) => c.url === '/api/share')).toBe(true));
    expect(screen.queryByRole('heading', { name: 'Older links' })).toBeNull();
  });

  it('gets a new link under a fresh key per press, shows it once with focus on it, and reads Replaced after', async () => {
    const user = setupUser();
    runner.older = [older('lnkturnedoffaa1')];
    runner.answers.push(() => {
      runner.older = [older('lnkturnedoffaa1', { replaced_by: 'capnew000000001', replaced_at: pbDate(Date.now()) })];
      return json(201, issued('capnew000000001', TOKEN));
    });
    openDialog();
    await section();
    await user.click(within(row(/^This resume Turned off on /)).getByRole('button', { name: 'Get a new link' }));
    const field = (await screen.findByLabelText('Share link')) as HTMLInputElement;
    expect(field.value).toBe(`${window.location.origin}/r#${TOKEN}`);
    await waitFor(() => expect(field).toHaveFocus());
    expect(screen.getByRole('heading', { name: 'Copy your new link' })).toBeInTheDocument();
    expect(screen.getByText(SHOW_ONCE_TEXT)).toBeInTheDocument();
    const [press] = runner.writes();
    expect(press.url).toBe('/api/share');
    expect(press.body).toEqual({ legacy_link_id: 'lnkturnedoffaa1' });
    expect(press.key).toMatch(UUID_V7_PATTERN);

    await user.click(screen.getByRole('button', { name: SAVED_LABEL }));
    expect(await screen.findByRole('listitem', { name: /^This resume Replaced on / })).toBeInTheDocument();
    expect(within(await section()).queryByRole('button')).toBeNull();
    expect(document.body.innerHTML).not.toContain(TOKEN);
  });

  it('a press after the link already has its new one points to Your links, under a new key', async () => {
    const user = setupUser();
    runner.older = [older('lnkturnedoffaa1')];
    runner.answers.push(() => typed(503, 'shares_unavailable'), () => json(200, issued('capnew000000001', null)));
    openDialog();
    await section();
    const press = () => user.click(within(row(/^This resume /)).getByRole('button', { name: 'Get a new link' }));
    await press();
    expect(await within(row(/^This resume /)).findByRole('alert')).toHaveTextContent(REPLACE_LATER_TEXT);
    await press();
    expect(await within(row(/^This resume /)).findByRole('status')).toHaveTextContent(ALREADY_REPLACED_TEXT);
    const [first, second] = runner.writes();
    expect(second.key).not.toBe(first.key);
    expect(screen.queryByLabelText('Share link')).toBeNull();
  });

  it('says why this resume can’t get a new link, and keeps saying it until the dialog closes', async () => {
    const user = setupUser();
    runner.older = [older('lnkturnedoffaa1')];
    runner.answers.push(() => json(200, { status: 'ineligible', reason: 'data_too_large' }));
    const { unmount } = openDialog();
    await section();
    await user.click(within(row(/^This resume /)).getByRole('button', { name: 'Get a new link' }));
    const alert = await within(row(/^This resume /)).findByRole('alert');
    expect(alert).toHaveTextContent('Can’t create a new link. This resume is too large to share. Shorten it, then try again.');
    expect(within(row(/^This resume /)).queryByRole('button')).toBeNull();
    // The lists reload after the press; the reason stays.
    await waitFor(() => expect(runner.calls.filter((c) => c.url === '/api/share' && c.method === 'GET').length).toBe(2));
    expect(within(row(/^This resume /)).getByRole('alert')).toHaveTextContent('too large to share');
    unmount();
    openDialog();
    await section();
    expect(within(row(/^This resume /)).getByRole('button', { name: 'Get a new link' })).toBeInTheDocument();
    expect(screen.queryByText(/too large to share/)).toBeNull();
  });

  it.each([
    ['route_disabled', () => typed(503, 'route_disabled')],
    ['materializer_unavailable', () => typed(503, 'materializer_unavailable')],
    ['shares_unavailable', () => typed(503, 'shares_unavailable')],
    ['a 5xx', () => json(502, { detail: 'Server detail that is never shown' })],
  ])('says a new link can’t be made yet on %s, and leaves the press', async (_name, answer) => {
    const user = setupUser();
    runner.older = [older('lnkturnedoffaa1')];
    runner.answers.push(answer);
    openDialog();
    await section();
    await user.click(within(row(/^This resume /)).getByRole('button', { name: 'Get a new link' }));
    expect(await within(row(/^This resume /)).findByRole('alert')).toHaveTextContent(REPLACE_LATER_TEXT);
    expect(within(row(/^This resume /)).getByRole('button', { name: 'Get a new link' })).toBeEnabled();
    expect(document.body.textContent).not.toContain('Server detail');
  });

  it('offers no Get a new link while sharing is off', async () => {
    gate.value = 'disabled';
    runner.older = rows();
    openDialog();
    const area = await section();
    expect(within(area).getByText(OLDER_INTRO_OFF_TEXT)).toBeInTheDocument();
    expect(within(area).queryByRole('button')).toBeNull();
    expect(row(/^This resume Turned off on /)).toBeInTheDocument();
  });

  it('says when older links can’t be loaded, and tries again', async () => {
    const user = setupUser();
    runner.older = [older('lnkturnedoffaa1')];
    runner.olderAnswers.push(() => typed(503, 'shares_unavailable'));
    openDialog();
    const area = await section();
    expect(within(area).getByRole('alert')).toHaveTextContent('Your older links can’t be loaded right now.');
    await user.click(within(area).getByRole('button', { name: 'Try again' }));
    expect(await screen.findByRole('listitem', { name: /^This resume Turned off on / })).toBeInTheDocument();
  });

  it('reads each state from the listed fields', () => {
    expect(olderLinkState(older('a')).kind).toBe('turned-off');
    expect(olderLinkState(older('a', { status: 'revoked_demo' })).kind).toBe('demo');
    expect(olderLinkState(older('a', { status: 'revoked_unverified' })).kind).toBe('unverified');
    expect(olderLinkState(older('a', { replaced_by: 'capnew000000001' })).kind).toBe('replaced');
    expect(olderLinkState(older('a', { turned_off_at: 'soon' }))).toEqual({ kind: 'turned-off', at: null });
  });
});

describe('the helpers', () => {
  it('puts the secret in the fragment', () => {
    expect(buildCapabilityUrl(TOKEN)).toBe(`${window.location.origin}/r#${TOKEN}`);
  });

  it('names a day in UTC', () => {
    expect(expiryDay(30, Date.UTC(2026, 10, 11, 23, 30))).toBe('2026-12-11');
  });

  it('reads every state from the owner fields', () => {
    const now = Date.now();
    expect(capabilityState(row('a'), now).kind).toBe('expires');
    expect(capabilityState(row('a', { expires_at: pbDate(now) }), now).kind).toBe('expired');
    expect(capabilityState(row('a', { expires_at: 'soon' }), now).kind).toBe('expired');
    expect(capabilityState(row('a', { status: 'revoked', revoked_reason: 'owner' }), now).kind).toBe('revoked');
    expect(capabilityState(row('a', { status: 'revoked', revoked_reason: 'source_deleted' }), now).kind).toBe(
      'source-deleted',
    );
  });
});
