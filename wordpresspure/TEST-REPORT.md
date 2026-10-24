# WordPress PHP 安全升级：测试报告

日期：2026-10-24。候选 Chart 1.1.26 / WordPress 7.1.3。测试系统 Olares 1.12.7-20260908，AMD64。

| 测试路径 | 实测 PHP 变化 | 当前结果 |
| --- | --- | --- |
| 正式市场 Chart 1.1.25 / WordPress 6.4.2 → 7.1.3 | 8.2.14 → 8.3.36 | 原地升级、完整停止恢复、数据及文件校验通过 |
| 补充上游 7.1.2 → 7.1.3（非历史市场包） | 8.3.35 → 8.3.36 | 原地升级、完整停止恢复、数据及文件校验通过 |
| 空数据新装 7.1.3 | 8.3.36 | 初始化、正常登录、内容与附件、代码及可视化编辑、完整停止恢复与数据校验全部通过 |

所有目标实例的实际 Apache PHP 请求均验证为 PHP 8.3.36、UID 1000、session.upload_progress.enabled=0。使用官方 wordpress:7.1.3-php8.3-apache 镜像，无自建 WordPress/PHP 镜像。AMD64/ARM64 的主镜像及辅助镜像架构已核对；没有宣称原生 ARM64 运行测试。

升级验证覆盖原账户、文章、页面、分类、标签、评论、图片附件、插件、子主题、站点设置、持久配置文件和原文件哈希。自动文件/数据库快照通过完整性检查，权限为私有 700/600。旧配置原文保留，数据库使用原生升级流程。旧 Data→Cache 迁移标记得到保留，不重放已完成的迁移。

真实原记录 ID 和附件字节在升级及完整恢复后均通过验证。WordPress 正常登录可能重算旧密码哈希；原密码正常登录已经确认。编辑器探测产生的自动草稿属于测试写入，完整恢复校验另外建立了测试写入完成后的独立检查点。

最终候选保留正式市场 Deployment 的不可变标签。已安装测试别名不能覆盖相同 Upload 版本，因此 A 的修复重试使用测试 Chart 1.1.27/1.1.28；正式候选仍只从 1.1.25 增加至 1.1.26。新装分支在新增保护前已验证；新增根目录恢复范围保护针对已有保存文件，另在旧站点上实测。

保存目录中的未知根文件不会被自动复制到公开网站根目录；原文件仍保留。约定公开根文件可访问。HTTP/2 实测：未知保存文件和内部快照路径返回 404，wp-config.php 及运行时旧配置副本返回 403。原业务数据在最终运行时完整停止恢复后再次通过。

## 已定位的测试环境差异

同一已知路径通过 Apache、应用内代理及外部 HTTP/2 返回正确结果，而测试机外部 HTTP/1.1 入口可能返回 500。这个现象在旧版和新版均出现。没有把该入口问题记作本次 PHP 升级失败，也没有把 HTTP/1.1 失败记作通过；逐层对比证据保存在 transport-matrix.json。

内置浏览器已完成真实密码登录、代码编辑器保存草稿及重新打开；其正文 blob 画布存在渲染差异。用户随后在普通浏览器退出代码模式，确认可视化编辑与草稿保存/刷新正常（2026-10-24 人工确认）。新装实例随后完成完整停止恢复，原账户、文章、页面、评论、分类标签、附件字节、插件主题、配置及数据库检查点全部通过。

三组测试均通过后卸载本次专用实例和数据，并删除全部本次 Upload 版本；共享中间件保留。尚未进行同事冒烟及原生 ARM64 运行验证。提交目标为测试市场草稿 PR。

## HTTP/1.1 follow-up diagnosis (2026-10-24)

Dedicated synthetic-response tests identified the system L4 gateway HTML buffering limit. L4 access logs report `response_payload_too_large`. Plain text of the same size passes; uncompressed HTML of approximately 32 KiB or larger fails over HTTP/1.1 even with explicit Content-Length, while HTTP/2 passes. The gateway injects a language meta tag into HTML. System source sets the TLS listener buffer limit to 32768 and buffers HTML in its Lua filter. This is not a PHP exception or a general chunked-transfer failure. Compressed HTML succeeds in the observed path; it is only a temporary mitigation. A system gateway change is required and was not applied to the live test machine.

[System source](https://github.com/beclab/Olares/blob/main/framework/l4-bfl-proxy/internal/xds/translator/translator.go) · [Envoy flow-control documentation](https://www.envoyproxy.io/docs/envoy/latest/faq/configuration/flow_control). The dedicated diagnostic application and Upload record were cleaned; shared services were retained.

## Application proxy gzip mitigation (2026-10-24)

The OpenResty proxy now explicitly enables negotiated HTML gzip (level 5, minimum 1024 bytes, proxied responses allowed) with Vary: Accept-Encoding. HTML is the default compressed MIME type; binary attachments and REST content types are not newly added. Already encoded upstream responses are passed through without double compression. Explicit identity and gzip;q=0 requests are respected.

The proxy ConfigMap is split into templates/proxy-config.yaml and its rendered checksum is included in the proxy Pod template. A real baseline-to-modified fixture upgrade automatically replaced the proxy Pod; existing saved site configuration, login, draft content and image bytes were preserved. Candidate Chart remains 1.1.26; the dedicated test upgrade used fixture 1.1.26 to 1.1.27 only.

The 18-case matrix covered HTTP/1.1 and HTTP/2, identity/gzip/gzip;q=0, and large HTML 200/404 responses with and without an explicit length. With gzip accepted, a 219000-byte synthetic HTML 404 changed from external HTTP/1.1 500 to the correct 404. Its decompressed body hash matched the source. Large 200 pages with gzip and HTTP/2 cases also passed. OpenResty syntax and historical-values rendering passed.

This is a partial mitigation, not a gateway fix. The authenticated new-post editor was 737716 bytes before gateway HTML injection and 85600 bytes after gzip. It returned 200 with real editor HTML over verified HTTP/2 (both identity and gzip), but HTTP/1.1 still returned 500 with either encoding because even compressed content exceeds the system limit. Explicit identity/gzip;q=0 large synthetic HTML also retains the HTTP/1.1 gateway failure. These cases are recorded as unresolved, not passed. No system gateway configuration was modified. The dedicated fixture/data and both Upload versions were removed after testing; shared services were retained.
