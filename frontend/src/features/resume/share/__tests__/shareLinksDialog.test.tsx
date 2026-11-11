// The share links dialog (ROUNDS-00B-L04): a link's secret is shown once,
// in the show-once panel, which copies nothing for you and closes only
// through "I saved this link"; a clipboard failure leaves the link
// selectable; the secret is gone once the panel closes; one key per create
// form and per Rotate click; rows show their state, and only live rows
// can be rotated or revoked; the panel is the dialog, traps focus, and
// gives it back; and a closed gate keeps the earlier dialog.

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
  COPY_FAILED_TEXT,
  REVOKE_CONFIRM_TEXT,
  ROTATE_CONFIRM_TEXT,
  SAVED_LABEL,
  SHOW_ONCE_TEXT,
} from '../ShareLinksDialog';
import { buildCapabilityUrl, capabilityState, expiryDay, type ShareCapability } from '../client';

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

class FakeRunner {
  calls: Call[] = [];
  list: ShareCapability[] = [];
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

  it('keeps the earlier dialog while the gate is closed', async () => {
    gate.value = 'disabled';
    runner.fetch.mockImplementation(async () => json(200, []));
    render(<ShareDialog open onClose={vi.fn()} resumeId={RESUME} />);
    expect(await screen.findByRole('button', { name: /Create share link/ })).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Create link' })).toBeNull();
  });

  it('shows the share links dialog while the gate is open', async () => {
    render(<ShareDialog open onClose={vi.fn()} resumeId={RESUME} />);
    expect(await screen.findByRole('button', { name: 'Create link' })).toBeInTheDocument();
    await act(async () => {});
  });
});

describe('a gate flip', () => {
  it('the earlier dialog refuses a share capability and shows or copies none of it', async () => {
    // The SPA reads the gate as closed, and the runner as open.
    gate.value = 'disabled';
    const user = setupUser();
    runner.fetch.mockImplementation(async (_url: string, init: RequestInit = {}) =>
      (init.method ?? 'GET') === 'GET' ? json(200, []) : json(201, issued('capaaaaaaaaaaa1', TOKEN)),
    );
    render(<ShareDialog open onClose={vi.fn()} resumeId={RESUME} />);
    await user.click(await screen.findByRole('button', { name: /Create share link/ }));
    expect(await screen.findByText(/links can’t be made here right now/)).toBeInTheDocument();
    expect(writeText).not.toHaveBeenCalled();
    expect(document.body.innerHTML).not.toContain(TOKEN.slice(4));
  });

  it('a runner that reads the gate as closed refuses the share links dialog, which shows its own text', async () => {
    const user = setupUser();
    runner.answers.push(() => typed(400, 'invalid_request'));
    openDialog();
    await user.click(await screen.findByRole('button', { name: 'Create link' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('This link can’t be made as set. Reload the page, then try again.');
    expect(screen.queryByLabelText('Share link')).toBeNull();
    expect(document.body.textContent).not.toContain('Server detail');
    expect(writeText).not.toHaveBeenCalled();
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
