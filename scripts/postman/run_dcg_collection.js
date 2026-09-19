#!/usr/bin/env node
// Run a selected DCG collection folder with credentials held only in process memory.
const fs = require('fs');
const path = require('path');
const root = path.resolve(__dirname, '../..');
const newman = require(path.join(root, '.dcg/tools/node_modules/newman'));
const [folder, baseUrl, compatibleId, breakingId] = process.argv.slice(2);
if (!folder || !baseUrl || !process.env.DCG_DEMO_USERNAME || !process.env.DCG_DEMO_PASSWORD) {
  console.error('Folder, base URL, and DCG_DEMO_USERNAME/PASSWORD are required');
  process.exit(2);
}
const collection = JSON.parse(fs.readFileSync(path.join(root, 'postman/dcg-governance-collection.json')));
const environment = JSON.parse(fs.readFileSync(path.join(root, 'postman/dcg-governance-environment.json')));
const values = {dcg_base_url: baseUrl, dcg_username: process.env.DCG_DEMO_USERNAME,
  dcg_password: process.env.DCG_DEMO_PASSWORD,
  compatible_run_id: compatibleId || '', breaking_run_id: breakingId || ''};
for (const v of environment.values) if (Object.hasOwn(values, v.key)) v.value = values[v.key];
newman.run({collection, environment, folder, reporters: 'cli', timeoutRequest: 8000,
  delayRequest: 250, bail: true}, (error, summary) => {
  if (error) {console.error(error.message); process.exit(1);}
  process.exit(summary.run.failures.length ? 1 : 0);
});
