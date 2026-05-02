/// <reference path="../pb_data/types.d.ts" />

// Public demo account for the hosted instance. It is safe for this
// credential to be documented because the account is intentionally
// reset on logout by the frontend.

const DEMO_EMAIL = "demo@rounds.keyurgolani.name";
const DEMO_PASSWORD = "RoundsDemo123!";

migrate(
  (db) => {
    const dao = new Dao(db);
    const users = dao.findCollectionByNameOrId("users");

    addFieldIfMissing(users, { name: "is_demo", type: "bool" });
    addFieldIfMissing(users, { name: "demo_run_used", type: "bool" });
    addFieldIfMissing(users, { name: "demo_evaluate_used", type: "bool" });
    dao.saveCollection(users);

    let demo = null;
    try {
      demo = dao.findFirstRecordByData("users", "email", DEMO_EMAIL);
    } catch (_) {
      demo = new Record(users);
      demo.set("email", DEMO_EMAIL);
      demo.setPassword(DEMO_PASSWORD);
    }

    demo.set("emailVisibility", true);
    demo.set("username", "rounds-demo");
    demo.set("verified", true);
    demo.set("name", "Rounds Demo");
    demo.set("bio", "Disposable hosted demo account. Changes reset on logout.");
    demo.set("target", "Explore Rounds");
    demo.set("is_demo", true);
    demo.set("demo_run_used", false);
    demo.set("demo_evaluate_used", false);
    dao.saveRecord(demo);
  },
  (db) => {
    const dao = new Dao(db);

    try {
      const demo = dao.findFirstRecordByData("users", "email", DEMO_EMAIL);
      dao.deleteRecord(demo);
    } catch (_) {
      /* demo user missing */
    }

    try {
      const users = dao.findCollectionByNameOrId("users");
      removeFieldIfPresent(users, "is_demo");
      removeFieldIfPresent(users, "demo_run_used");
      removeFieldIfPresent(users, "demo_evaluate_used");
      dao.saveCollection(users);
    } catch (_) {
      /* users collection missing */
    }
  },
);

function hasField(collection, name) {
  const fields = collection.schema.fields() || [];
  return fields.some((f) => f.name === name);
}

function addFieldIfMissing(collection, field) {
  if (!hasField(collection, field.name)) {
    collection.schema.addField(new SchemaField(field));
  }
}

function removeFieldIfPresent(collection, name) {
  if (hasField(collection, name)) {
    collection.schema.removeField(name);
  }
}
