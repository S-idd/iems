#!/usr/bin/env node
// Run the existing IEMS collection with the demo password only in process memory.
const fs = require('fs');
const path = require('path');
const root = path.resolve(__dirname, '../..');
const newman = require(path.join(root, '.dcg/tools/node_modules/newman'));
const baseUrl = process.argv[2];
if (!baseUrl || !process.env.IEMS_DEMO_ADMIN_PASSWORD) {
  console.error('Base URL and IEMS_DEMO_ADMIN_PASSWORD are required');
  process.exit(2);
}
const collection = JSON.parse(fs.readFileSync(path.join(root, 'postman/iems-api-collection.json')));
const environment = JSON.parse(fs.readFileSync(path.join(root, 'postman/iems-demo.postman_environment.json')));
for (const value of environment.values) {
  if (value.key === 'baseUrl') value.value = baseUrl;
  if (value.key === 'adminPassword') value.value = process.env.IEMS_DEMO_ADMIN_PASSWORD;
}
newman.run({collection, environment, reporters: 'cli', timeoutRequest: 10000,
  delayRequest: 100, bail: true}, (error, summary) => {
  if (error) { console.error(error.message); process.exit(1); }
  const stats = summary.run.stats;
  const result = {collection: 'postman/iems-api-collection.json',
    requests: stats.requests.total, assertions: stats.assertions.total,
    failures: summary.run.failures.length};
  console.log('IEMS_INTEGRATED_SUMMARY=' + JSON.stringify(result));
  process.exit(result.failures ? 1 : 0);
});
