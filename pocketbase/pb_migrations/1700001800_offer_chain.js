/// <reference path="../pb_data/types.d.ts" />

// Promotes `offers` from one-per-application to a chain of rounds.
// Each row is a discrete offer round (verbal, written, counter…).
// When a new round is created, the prior active round flips to
// status='superseded' and the new row links back via previous_offer.
//
// Schema deltas:
//   1. Drop the UNIQUE (user, application) index — multiple offer
//      rounds per application are now expected.
//   2. Replace it with a non-unique index on the same columns to keep
//      list queries fast.
//   3. Add the 'superseded' value to the status select.
//   4. Add `previous_offer` relation (self-link to offers) so the
//      chain has explicit lineage rather than implied order.

migrate(
  (db) => {
    const dao = new Dao(db);
    const offers = dao.findCollectionByNameOrId("offers");

    // 1 + 2: swap the unique index for a plain one.
    offers.indexes = offers.indexes.map((idx) =>
      idx.includes("idx_offers_user_application")
        ? "CREATE INDEX idx_offers_user_application ON offers (user, application)"
        : idx,
    );

    // 3: extend status select.
    const statusField = offers.schema.getFieldByName("status");
    if (statusField && !statusField.options.values.includes("superseded")) {
      statusField.options.values = [
        ...statusField.options.values,
        "superseded",
      ];
    }

    // 4: previous_offer self-relation.
    if (!offers.schema.getFieldByName("previous_offer")) {
      offers.schema.addField(
        new SchemaField({
          name: "previous_offer",
          type: "relation",
          options: {
            collectionId: offers.id,
            cascadeDelete: false,
            maxSelect: 1,
          },
        }),
      );
    }

    dao.saveCollection(offers);
  },
  (db) => {
    const dao = new Dao(db);
    try {
      const offers = dao.findCollectionByNameOrId("offers");

      // Drop the relation column.
      try {
        offers.schema.removeField("previous_offer");
      } catch (_) {
        /* already gone */
      }

      // Strip 'superseded' from the select. Rows with that status will
      // be left with an invalid value; PB tolerates it at read time but
      // saves will fail until the row is updated to a valid value. The
      // rollback path assumes the caller has already drained those.
      const statusField = offers.schema.getFieldByName("status");
      if (statusField) {
        statusField.options.values = statusField.options.values.filter(
          (v) => v !== "superseded",
        );
      }

      // Restore the unique index.
      offers.indexes = offers.indexes.map((idx) =>
        idx.includes("idx_offers_user_application")
          ? "CREATE UNIQUE INDEX idx_offers_user_application ON offers (user, application)"
          : idx,
      );

      dao.saveCollection(offers);
    } catch (_) {
      /* collection dropped */
    }
  },
);
