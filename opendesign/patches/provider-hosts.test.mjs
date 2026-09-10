import assert from 'node:assert/strict';
import { test } from 'node:test';
import { validateUserProviderBaseUrl, validateBaseUrlResolved, assertExternalAssetUrl } from '/app/apps/daemon/dist/connectionTest.js';

const privateDns = async () => [{ address: '192.168.50.138', family: 4 }];
test('user provider domains and private literals work without a preset hostname', async () => {
  for (const url of ['https://4824d8d8.olarestest001.olares.com/v1', 'https://another.example/v1', 'http://10.0.0.8:8080/v1', 'http://[fd00::8]:8080/v1']) {
    const result = await validateUserProviderBaseUrl(url, privateDns);
    assert.equal(result.error, undefined, url);
    assert.ok(result.parsed, url);
  }
});
test('provider URL still requires HTTP or HTTPS', async () => {
  for (const url of ['not-a-url', 'file:///etc/passwd', 'ftp://example.com']) {
    assert.ok((await validateUserProviderBaseUrl(url, privateDns)).error, url);
  }
});
test('allowance does not leak to other URLs or upstream assets', async () => {
  await validateUserProviderBaseUrl('https://another.example/v1', privateDns);
  assert.ok((await validateBaseUrlResolved('https://another.example/file', privateDns)).error);
  assert.equal((await assertExternalAssetUrl('https://another.example/file', privateDns)).ok, false);
  assert.equal((await assertExternalAssetUrl('http://169.254.169.254/latest/meta-data', privateDns)).ok, false);
});
