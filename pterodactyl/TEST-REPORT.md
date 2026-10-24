# Pterodactyl 1.15.2 validation

Validated on October 24, 2026, on Olares 1.12.7-20260908, Linux AMD64. Production candidate: Chart 0.0.16, Panel 1.15.2, Wings 1.13.3.

## Baselines

| Case | Actual source | Panel / PHP before | Result |
| --- | --- | --- | --- |
| A | Formal Market Chart 0.0.14, downloaded from market.olares | 1.15.1 / 8.3.33 | In-place upgrade and complete stop/resume passed |
| B | Supplemental upstream 1.15.0 image using the current packaging harness | 1.15.0 / 8.3.33 | In-place upgrade and complete stop/resume passed |
| C | Empty-data installation of the target | 1.15.2 / 8.3.36 | Fresh initialization, functionality, and complete stop/resume passed |

The market history contains only one distinct Panel application version. B was explicitly approved as a supplemental upstream baseline; it is not a historical market package.

Fixture identity, database/Redis namespace, external ports, and chart-generated random test credentials were isolated. Application source images were not patched. Installed fixture revisions used the next ordinary chart patch when an already-uploaded version could not be replaced. A and C received fixture-only Chart 0.0.17 for the final existing-Wings-configuration guard; the production candidate remains 0.0.16. Fresh initialization was tested before this guard was added; its new branch applies only when an existing configuration file is present. B exercised the final guard during its first upgrade from 1.15.0.

## Verified behavior

- Actual PHP-FPM requests report PHP 8.3.36, UID 1000, and disabled session upload progress. Both older baselines reported PHP 8.3.33 with upload progress enabled.
- Normal password login through the external private entrance, authenticated account lookup, and the admin dashboard passed before upgrade, after upgrade, and after full stop/resume. No database/browser session extraction or fabricated login session was used.
- Original server UUID, owner, allocation, custom location/nest/egg, server settings, inactive schedule/task, backup records, and application encryption key remained intact.
- Eleven business tables were compared by content hashes, excluding normal updated_at timestamps. Server files and backup archives were compared byte-for-byte.
- Server installation, real file writes/reads, normal client power start/stop/restart, authenticated console WSS, published TCP port, and SFTP login/upload/readback passed. Restart assertions used the actual Docker process start time because the Panel statistics endpoint caches responses for 20 seconds.
- Native server backup creation and restoration passed on all three cases. Existing backups remained available after upgrade and after full stop/resume.
- Existing schedules ran real queue jobs that started the original server and completed. They remained inactive afterward, and the server was stopped after each test.
- Complete stop was confirmed by the absence of active application pods. Resumed workloads became ready, original Docker image IDs remained cached, and persisted business data passed again.
- Automatic pre-migration SQL and Panel-file snapshots were validated for both upgrade paths. They include the users/server tables, custom fixture, encryption key, and Wings configuration. Snapshot directory/file modes were 700/600. The snapshots cover Panel state; the unchanged game volumes and native server backups were independently hashed.

## Packaging and configuration checks

- Panel uses the unmodified official v1.15.2 image, mirrored as docker.io/beclab/pterodactyl-panel:v1.15.2. Wings remains the unmodified official v1.13.3 image, mirrored as docker.io/beclab/pterodactyl-wings:v1.13.3.
- AMD64 and ARM64 registry configurations were verified for Panel, Wings, and all auxiliary images. Target Panel reports PHP 8.3.36 on both architectures. Source/mirror config digests match, including ordered uncompressed rootfs digests. Some older/Wings compressed layer digests change during mirror conversion.
- Old image values cannot retain vulnerable Panel images: the application and copy-init images are fixed in the template. Old-values Helm rendering and final chart lint passed.
- Existing matching-node Wings YAML is retained rather than regenerated. Node UUID and credential fields must match before it is reused; mismatched configuration is retained and startup stops. Raw configuration bytes remained identical during both tested Panel upgrades.
- Wings itself expands an implicit Docker network driver into bridge on full startup. Canonical configuration hashes were compared after full stop/resume, normalizing only that equivalent default. Historical canonical hashes came from files whose raw hashes exactly matched the recorded pre-stop checkpoints. The original raw hashes remain in the private evidence.

## Scope and observed limitations

The disposable server was a minimal HTTP process used to exercise Wings lifecycle, console, files, networking, SFTP, and backups. This change does not claim new Minecraft/Terraria/TShock installation or gameplay testing. The test-only runtime image was local to each disposable Docker service and was not published or included in the chart.

Wings needed initial retries while its Docker service initialized, and logged an optional CPU-burst warning. The final workloads and all listed operations passed. Wings remains the same experimental component/version already packaged by the market.

ARM64 image availability and contents were verified; native ARM64 runtime testing was not performed. Teammate test-market smoke testing remains pending. All three disposable applications, their private test data, and their Upload versions were removed; shared middleware was retained.

## Upstream references

- [Panel v1.15.2 security release](https://github.com/pterodactyl/panel/releases/tag/v1.15.2)
- [Official Panel source](https://github.com/pterodactyl/panel)
- [PHP releases](https://www.php.net/)
