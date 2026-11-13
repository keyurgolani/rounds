/// <reference path="../pb_data/types.d.ts" />

// Moves each saved AI provider key and model list out of ai_providers, at
// start (ROUNDS-14-L02 stage A, manifest ai-credentials-v1).
//
// For every ai_providers row, in id order, in pages:
//   * a saved key (encrypted_key and key_iv) becomes an ai_credentials row,
//     wrap legacy-v0, holding the pair as it was, and a copy of it for the
//     down step. No key is opened, and PocketBase never holds the root, so
//     the runner rewraps each key as aad-v1 on its first good use. A pair
//     that also sits under another account's provider is suspect-planted
//     on every account that holds it, and never opens.
//   * a first-party kind (anthropic, openai) with a base URL of its own
//     becomes the matching compatible kind, so the address it calls is the
//     one it names; the kinds it changed are kept for the down step.
//   * its cached model list becomes ai_provider_models rows: registry for
//     a first-party kind, user-declared for a compatible one, at most 1,000.
//     Each model an ai_settings row picks for the provider is added as
//     user-declared, so a saved choice keeps working.
//   * then a moved pair's encrypted_key and key_iv are cleared; the columns
//     stay, and so does models_cache. One half of a pair alone was never a
//     key, so it stays as it was.
// No other row changes. The runner reads none of the old columns from this
// release on.
//
// Dry run: with ROUNDS_AI_CREDENTIALS_MOVE=dry-run the migration takes the
// apply's path, writes its report (counts and a checksum, never an id or a
// key) to ROUNDS_AI_CREDENTIALS_MOVE_REPORT, which must be set and outside
// pb_data, and then throws, so PocketBase rolls the transaction back and
// nothing changes. The apply logs the same counts and checksum, so the two
// can be compared (docs/operations.md, "AI provider keys").
//
// down() puts each moved pair back on its provider and each changed kind
// back, then deletes every ai_credentials and ai_provider_models row and
// the journal, so 1700008800's down step can drop the empty collections. A
// key entered after the upgrade has no old pair, so it is gone after a
// rollback and has to be entered again.

const MIGRATION = "1700008820_ai_credentials_move";
// The _params row that keeps the kinds the up step changed.
const PARAM = "1700008820_ai_credentials_move.js";
const MODE_ENV = "ROUNDS_AI_CREDENTIALS_MOVE";
const REPORT_ENV = "ROUNDS_AI_CREDENTIALS_MOVE_REPORT";
const REPORT_KIND = "ai-credentials-move";
const REPORT_VERSION = 1;
const PAGE = 200;
const MODELS_MAX = 1000;
const MODEL_MAX = 256;
const COMPATIBLE = { anthropic: "anthropic-compatible", openai: "openai-compatible" };

// ---------------------------------------------------------------------------
// Decisions, with no PocketBase in them (test_ai_credentials_move.py runs
// them under node)
// ---------------------------------------------------------------------------

const PLAIN = /^[^\x00-\x1f\x7f]+$/;

function modelName(value) {
  return typeof value === "string" && value.length > 0 && value.length <= MODEL_MAX && PLAIN.test(value);
}

// The models a cached list names: strings a model id can be, once each,
// sorted, and at most MODELS_MAX. Anything else in the cache is skipped.
function cachedModels(raw) {
  if (typeof raw !== "string" || raw === "") return [];
  let parsed;
  try {
    parsed = JSON.parse(raw);
  } catch (_) {
    return [];
  }
  if (!Array.isArray(parsed)) return [];
  const seen = {};
  const out = [];
  parsed.forEach((m) => {
    if (modelName(m) && !Object.prototype.hasOwnProperty.call(seen, m)) {
      seen[m] = true;
      out.push(m);
    }
  });
  out.sort();
  return out.slice(0, MODELS_MAX);
}

// What the move does with one provider row. `suspect` says whether its pair
// also sits under another account; `declared` lists the models ai_settings
// rows pick for it.
function decide(row, suspect, declared) {
  const hasPair = row.encrypted_key !== "" && row.key_iv !== "";
  const converts = Object.prototype.hasOwnProperty.call(COMPATIBLE, row.kind) && row.base_url.trim() !== "";
  const kind = converts ? COMPATIBLE[row.kind] : row.kind;
  const verification = Object.prototype.hasOwnProperty.call(COMPATIBLE, kind) ? "registry" : "user-declared";
  const models = cachedModels(row.models_cache).map((m) => ({ model: m, verification }));
  const have = {};
  models.forEach((m) => {
    have[m.model] = true;
  });
  (declared || []).slice().sort().forEach((m) => {
    if (modelName(m) && !have[m] && models.length < MODELS_MAX) {
      have[m] = true;
      models.push({ model: m, verification: "user-declared" });
    }
  });
  return {
    credential: hasPair
      ? {
          wrap: "legacy-v0",
          key_version: 1,
          ciphertext: row.encrypted_key,
          nonce: row.key_iv,
          registered_host: "",
          registered_port: 0,
          status: suspect ? "suspect-planted" : "active",
          legacy_ciphertext: row.encrypted_key,
          legacy_nonce: row.key_iv,
        }
      : null,
    // Only a whole pair moves and clears. One half alone was never a key,
    // and it stays as it was, so the down step has nothing to put back.
    clears: hasPair,
    half: !hasPair && (row.encrypted_key !== "" || row.key_iv !== ""),
    kind: converts ? kind : null,
    models,
  };
}

// The counts a report and the apply's log line carry.
function emptyCounts() {
  return {
    providers: 0,
    keys_moved: 0,
    keys_suspect_planted: 0,
    halves_left: 0,
    kinds_converted: 0,
    providers_with_models: 0,
    models_seeded: 0,
    models_declared: 0,
  };
}

function count(counts, decision) {
  counts.providers += 1;
  if (decision.credential) {
    counts.keys_moved += 1;
    if (decision.credential.status === "suspect-planted") counts.keys_suspect_planted += 1;
  } else if (decision.half) counts.halves_left += 1;
  if (decision.kind) counts.kinds_converted += 1;
  if (decision.models.length > 0) counts.providers_with_models += 1;
  decision.models.forEach((m) => {
    if (m.verification === "user-declared") counts.models_declared += 1;
    else counts.models_seeded += 1;
  });
}

// One link of the checksum chain: the provider and what the move did with
// it, never its key.
function outcomeOf(id, decision) {
  return JSON.stringify([
    id,
    decision.credential ? decision.credential.status : "none",
    decision.clears,
    decision.kind || "",
    decision.models.map((m) => m.model + "|" + m.verification),
  ]);
}

// ---------------------------------------------------------------------------
// The migration
// ---------------------------------------------------------------------------

migrate(
  (db) => {
    const dao = new Dao(db);
    const dryRun = ($os.getenv(MODE_ENV) || "").trim().toLowerCase() === "dry-run";
    const reportPath = ($os.getenv(REPORT_ENV) || "").trim();
    if (dryRun) {
      if (!reportPath) {
        throw new Error(MIGRATION + ": " + MODE_ENV + "=dry-run needs " + REPORT_ENV + " set to a path outside pb_data");
      }
      if (reportPath.indexOf("pb_data") >= 0) {
        throw new Error(MIGRATION + ": refusing to write the dry-run report inside pb_data");
      }
    }
    const logLine = (event, fields) => {
      console.log(JSON.stringify(Object.assign({ v: "obs/v1", event, service: "pocketbase" }, fields)));
    };
    const credentials = dao.findCollectionByNameOrId("ai_credentials");
    const modelRows = dao.findCollectionByNameOrId("ai_provider_models");
    const counts = emptyCounts();
    let chain = $security.sha256(REPORT_KIND + "/" + REPORT_VERSION);
    let step = "suspects";
    try {
      // Pairs held under more than one account.
      const suspects = {};
      const pairs = arrayOf(new DynamicModel({ encrypted_key: "", key_iv: "" }));
      db.newQuery(
        "SELECT encrypted_key, key_iv FROM ai_providers WHERE COALESCE(encrypted_key, '') != '' " +
          "AND COALESCE(key_iv, '') != '' GROUP BY encrypted_key, key_iv HAVING COUNT(DISTINCT user) > 1",
      ).all(pairs);
      pairs.forEach((p) => {
        suspects[p.encrypted_key + "\n" + p.key_iv] = true;
      });

      // The models each ai_settings row picks, by provider.
      step = "settings";
      const declared = {};
      const picks = arrayOf(new DynamicModel({ provider: "", model: "" }));
      db.newQuery(
        "SELECT text_provider AS provider, text_model AS model FROM ai_settings " +
          "WHERE COALESCE(text_provider, '') != '' AND COALESCE(text_model, '') != '' " +
          "UNION SELECT vision_provider AS provider, vision_model AS model FROM ai_settings " +
          "WHERE COALESCE(vision_provider, '') != '' AND COALESCE(vision_model, '') != ''",
      ).all(picks);
      picks.forEach((p) => {
        (declared[p.provider] = declared[p.provider] || []).push(p.model);
      });

      step = "move";
      const converted = [];
      let after = "";
      for (;;) {
        const rows = arrayOf(
          new DynamicModel({ id: "", user: "", kind: "", base_url: "", encrypted_key: "", key_iv: "", models_cache: "" }),
        );
        db.newQuery(
          "SELECT id, COALESCE(user, '') AS user, COALESCE(kind, '') AS kind, COALESCE(base_url, '') AS base_url, " +
            "COALESCE(encrypted_key, '') AS encrypted_key, COALESCE(key_iv, '') AS key_iv, " +
            "COALESCE(CAST(models_cache AS TEXT), '') AS models_cache FROM ai_providers WHERE id > {:after} " +
            "ORDER BY id LIMIT " + PAGE,
        )
          .bind({ after })
          .all(rows);
        if (rows.length === 0) break;
        rows.forEach((row) => {
          const decision = decide(row, Boolean(suspects[row.encrypted_key + "\n" + row.key_iv]), declared[row.id]);
          if (row.user !== "") {
            if (decision.credential) {
              const record = new Record(credentials);
              record.set("user", row.user);
              record.set("provider", row.id);
              Object.keys(decision.credential).forEach((key) => record.set(key, decision.credential[key]));
              dao.saveRecord(record);
            }
            decision.models.forEach((m) => {
              const record = new Record(modelRows);
              record.set("user", row.user);
              record.set("provider", row.id);
              record.set("model", m.model);
              record.set("verification", m.verification);
              dao.saveRecord(record);
            });
          }
          if (decision.kind) {
            converted.push({ provider: row.id, kind: row.kind });
            db.newQuery("UPDATE ai_providers SET kind = {:kind} WHERE id = {:id}").bind({ kind: decision.kind, id: row.id }).execute();
          }
          if (decision.clears) {
            db.newQuery("UPDATE ai_providers SET encrypted_key = '', key_iv = '' WHERE id = {:id}").bind({ id: row.id }).execute();
          }
          count(counts, decision);
          chain = $security.sha256(chain + outcomeOf(row.id, decision));
        });
        after = rows[rows.length - 1].id;
        if (rows.length < PAGE) break;
      }
      if (converted.length > 0) dao.saveParam(PARAM, { migration: MIGRATION, kinds: converted });
    } catch (err) {
      logLine("ai_credentials_move_failed", { step });
      if (dryRun) {
        $os.writeFile(
          reportPath,
          JSON.stringify({ report_kind: REPORT_KIND, report_version: REPORT_VERSION, dry_run: true, status: "failed", step }, null, 2) + "\n",
          0o600,
        );
      }
      throw err;
    }
    const checksum = "sha256:" + chain;
    if (dryRun) {
      $os.writeFile(
        reportPath,
        JSON.stringify(
          { report_kind: REPORT_KIND, report_version: REPORT_VERSION, dry_run: true, status: "ok", counts, checksum },
          null,
          2,
        ) + "\n",
        0o600,
      );
      logLine("ai_credentials_move_dry_run", Object.assign({ checksum }, counts));
      throw new Error(MIGRATION + ": dry run complete; report written to " + reportPath + "; aborting so nothing changes");
    }
    logLine("ai_credentials_moved", Object.assign({ checksum }, counts));
  },

  (db) => {
    // Each moved pair back on its provider, unless that provider holds a
    // key again, which only a client write before the rollback could give it.
    db.newQuery(
      "UPDATE ai_providers SET encrypted_key = (SELECT c.legacy_ciphertext FROM ai_credentials c " +
        "WHERE c.provider = ai_providers.id), key_iv = (SELECT c.legacy_nonce FROM ai_credentials c " +
        "WHERE c.provider = ai_providers.id) WHERE COALESCE(encrypted_key, '') = '' AND EXISTS (SELECT 1 FROM " +
        "ai_credentials c WHERE c.provider = ai_providers.id AND COALESCE(c.legacy_ciphertext, '') != '' " +
        "AND COALESCE(c.legacy_nonce, '') != '')",
    ).execute();
    // Each changed kind back, on a provider that still has the kind it was
    // given.
    const row = new DynamicModel({ value: "" });
    let journal = null;
    try {
      db.newQuery("SELECT CAST(value AS TEXT) AS value FROM _params WHERE key = {:key}").bind({ key: PARAM }).one(row);
      journal = JSON.parse(row.value);
    } catch (_) {
      journal = null;
    }
    if (journal && Array.isArray(journal.kinds)) {
      journal.kinds.forEach((k) => {
        if (!Object.prototype.hasOwnProperty.call(COMPATIBLE, k.kind)) return;
        db.newQuery("UPDATE ai_providers SET kind = {:prior} WHERE id = {:id} AND kind = {:now}")
          .bind({ prior: k.kind, id: k.provider, now: COMPATIBLE[k.kind] })
          .execute();
      });
    }
    db.newQuery("DELETE FROM ai_credentials").execute();
    db.newQuery("DELETE FROM ai_provider_models").execute();
    db.newQuery("DELETE FROM _params WHERE key = {:key}").bind({ key: PARAM }).execute();
    console.log(JSON.stringify({ v: "obs/v1", event: "ai_credentials_move_reversed", service: "pocketbase" }));
  },
);

if (typeof module !== "undefined" && module.exports) {
  module.exports = { decide, cachedModels, emptyCounts, count, outcomeOf, MODELS_MAX };
}
