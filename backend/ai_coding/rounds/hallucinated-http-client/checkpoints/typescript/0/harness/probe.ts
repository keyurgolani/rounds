// The candidate's side of checkpoint 0's grade: point client.ts at the
// driver's server, call fetchUser, and print the result as one JSON line.
// It runs as a tsx child of grade.py, with the candidate's project root as
// its working directory and no result channel.
import { config, fetchUser } from '../../client.ts';

(async () => {
  config.baseUrl = process.argv[2];
  const result = await fetchUser(process.argv[3]);
  process.stdout.write('\n' + JSON.stringify(result) + '\n');
})().catch((err) => {
  process.stderr.write(String(err && err.stack ? err.stack : err) + '\n');
  process.exit(1);
});
