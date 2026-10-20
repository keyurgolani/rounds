// Signup gating for hosted instances.
//
// The SIGNUPS gate hides the signup flow in the SPA. `ROUNDS_GATE_SIGNUPS`
// wins when set; otherwise `VITE_DISABLE_SIGNUPS=true` still disables it.
// PocketBase enforces the same gate (or `ROUNDS_DISABLE_SIGNUPS=true`)
// through a server-side hook, so hosted instances should set the gate
// once in `.env` or the `rounds-gates` ConfigMap.

import { gateValue } from '../lib/gates';

export const signupConfig = {
  disabled: gateValue('SIGNUPS') === 'disabled',
};
