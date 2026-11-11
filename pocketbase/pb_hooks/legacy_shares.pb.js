/// <reference path="../pb_data/types.d.ts" />

// pocketbase legacy-share-receipt [--out PATH] [--scan] [--commit SHA]: the
// receipt an operator signs (python -m app.legacy_receipt sign) for the
// older share links' migration (ROUNDS-00B-L06 stage 1). legacy_shares.js
// reads its arguments; PocketBase reads its own flags (--dir and the rest)
// before this runs.
$app.rootCmd.addCommand(
  new Command({
    use: "legacy-share-receipt",
    short: "Print the receipt for the older share links' migration journal",
    disableFlagParsing: true,
    run: (cmd, args) => require(`${__hooks}/legacy_shares.js`).receiptCommand(args),
  }),
);
