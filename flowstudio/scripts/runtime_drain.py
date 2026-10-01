"""Helm 只删 chart 对象。卸装前必须排空运行时对象，否则 namespace 卡 Terminating。

覆盖：动态引擎 Deployment/Service、预拉 Job 及其 Pod、本实例 GPUBinding。
不碰 appCommon / 模型权重。
"""

from __future__ import annotations

import json
import os
import ssl
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Callable

APP_DEFAULT = "flowstudio"
LABEL_ENGINE = "flowstudio.bytetrade.io/engine=true"
LABEL_PREPULL = "flowstudio.bytetrade.io/engine-prepull=true"
# ImagePull / sidecar 残留会挡住 namespace；立刻杀，不等 grace。
_GRACE0 = "gracePeriodSeconds=0"
_JOB_PROP = f"propagationPolicy=Background&{_GRACE0}"
_WAIT_S = 90.0
_POLL_S = 2.0

HttpCall = Callable[[str, str], dict[str, Any]]


def ignore_http_error(method: str, code: int) -> bool:
    return code == 404 or (code == 409 and method == "DELETE")


def owner_from_namespace(namespace: str, app: str) -> str:
    """``<app>-<owner>``；shared 命名空间不是用户 owner。"""
    prefix = f"{app}-"
    if not namespace.startswith(prefix):
        return ""
    suffix = namespace[len(prefix) :]
    return "" if suffix == "shared" else suffix


def binding_ours(item: dict[str, Any], *, ns: str, app: str, owner: str) -> bool:
    spec = item.get("spec") or {}
    bns = str(spec.get("namespace") or "").strip()
    if bns:
        return bns == ns
    if str(spec.get("appName") or "").strip() != app:
        return False
    # 删除侧：owner 未知时不能按 appName 认领，避免扫掉其他用户的绑定。
    if not owner:
        return False
    bowner = str(spec.get("owner") or "").strip()
    return not bowner or bowner == owner


def names(data: dict[str, Any]) -> list[str]:
    # Terminating + finalizer 仍挡 namespace，必须计入残留。
    out: list[str] = []
    for item in data.get("items") or []:
        name = str((item.get("metadata") or {}).get("name") or "").strip()
        if name:
            out.append(name)
    return out


def drain(
    call: HttpCall,
    *,
    ns: str,
    app: str,
    owner: str = "",
    wait_s: float = _WAIT_S,
) -> dict[str, int]:
    """按标签删运行时对象，再等到集合空（或超时）。

    删除尽力而为：某一类失败不能挡住其余（尤其是会卡住 namespace 的 Job/Pod）。
    是否清空必须严格确认。
    """
    owner = (owner or owner_from_namespace(ns, app)).strip()
    counts = _purge_namespaced(call, ns)
    counts["gpubinding"] = _purge_gpu_bindings(call, ns=ns, app=app, owner=owner)

    leftover = _wait_empty(call, ns=ns, wait_s=wait_s)
    if leftover:
        extra = _purge_namespaced(call, ns)
        for key in ("deploy", "svc", "job", "pod"):
            counts[key] += extra[key]
        leftover = _wait_empty(call, ns=ns, wait_s=min(15.0, wait_s))
    if leftover:
        counts["leftover"] = leftover
    return counts


def _purge_namespaced(call: HttpCall, ns: str) -> dict[str, int]:
    # 与 leftover 同一集合：挡住 namespace 的运行时对象。
    return {
        "deploy": _delete_listed(
            call, f"/apis/apps/v1/namespaces/{ns}/deployments", LABEL_ENGINE
        ),
        "svc": _delete_listed(call, f"/api/v1/namespaces/{ns}/services", LABEL_ENGINE),
        "job": _delete_listed(
            call, f"/apis/batch/v1/namespaces/{ns}/jobs", LABEL_PREPULL, extra=_JOB_PROP
        ),
        "pod": (
            _delete_listed(
                call, f"/api/v1/namespaces/{ns}/pods", LABEL_PREPULL, extra=_GRACE0
            )
            + _delete_listed(
                call, f"/api/v1/namespaces/{ns}/pods", LABEL_ENGINE, extra=_GRACE0
            )
        ),
    }


def _purge_gpu_bindings(call: HttpCall, *, ns: str, app: str, owner: str) -> int:
    # cluster-scoped：失败不得阻断 namespace 内 Job/Pod 排空。
    gpu_path = "/apis/gpu.bytetrade.io/v1alpha1/gpubindings"
    try:
        items = call("GET", gpu_path).get("items") or []
    except Exception as exc:
        print(f"runtime_drain gpu list skipped: {exc}", flush=True)
        return 0
    n = 0
    for item in items:
        name = str((item.get("metadata") or {}).get("name") or "").strip()
        if not name or not binding_ours(item, ns=ns, app=app, owner=owner):
            continue
        try:
            call("DELETE", f"{gpu_path}/{name}")
        except Exception as exc:
            print(f"runtime_drain gpu delete skipped {name}: {exc}", flush=True)
            continue
        n += 1
    return n


def _delete_listed(call: HttpCall, api_path: str, label: str, *, extra: str = "") -> int:
    q = urllib.parse.urlencode({"labelSelector": label})
    try:
        data = call("GET", f"{api_path}?{q}")
    except Exception as exc:
        print(f"runtime_drain list skipped {api_path}: {exc}", flush=True)
        return 0
    n = 0
    for name in names(data):
        path = f"{api_path}/{name}"
        if extra:
            path = f"{path}?{extra}"
        try:
            call("DELETE", path)
        except Exception as exc:
            print(f"runtime_drain delete skipped {path}: {exc}", flush=True)
            continue
        n += 1
    return n


def _wait_empty(call: HttpCall, *, ns: str, wait_s: float) -> int:
    deadline = time.monotonic() + max(0.0, wait_s)
    while True:
        leftover = _leftover_count(call, ns)
        if leftover == 0:
            return 0
        if time.monotonic() >= deadline:
            return leftover
        time.sleep(_POLL_S)


def _leftover_count(call: HttpCall, ns: str) -> int:
    total = 0
    for path, label in (
        (f"/apis/apps/v1/namespaces/{ns}/deployments", LABEL_ENGINE),
        (f"/api/v1/namespaces/{ns}/services", LABEL_ENGINE),
        (f"/apis/batch/v1/namespaces/{ns}/jobs", LABEL_PREPULL),
        (f"/api/v1/namespaces/{ns}/pods", LABEL_PREPULL),
        (f"/api/v1/namespaces/{ns}/pods", LABEL_ENGINE),
    ):
        q = urllib.parse.urlencode({"labelSelector": label})
        try:
            total += len(names(call("GET", f"{path}?{q}")))
        except Exception as exc:
            print(f"runtime_drain leftover list skipped {path}: {exc}", flush=True)
            # 列不出就不能声称已空。
            total += 1
    return total


def in_cluster_call(method: str, path: str) -> dict[str, Any]:
    sa = "/var/run/secrets/kubernetes.io/serviceaccount"
    token = open(f"{sa}/token").read().strip()
    ctx = ssl.create_default_context(cafile=f"{sa}/ca.crt")
    req = urllib.request.Request(
        "https://kubernetes.default.svc" + path,
        method=method,
        headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, context=ctx, timeout=30) as resp:
            body = resp.read().decode() or "{}"
            return json.loads(body) if body.strip() else {}
    except urllib.error.HTTPError as exc:
        if ignore_http_error(method, exc.code):
            return {}
        raise


def main() -> None:
    sa = "/var/run/secrets/kubernetes.io/serviceaccount"
    ns = open(f"{sa}/namespace").read().strip()
    app = (os.environ.get("OLARES_APP_NAME") or APP_DEFAULT).strip() or APP_DEFAULT
    owner = (os.environ.get("OLARES_OWNER") or "").strip()
    counts = drain(in_cluster_call, ns=ns, app=app, owner=owner)
    leftover = int(counts.get("leftover") or 0)
    print(
        "runtime_drain done "
        + " ".join(f"{k}={v}" for k, v in counts.items() if k != "leftover")
        + (f" leftover={leftover}" if leftover else ""),
        flush=True,
    )
    if leftover:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
