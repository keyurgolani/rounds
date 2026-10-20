/// <reference path="../pb_data/types.d.ts" />

// Expand step for server-owned definitions (ROUNDS-00A-L02).
//
// The compiled definitions in backend/definitions/ are the source of
// truth for what executes and how it scores. This migration records, on
// each presentation row, which definition version it corresponds to, so
// step 2 can resolve a request's (track, slug, variant, version) against
// the manifest. At this step the runner still reads the legacy PocketBase
// path (ROUNDS_GATE_EXECUTION_DEFINITIONS=legacy), so the new columns are
// written and not yet read; the resolver, never a column, is the
// authority on whether a version exists.
//
// It is additive and non-destructive:
//   * a new server-only collection, definition_migration_journal, with a
//     row per touched presentation row recording its mapping;
//   * definition_version (number) on coding_questions, ai_coding_rounds,
//     and take_home_assignments, plus definition_case_ids (json) on
//     coding_questions (the case ids its compiled test definition holds);
//   * every presentation row stays, so drafts and attempts survive.
//
// Mapping by slug (backend/definitions/manifest.json; the committed
// touched-row manifest pocketbase/migration-manifests/
// 1700006200_definitions_expand.json records the expected disposition):
//   * the coding questions the manifest compiles (ACTIVE_CODING) and
//     hallucinated-http-client (ACTIVE_AI_CODING) -> active, version 1;
//   * the 5 removed AI-coding samples and the 3 removed take-home
//     assignments, present only on a pre-2026-05-16 database, -> retired,
//     version 1 (their definitions are retired, payload-free for the
//     AI-coding ones), so a request gets definition_retired, not a run;
//   * any other slug, such as a question an admin added, has no
//     definition, so its row is left unversioned, journaled
//     definition-not-found, and the resolver answers definition_not_found
//     at step 2.
//
// down() removes only the columns and the journal collection it added. It
// deletes no presentation, draft, or attempt row, so it is a safe revert;
// account isolation and user content are untouched.

// The removed samples whose sources are gone (build.py SOURCELESS_AI_CODING)
// and the removed take-home assignments (build.py RETIRED_TAKE_HOME). Only
// a pre-2026-05-16 database still has rows for these.
const RETIRED_AI_CODING = ["async-bugs-py", "cart-bugfix-py", "log-parser-ts", "rate-limiter-ts", "word-count-py"];
const RETIRED_TAKE_HOME = ["csv-summarize-py", "event-bus-ts", "kv-store-py"];
// The slugs with an active version 1 in the manifest: every seeded coding
// question and the one AI-coding round with sources.
const ACTIVE_CODING = [
  "3sum", "add-two-numbers", "alien-dictionary", "amazon-locker-distance-multi-source-bfs",
  "amazon-locker-package-fit", "amazon-lottery-weighted-random-selection", "balanced-binary-tree",
  "battleship-game-model", "best-time-to-buy-and-sell-stock", "best-time-to-buy-and-sell-stock-ii",
  "best-time-to-buy-and-sell-stock-with-cooldown", "best-time-to-buy-and-sell-stock-with-transaction-fee",
  "binary-search", "binary-tree-inorder-traversal", "binary-tree-level-order-traversal",
  "binary-tree-maximum-path-sum", "binary-tree-path-sum-ii", "binary-tree-right-side-view",
  "binary-tree-zigzag-level-order-traversal", "book-index-generator", "burst-balloons", "candy-distribution",
  "change-machine-coin-inventory", "cheapest-flights-within-k-stops", "check-permutation",
  "chess-model-move-validation", "city-traffic-max-edge-load-during-event", "climbing-stairs", "clone-graph",
  "coffee-shop-order-system", "coin-change-ii", "coin-change-minimum-coins-for-amount", "combination-sum",
  "construct-binary-tree-from-preorder-and-inorder-traversal", "container-with-most-water",
  "contains-duplicate", "count-negatives-in-a-sorted-matrix", "count-palindrome-pairs-among-substrings",
  "counting-bits", "course-schedule", "course-schedule-ii", "daily-temperatures",
  "date-map-floor-key-lookup", "deck-of-cards", "decode-string", "decode-ways", "diameter-of-binary-tree",
  "dice-rolling-simulator-statistics", "discount-prices-in-a-sentence", "distinct-subsequences",
  "edit-distance", "encode-and-decode-strings", "escape-maze-with-one-wall-removal",
  "evaluate-reverse-polish-notation", "falling-water-trapping-rain-water", "filesystem-search-api",
  "find-all-anagrams-in-a-string", "find-median-from-data-stream", "find-minimum-in-rotated-sorted-array",
  "find-the-duplicate-number", "first-missing-positive", "first-unique-character-in-stream",
  "foldable-binary-tree", "gas-station", "generate-parentheses", "graph-valid-tree", "group-anagrams",
  "group-isomorphic-words", "hamming-distance-between-dna-strands", "hand-of-straights", "happy-number",
  "house-robber", "house-robber-ii", "implement-trie-prefix-tree", "insert-interval",
  "intcode-program-alarm", "interleaving-string", "invert-binary-tree", "is-unique", "isbn-10-verifier",
  "jump-game", "jump-game-ii", "k-closest-points-to-origin", "kmp-pattern-search",
  "knight-minimum-moves-on-chessboard", "koko-eating-bananas", "kth-largest-element-in-an-array",
  "kth-smallest-element-in-a-bst", "largest-24-hour-time-from-digits", "largest-rectangle-in-histogram",
  "leaderboard-system", "letter-combinations-of-a-phone-number", "lfu-cache", "linked-list-cycle",
  "linked-list-cycle-ii", "longest-common-subsequence", "longest-consecutive-sequence",
  "longest-increasing-path-in-a-matrix", "longest-increasing-subsequence", "longest-palindromic-substring",
  "longest-substring-without-repeating-characters", "look-and-say-sequence-membership",
  "lowest-common-ancestor-of-a-binary-tree", "lowest-common-ancestor-of-a-bst", "lru-cache",
  "max-area-of-island", "max-concurrent-tasks-from-server-log", "maximum-depth-of-binary-tree",
  "maximum-product-subarray", "maximum-profitable-windows", "maximum-root-to-leaf-path-sum",
  "maximum-subarray", "median-of-two-sorted-arrays", "merge-intervals", "merge-k-sorted-lists",
  "merge-overlapping-intervals", "merge-sorted-notification-lists", "merge-two-sorted-lists",
  "merging-k-sorted-data-streams-streaming", "micro-service-availability-alarm", "min-cost-climbing-stairs",
  "min-stack", "minimum-meeting-rooms", "minimum-number-of-arrows-to-burst-balloons",
  "minimum-window-substring", "missing-number", "modal-widget-component-domain-model",
  "most-common-3-page-sequence-in-web-log", "move-zeroes", "multiply-strings", "nearest-caf-finder",
  "network-delay-time", "non-overlapping-intervals", "number-of-1-bits",
  "number-of-connected-components-in-an-undirected-graph", "number-of-islands",
  "number-pad-texting-t9-word-lookup", "org-chart-total-reports", "pacific-atlantic-water-flow",
  "package-manager-install-order", "palindrome-linked-list", "palindromic-substrings", "pangram-detector",
  "parking-lot-management-system", "partition-equal-subset-sum", "partition-labels", "permutations",
  "plus-one", "pow-x-n", "product-of-array-except-self", "product-recommendation-distance",
  "recently-listened-tracks-widget", "redundant-connection", "regular-expression-matching",
  "remove-duplicates-from-sorted-array", "remove-nth-node-from-end-of-list", "reorder-list", "reverse-bits",
  "reverse-integer", "reverse-linked-list", "reverse-nodes-in-k-group", "rna-transcription",
  "robot-duel-board-game", "rocket-equation-fuel-sum", "rocket-equation-fuel-sum-with-fuel-mass",
  "rotate-image", "rotting-oranges", "same-tree", "search-a-2d-matrix", "search-in-rotated-sorted-array",
  "serialize-and-deserialize-binary-tree", "set-matrix-zeroes", "set-with-expiry",
  "shortest-path-between-profiles", "single-number", "sliding-window-maximum", "smallest-k-numbers",
  "sort-colors", "sorting-iterators-k-way-merge", "speeding-cars-in-city-grid", "spell-checker-trie-based",
  "spiral-matrix", "spreadsheet-cells-formulas-cycles", "stack-from-scratch",
  "stock-buy-sell-best-pair-of-days", "stock-span", "string-to-integer-atoi", "stringify-looped-graph",
  "subarray-sum-equals-k", "subsets", "subtree-of-another-tree", "sum-of-two-integers", "surrounded-regions",
  "symmetric-tree", "target-sum", "task-scheduler", "team-vacation-overlap-risk-periods",
  "text-editor-model-composable-elements", "time-based-key-value-store", "top-k-frequent-elements",
  "traffic-intersection-crossings", "tree-to-first-child-next-sibling-events", "trie-prefix-word-count",
  "two-sum", "two-sum-ii-input-array-is-sorted", "unique-linked-list-values", "unique-paths",
  "unix-find-command-composable-matchers", "urlify", "valid-anagram", "valid-palindrome",
  "valid-parentheses", "valid-sudoku", "validate-binary-search-tree", "vending-machine", "walls-and-gates",
  "weighted-matrix-minimum-cost-path", "wildcard-matching", "winnable-path",
  "word-break-sentence-reconstruction", "word-ladder", "word-search", "word-search-ii",
  "zeitgeist-top-n-most-popular-items", "zigzag-string-conversion",
];
const ACTIVE_AI_CODING = [
  "hallucinated-http-client",
];
const JOURNAL = "definition_migration_journal";
const MIGRATION = "1700006200_definitions_expand";

migrate(
  (db) => {
    const dao = new Dao(db);

    // Resolve every presentation collection before writing anything, so a
    // missing one fails the whole migration and changes nothing.
    const coding = dao.findCollectionByNameOrId("coding_questions");
    const aiRounds = dao.findCollectionByNameOrId("ai_coding_rounds");
    const takeHome = dao.findCollectionByNameOrId("take_home_assignments");

    // 1) The server-only journal. Every client rule is null, so only a
    //    superuser (this migration) ever reads or writes it.
    const journal = new Collection({
      name: "definition_migration_journal",
      type: "base",
      listRule: null,
      viewRule: null,
      createRule: null,
      updateRule: null,
      deleteRule: null,
      schema: [
        { name: "migration", type: "text", required: true },
        { name: "collection", type: "text", required: true },
        { name: "record", type: "text", required: true },
        { name: "slug", type: "text" },
        { name: "definition_track", type: "text" },
        { name: "definition_version", type: "number" },
        { name: "disposition", type: "text", required: true },
      ],
      indexes: [
        `CREATE INDEX idx_def_journal_migration ON ${JOURNAL} (migration)`,
      ],
    });
    dao.saveCollection(journal);

    // 2) The new presentation columns.
    const numberField = (name) => new SchemaField({ name, type: "number" });
    coding.schema.addField(numberField("definition_version"));
    coding.schema.addField(new SchemaField({ name: "definition_case_ids", type: "json", options: { maxSize: 64 * 1024 } }));
    dao.saveCollection(coding);
    aiRounds.schema.addField(numberField("definition_version"));
    dao.saveCollection(aiRounds);
    takeHome.schema.addField(numberField("definition_version"));
    dao.saveCollection(takeHome);

    const record = (collection, row, track, version, disposition, caseIds) => {
      if (version !== null) row.set("definition_version", version);
      if (caseIds !== null) row.set("definition_case_ids", caseIds);
      dao.saveRecord(row);
      const entry = new Record(journal, {
        migration: MIGRATION,
        collection: collection,
        record: row.id,
        slug: row.getString("slug"),
        definition_track: track,
        definition_version: version === null ? 0 : version,
        disposition: disposition,
      });
      dao.saveRecord(entry);
    };

    // 3) Map each presentation row. find*ByFilter with an always-true
    //    filter lists every row; nothing is deleted or recreated.
    for (const row of dao.findRecordsByFilter("coding_questions", "id != ''")) {
      if (ACTIVE_CODING.indexOf(row.getString("slug")) === -1) {
        record("coding_questions", row, "coding", null, "definition-not-found", null);
        continue;
      }
      // A json field reads back as raw bytes, so take its text with
      // getString and parse it. The case ids are c000.. over the stored
      // object cases, matching build.py's compiled test definition.
      let cases;
      try {
        cases = JSON.parse(row.getString("test_cases"));
      } catch (_) {
        cases = [];
      }
      const ids = [];
      if (Array.isArray(cases)) {
        for (let i = 0; i < cases.length; i += 1) {
          if (cases[i] && typeof cases[i] === "object") ids.push("c" + String(ids.length).padStart(3, "0"));
        }
      }
      record("coding_questions", row, "coding", 1, "active", ids);
    }
    for (const row of dao.findRecordsByFilter("ai_coding_rounds", "id != ''")) {
      const slug = row.getString("slug");
      if (RETIRED_AI_CODING.indexOf(slug) !== -1) record("ai_coding_rounds", row, "ai-coding", 1, "retired", null);
      else if (ACTIVE_AI_CODING.indexOf(slug) !== -1) record("ai_coding_rounds", row, "ai-coding", 1, "active", null);
      else record("ai_coding_rounds", row, "ai-coding", null, "definition-not-found", null);
    }
    for (const row of dao.findRecordsByFilter("take_home_assignments", "id != ''")) {
      const slug = row.getString("slug");
      const retired = RETIRED_TAKE_HOME.indexOf(slug) !== -1;
      // No active take-home definition exists at step 1; a non-retired
      // assignment is left unversioned and resolves to not-found.
      record("take_home_assignments", row, "take-home", retired ? 1 : null, retired ? "retired" : "definition-not-found", null);
    }
  },
  (db) => {
    const dao = new Dao(db);
    // Forward-safe revert: drop only the added columns and the journal
    // collection. No presentation, draft, or attempt row is touched.
    for (const [name, fields] of [
      ["coding_questions", ["definition_version", "definition_case_ids"]],
      ["ai_coding_rounds", ["definition_version"]],
      ["take_home_assignments", ["definition_version"]],
    ]) {
      const collection = dao.findCollectionByNameOrId(name);
      for (const field of fields) {
        if (collection.schema.getFieldByName(field)) collection.schema.removeField(collection.schema.getFieldByName(field).id);
      }
      dao.saveCollection(collection);
    }
    dao.deleteCollection(dao.findCollectionByNameOrId(JOURNAL));
  }
);
