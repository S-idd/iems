#!/usr/bin/env node
// Inject one-run credentials in memory; never export a filled environment.
const fs = require('fs');
const path = require('path');
const root = path.resolve(__dirname, '../..');
const newman = require(path.join(root, '.dcg/tools/node_modules/newman'));
const [dcgBase, iemsBase, onlineId, retryId] = process.argv.slice(2);
if (!dcgBase || !iemsBase || !onlineId || !retryId || !process.env.DCG_DEMO_USERNAME ||
    !process.env.DCG_DEMO_PASSWORD || !process.env.IEMS_DCG_WEBHOOK_AUTH) {
  console.error('DCG/IEMS URLs, run IDs and process-memory auth variables are required');
  process.exit(2);
}
const collection = JSON.parse(fs.readFileSync(path.join(root, 'postman/dcg-webhook-collection.json')));
const environment = JSON.parse(fs.readFileSync(path.join(root, 'postman/dcg-webhook-environment.json')));
const values = {dcg_base_url: dcgBase, iems_base_url: iemsBase,
  dcg_username: process.env.DCG_DEMO_USERNAME, dcg_password: process.env.DCG_DEMO_PASSWORD,
  iems_dcg_auth: process.env.IEMS_DCG_WEBHOOK_AUTH, online_run_id: onlineId, retry_run_id: retryId};
for (const entry of environment.values) entry.value = values[entry.key] || '';
newman.run({collection, environment, reporters: 'cli', timeoutRequest: 8000, delayRequest: 150,
  bail: true}, (error, summary) => {
  if (error) {console.error(error.message); process.exit(1);}
  process.exit(summary.run.failures.length ? 1 : 0);
});
