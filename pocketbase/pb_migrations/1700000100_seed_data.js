/// <reference path="../pb_data/types.d.ts" />

// Fresh-release data seed. This is the only shared-content data migration:
// it loads the final question libraries and guide cheat sheets into the
// final schema created by 1700000000_init_collections.js.
migrate(
  (db) => {
    const dao = new Dao(db);

    const content = readJson("content.json", true) || {};
    const moreCoding = readJson("more_coding.json", false) || {};
    const moreContent = readJson("more_content.json", false) || {};

    const categoryIdByName = seedCategories(dao, [
      ...(content.behavioral_categories || []),
      ...(moreContent.behavioral_categories || []),
    ]);

    seedRows(dao, "system_design_questions", [
      ...(content.system_design_questions || []),
      ...(moreContent.system_design_questions || []),
    ], (row) => ({ ...row, slug: slugify(row.slug || row.title) }));

    seedRows(dao, "coding_questions", [
      ...(content.coding_questions || []),
      ...(moreCoding.coding_questions || []),
    ], (row) => {
      const next = { ...row, slug: slugify(row.slug || row.title) };
      if (!next.entry || typeof next.entry !== "object") {
        next.entry = inferFunctionEntry(next);
      }
      if (!next.entry) {
        throw new Error("seed_data: missing coding entry for " + next.title);
      }
      return next;
    });

    seedRows(dao, "behavioral_questions", [
      ...(content.behavioral_questions || []),
      ...(moreContent.behavioral_questions || []),
    ], (row) => {
      const { category_names, ...rest } = row;
      return {
        ...rest,
        slug: slugify(row.slug || row.title),
        categories: (category_names || [])
          .map((name) => categoryIdByName[name])
          .filter(Boolean),
      };
    });

    seedGuideRows(dao, "system_design_guides", "system_design_guides.json");
    seedGuideRows(dao, "coding_guides", "coding_guides.json");
    seedGuideRows(dao, "behavioral_guides", "behavioral_guides.json");
  },
  (db) => {
    const dao = new Dao(db);
    for (const name of [
      "behavioral_guides",
      "coding_guides",
      "system_design_guides",
      "behavioral_questions",
      "behavioral_categories",
      "coding_questions",
      "system_design_questions",
    ]) {
      try {
        const records = dao.findRecordsByFilter(name, 'id != ""', "", 100000, 0);
        for (const record of records) dao.deleteRecord(record);
      } catch (_) {
        /* collection missing */
      }
    }
  },
);

function readJson(fileName, required) {
  try {
    const bytes = $os.readFile(`/pb_seeds/${fileName}`);
    return JSON.parse(toString(bytes));
  } catch (e) {
    if (required) throw new Error("seed_data: failed to read " + fileName + ": " + e.message);
    return null;
  }
}

function slugify(s) {
  return (s || "")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "")
    .slice(0, 80);
}

function seedCategories(dao, rows) {
  const collection = dao.findCollectionByNameOrId("behavioral_categories");
  const idByName = {};
  const existing = dao.findRecordsByFilter("behavioral_categories", 'id != ""', "", 10000, 0);
  for (const record of existing) idByName[record.get("name")] = record.id;

  for (const row of rows) {
    if (!row.name) continue;
    const rec = idByName[row.name]
      ? dao.findFirstRecordByData("behavioral_categories", "name", row.name)
      : new Record(collection);
    rec.set("name", row.name);
    rec.set("description", row.description || "");
    rec.set("color", row.color || "");
    rec.set("icon", row.icon || "");
    dao.saveRecord(rec);
    idByName[row.name] = rec.id;
  }

  return idByName;
}

function seedRows(dao, collectionName, rows, normalize) {
  const collection = dao.findCollectionByNameOrId(collectionName);
  const existingBySlug = {};
  const existing = dao.findRecordsByFilter(collectionName, 'id != ""', "", 100000, 0);
  for (const record of existing) existingBySlug[record.get("slug")] = record;

  for (const row of rows) {
    const next = normalize(row);
    if (!next.slug) continue;
    const rec = existingBySlug[next.slug] || new Record(collection);
    for (const [key, value] of Object.entries(next)) {
      if (value === null || value === undefined) continue;
      rec.set(key, value);
    }
    dao.saveRecord(rec);
    existingBySlug[next.slug] = rec;
  }
}

function seedGuideRows(dao, collectionName, fileName) {
  const rows = readJson(fileName, true) || [];
  seedRows(dao, collectionName, rows, (row) => ({ ...row, slug: slugify(row.slug || row.title) }));
}

function inferFunctionEntry(row) {
  const starter = (row.starter_code && row.starter_code.python) || "";
  const match = starter.match(/def\s+(\w+)\s*\(([^)]*)\)/);
  if (!match) return null;
  const name = match[1];
  const paramsRaw = match[2].trim();
  const params = paramsRaw
    ? paramsRaw
        .split(",")
        .map((part) => part.trim())
        .filter((part) => part && part !== "self")
        .map((part) => ({ name: part.split(/[:=]/)[0].trim(), type: "any" }))
    : [];
  return { kind: "function", name, params, returns: "any" };
}
