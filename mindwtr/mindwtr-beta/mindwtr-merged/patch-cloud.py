#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""给 Mindwtr Cloud 的服务端源码插入一条 /mcp 转发分支。

背景
----
Mindwtr Cloud 的 HTTP 服务端是 apps/cloud/src/server.ts，用 Bun 原生 serve 启动，
路由是一条写在 fetch handler 内部的 if/else 长链，没有 Web 框架，也没有导出可挂载的
fetch handler。想让同一个容器里的 MCP helper（apps/mcp-server，npm 包 mindwtr-mcp）
跟 Cloud 共用对外端口，有两条路：

  A. 在 Cloud 自己的 fetch handler 里加一条 /mcp 分支，内部转发给 helper；
  B. 在 Cloud 前面加一层反向代理（nginx / bun 脚本）。

本脚本做的是 A。插入点被刻意选在「OPTIONS 分支之后、/health 与 /ready 之后、第一条被
withNamespace(...) 包裹的 /v1 路由之前」，因为 Cloud 的 token 鉴权是逐路由写在
withNamespace 内部的，插在这个位置，/mcp 不会被 Cloud 的 Bearer 白名单拦到，两套鉴权
互不干扰。

用法
----
    python3 patch-cloud.py [路径]            # 默认 apps/cloud/src/server.ts
    python3 patch-cloud.py --check 路径       # 只检查不写入（干跑）
    python3 patch-cloud.py --print 路径       # 打印插入前后带行号的片段

脚本是幂等的：已经打过补丁的文件再次执行会直接退出并报告 ALREADY PATCHED。
任何一步失败都返回非零退出码，让 docker build 立刻失败。
"""

import argparse
import io
import os
import re
import sys

DEFAULT_TARGET = os.path.join('apps', 'cloud', 'src', 'server.ts')

# 补丁标记：用于幂等判断，也方便在改动后的源码里一眼认出插入点。
MARKER = 'MINDWTR_MCP_UPSTREAM'
BLOCK_HEADER = '// --- Mindwtr MCP passthrough (added by mindwtr-merged/patch-cloud.py) ---'

# 插入的代码块。缩进会在写入时按目标位置自动对齐（上游用的是 4 空格缩进）。
BLOCK_TEMPLATE = """\
// --- Mindwtr MCP passthrough (added by mindwtr-merged/patch-cloud.py) ---
// Forwards /mcp and /healthz to the MCP helper process running in the same
// container. This branch sits before every withNamespace(...) wrapped route,
// so the Cloud bearer-token allowlist never applies here: the helper does its
// own Bearer check with its own token.
// The helper rejects a request whose Origin hostname differs from the host it
// binds to (isAllowedOrigin in apps/mcp-server/src/http-server.ts), so Origin
// and Host are dropped; Authorization is forwarded untouched.
if (pathname === '/mcp' || pathname === '/healthz') {{
    const upstream = process.env.MINDWTR_MCP_UPSTREAM ?? 'http://127.0.0.1:8723';
    const upstreamHeaders = new Headers(req.headers);
    upstreamHeaders.delete('origin');
    upstreamHeaders.delete('host');
    const upstreamInit: RequestInit = {{
        method: req.method,
        headers: upstreamHeaders,
    }};
    if (req.method !== 'GET' && req.method !== 'HEAD' && req.body) {{
        upstreamInit.body = req.body as unknown as BodyInit;
    }}
    return fetch(`${{upstream}}${{pathname}}${{url.search}}`, upstreamInit);
}}
// --- end of Mindwtr MCP passthrough ---
"""


def fail(message):
    sys.stderr.write('[patch-cloud] ERROR: %s\n' % message)
    sys.exit(1)


def read_source(path):
    with io.open(path, 'r', encoding='utf-8') as handle:
        return handle.read()


def find_anchor(source):
    """返回 (插入位置下标, 该行缩进, 锚点行描述)。

    第一条 withNamespace(...) 调用本身位于某个路由判断 if (...) 块内部，
    直接把代码插在它前面会让新分支只在 /v1 路由命中时才执行，语义是错的。
    所以要从 withNamespace 所在行往上找那个 if 语句的起始行，插在它之前。
    """
    fetch_anchor = source.find('async fetch(req: Request)')
    if fetch_anchor < 0:
        fail('找不到 "async fetch(req: Request)"：这个文件可能不是 Mindwtr Cloud 的 server.ts。')

    # 第一条被 withNamespace(...) 包裹的 /v1 路由，就是第一条 /v1 分支。
    namespace_anchor = source.find('withNamespace(', fetch_anchor)
    if namespace_anchor < 0:
        fail('找不到 withNamespace( 调用：无法定位插入点。')

    lines = source.split('\n')
    namespace_line = source.count('\n', 0, namespace_anchor)
    namespace_indent = len(lines[namespace_line]) - len(lines[namespace_line].lstrip())

    # 往上找最近的一行 if (，即包裹该路由判断的 if 语句起点。
    # 条件本身是多行的（`if (` / `|| pathname...` / `) {`），所以只认以 if 开头的行，
    # 跳过 `) {` 这类续行。
    insert_line = namespace_line
    for candidate in range(namespace_line - 1, -1, -1):
        stripped = lines[candidate].strip()
        if re.match(r'^if\s*\(', stripped):
            insert_line = candidate
            break
        # 没有外层 if：遇到同缩进的其他语句就停，插在它后面。
        indent = len(lines[candidate]) - len(stripped)
        if indent < namespace_indent and stripped and not stripped.startswith(('||', ')', '//')):
            insert_line = candidate + 1
            break

    line_start = sum(len(line) + 1 for line in lines[:insert_line])
    anchor_line = lines[insert_line].strip()
    indent = lines[insert_line][:len(lines[insert_line]) - len(anchor_line)]
    if not indent:
        fail('插入点所在行没有缩进，无法安全插入。')
    return line_start, indent, anchor_line


def build_block(indent):
    body = BLOCK_TEMPLATE.format().rstrip('\n')
    return ''.join('%s%s\n' % (indent, line) if line.strip() else '\n' for line in body.split('\n'))


def render_context(source, line_start, context=6):
    lines = source.split('\n')
    # line_start 指向插入位置所在的行首，换算成 1-based 行号。
    anchor_index = source.count('\n', 0, line_start)
    begin = max(0, anchor_index - context)
    end = min(len(lines), anchor_index + context + 1)
    out = []
    for number in range(begin, end):
        out.append('%5d| %s' % (number + 1, lines[number]))
    return '\n'.join(out)


def main():
    parser = argparse.ArgumentParser(description='给 Mindwtr Cloud 的 server.ts 插入 /mcp 转发分支')
    parser.add_argument('path', nargs='?', default=DEFAULT_TARGET, help='目标文件路径')
    parser.add_argument('--check', action='store_true', help='只检查，不写入')
    parser.add_argument('--print', dest='do_print', action='store_true', help='打印插入点前后带行号的片段')
    args = parser.parse_args()

    path = args.path
    if not os.path.isfile(path):
        fail('目标文件不存在：%s' % path)

    source = read_source(path)

    if MARKER in source:
        print('[patch-cloud] ALREADY PATCHED: %s 已包含 %s，跳过。' % (path, MARKER))
        if args.do_print:
            line_start = source.find(MARKER)
            print(render_context(source, line_start))
        return 0

    line_start, indent, anchor_line = find_anchor(source)

    print('[patch-cloud] target      : %s' % path)
    print('[patch-cloud] anchor line : %s' % anchor_line[:120])
    print('[patch-cloud] indent      : %d spaces' % len(indent))

    if args.do_print:
        print('[patch-cloud] --- context before insertion ---')
        print(render_context(source, line_start))
        print('[patch-cloud] --- context after insertion (preview) ---')
        preview = source[:line_start] + build_block(indent) + source[line_start:]
        preview_start = line_start + len(build_block(indent))
        print(render_context(preview, preview_start))

    if args.check:
        print('[patch-cloud] CHECK ONLY: 未写入任何内容。')
        return 0

    patched = source[:line_start] + build_block(indent) + source[line_start:]
    with io.open(path, 'w', encoding='utf-8') as handle:
        handle.write(patched)

    # 写回后复核：插入块只出现一次，且关键锚点在位。
    verify = read_source(path)
    if verify.count(MARKER) != 1:
        fail('写入后校验失败：期望 %s 出现 1 次，实际 %d 次。' % (MARKER, verify.count(MARKER)))
    if verify.count(BLOCK_HEADER) != 1:
        fail('写入后校验失败：插入块出现 %d 次，期望 1 次。' % verify.count(BLOCK_HEADER))
    if "pathname === '/mcp'" not in verify:
        fail('写入后校验失败：插入块里没有 /mcp 路由判断。')
    print('[patch-cloud] PATCH OK: 已在 %s 插入 /mcp 与 /healthz 转发分支。' % path)
    print('[patch-cloud] --- inserted region ---')
    print(render_context(verify, line_start, context=4))
    return 0


if __name__ == '__main__':
    sys.exit(main())
