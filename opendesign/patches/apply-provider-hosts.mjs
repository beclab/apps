import { readFileSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';

const root = process.argv[2] || '/app';
function replaceOnce(file, before, after) {
  const path = join(root, file);
  const source = readFileSync(path, 'utf8');
  if (source.split(before).length !== 2) throw new Error(`Upstream patch context changed: ${file}`);
  writeFileSync(path, source.replace(before, after));
}

replaceOnce('apps/daemon/src/connectionTest.ts',
`  return validateBaseUrlResolved(baseUrl, lookup, {
    allowedInternalHosts: configuredAllowedInternalHosts(),
  });`,
`  // Olares: the user explicitly chose this provider endpoint. Trust its exact
  // hostname for this request only; never mutate the process-wide allowlist.
  // Asset URLs still use the strict validateBaseUrlResolved path below.
  const allowedInternalHosts = configuredAllowedInternalHosts();
  try {
    const provider = new URL(baseUrl);
    if (provider.protocol === 'http:' || provider.protocol === 'https:') {
      allowedInternalHosts.push(provider.hostname.toLowerCase());
    }
  } catch {
    // Preserve upstream validation and its error message for malformed URLs.
  }
  return validateBaseUrlResolved(baseUrl, lookup, { allowedInternalHosts });`);

// Handoff summaries also use the user-configured provider endpoint.
replaceOnce('apps/daemon/src/server.ts',
  '  validateBaseUrlResolved,', '  validateUserProviderBaseUrl,');
replaceOnce('apps/daemon/src/server.ts',
  'const validateExternalApiBaseUrl = (baseUrl) => validateBaseUrlResolved(baseUrl);',
  'const validateExternalApiBaseUrl = (baseUrl) => validateUserProviderBaseUrl(baseUrl);');
console.log('Applied Olares request-scoped provider hostname support');
