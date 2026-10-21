/// <reference path="../pb_data/types.d.ts" />

// JSON field limits (ROUNDS-00A-L03, decision D10).
//
// PocketBase's own 1702134272_set_default_json_max_size migration sets every
// JSON field's maxSize to 2,000,000 bytes. It sorts after every 1700xxxxxx
// migration here, so on a database built from scratch it overwrites the limit
// each of them declares. This migration sorts right after it and sets each
// JSON field the repository's migrations define back to the size they end on.
// It skips a collection or field the database doesn't have and saves a
// collection only when one of its limits changes, so on a database upgraded
// in place it changes only the fields that don't already hold their size.
// The down step puts PocketBase's 2,000,000-byte default back.
//
// LIMITS stays a literal, sorted list of [collection, field, bytes]. A
// migration that adds a JSON field or changes a maxSize registers it in a new
// NNNNNNNNNN_json_limits_<name>.js copied from this file, with its own LIMITS
// and sorted after this one, so its entries win. This file is never edited:
// PocketBase runs each migration once. scripts/lint_migrations.py and
// pocketbase/tests/test_json_limits.py hold the registry to the migrations,
// and harness phase 12c checks it on fresh and upgraded databases
// (docs/development.md#json-field-limits).
//
// 1048576 is 1 MiB, 2097152 is 2 MiB, 4194304 is 4 MiB, 8388608 is 8 MiB, and
// 16777216 is 16 MiB.
const LIMITS = [
  ["admission_commands", "result", 1048576],
  ["ai_coding_attempts", "ai_chats", 2097152],
  ["ai_coding_attempts", "rubric_review", 2097152],
  ["ai_coding_attempts", "test_results", 2097152],
  ["ai_coding_rounds", "checkpoints", 2097152],
  ["ai_coding_rounds", "companies", 2097152],
  ["ai_coding_rounds", "rubric", 2097152],
  ["ai_coding_rounds", "starter_files", 2097152],
  ["ai_coding_rounds", "topics", 2097152],
  ["ai_providers", "models_cache", 262144],
  ["behavioral_guides", "checklists", 4194304],
  ["behavioral_guides", "resources", 4194304],
  ["behavioral_guides", "sections", 4194304],
  ["behavioral_questions", "common_pitfalls", 2097152],
  ["behavioral_questions", "follow_up_questions", 2097152],
  ["behavioral_questions", "sample_response", 2097152],
  ["behavioral_questions", "star_guide", 2097152],
  ["behavioral_questions", "tags", 2097152],
  ["behavioral_questions", "tips", 2097152],
  ["behavioral_questions", "what_interviewers_look_for", 2097152],
  ["campaigns", "target_companies", 2097152],
  ["coding_guides", "checklists", 4194304],
  ["coding_guides", "resources", 4194304],
  ["coding_guides", "sections", 4194304],
  ["coding_questions", "boilerplate_code", 2097152],
  ["coding_questions", "companies", 2097152],
  ["coding_questions", "constraints", 2097152],
  ["coding_questions", "definition_case_ids", 65536],
  ["coding_questions", "entry", 65536],
  ["coding_questions", "hints", 2097152],
  ["coding_questions", "solutions", 2097152],
  ["coding_questions", "starter_code", 2097152],
  ["coding_questions", "test_cases", 2097152],
  ["coding_questions", "thought_process", 2097152],
  ["coding_questions", "tips", 2097152],
  ["coding_questions", "topics", 2097152],
  ["execution_attempts", "operator_view", 65536],
  ["execution_envelopes", "user_view", 1048576],
  ["execution_jobs", "definition", 1024],
  ["execution_jobs", "input", 8388608],
  ["experience_anecdotes", "tags", 2097152],
  ["experience_bullets", "tags", 2097152],
  ["experience_jobs", "tags", 2097152],
  ["experience_projects", "tags", 2097152],
  ["experience_projects", "tech_stack", 2097152],
  ["interview_rounds", "questions_asked", 2097152],
  ["offers", "trail", 2097152],
  ["relation_quarantine", "payload", 16777216],
  ["relation_quarantine_reports", "findings", 16777216],
  ["relation_quarantine_reports", "outcomes", 16777216],
  ["relation_quarantine_reports", "relations", 16777216],
  ["relation_quarantine_reports", "summary", 16777216],
  ["resume_variants", "ats_breakdown", 2097152],
  ["resume_variants", "data", 2097152],
  ["resume_variants", "links", 2097152],
  ["resume_variants", "role_focus", 2097152],
  ["resume_versions", "data", 2097152],
  ["resume_versions", "links", 2097152],
  ["resumes", "data", 2097152],
  ["resumes", "design", 2097152],
  ["resumes", "links", 2097152],
  ["system_design_guides", "checklists", 4194304],
  ["system_design_guides", "resources", 4194304],
  ["system_design_guides", "sections", 4194304],
  ["system_design_questions", "api_design", 2097152],
  ["system_design_questions", "architecture_diagram", 2097152],
  ["system_design_questions", "constraints", 2097152],
  ["system_design_questions", "database_schema", 2097152],
  ["system_design_questions", "detailed_design", 2097152],
  ["system_design_questions", "estimation", 2097152],
  ["system_design_questions", "high_level_design", 2097152],
  ["system_design_questions", "hints", 2097152],
  ["system_design_questions", "requirements_functional", 2097152],
  ["system_design_questions", "requirements_nonfunctional", 2097152],
  ["system_design_questions", "senior_topics", 2097152],
  ["system_design_questions", "tags", 2097152],
  ["system_design_questions", "thought_process", 2097152],
  ["system_design_questions", "tips", 2097152],
  ["system_design_questions", "trade_offs", 2097152],
  ["system_design_questions", "tradeoff_visual", 2097152],
  ["take_home_assignments", "companies", 2097152],
  ["take_home_assignments", "harness_files", 2097152],
  ["take_home_assignments", "rubric", 2097152],
  ["take_home_assignments", "starter_files", 2097152],
  ["take_home_assignments", "topics", 2097152],
  ["take_home_attempts", "ai_chats", 2097152],
  ["take_home_attempts", "files", 8388608],
  ["take_home_attempts", "harness_output", 2097152],
  ["take_home_attempts", "rubric_review", 2097152],
  ["todos", "mentions", 2097152],
];
const DEFAULT_BYTES = 2000000; // PocketBase's JSON default

// Sets each registered JSON field the database has to size(bytes) and saves
// each collection whose limits changed, once.
function apply(dao, size) {
  const found = {};
  const changed = [];
  for (const entry of LIMITS) {
    const name = entry[0];
    if (!(name in found)) {
      try {
        found[name] = dao.findCollectionByNameOrId(name);
      } catch (_) {
        found[name] = null; // not on this database
      }
    }
    const field = found[name] ? found[name].schema.getFieldByName(entry[1]) : null;
    const bytes = size(entry[2]);
    if (!field || field.type !== "json" || field.options.maxSize === bytes) continue;
    field.options.maxSize = bytes;
    if (changed.indexOf(name) < 0) changed.push(name);
  }
  for (const name of changed) dao.saveCollection(found[name]);
}

migrate(
  (db) => apply(new Dao(db), (bytes) => bytes),
  (db) => apply(new Dao(db), () => DEFAULT_BYTES),
);
