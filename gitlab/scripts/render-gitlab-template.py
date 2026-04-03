#!/usr/bin/env python3
"""Post-process helm template output for gitlab-in-olares Helm chart templates."""
import re
import sys

CLUSTER_ROLE_START = "# Source: gitlab/charts/nginx-ingress/templates/clusterrole.yaml\n"
CTRL_ROLE_START = "# Source: gitlab/charts/nginx-ingress/templates/controller-role.yaml\n"

def strip_horizontal_pod_autoscalers(text: str) -> str:
    """Drop HorizontalPodAutoscaler documents (Helm chart default; legacy v16 had none)."""
    parts = re.split(r"^---\s*\n", text, flags=re.M)
    kept = [p for p in parts if p.strip() and not re.search(
        r"^kind:\s*[\"']?HorizontalPodAutoscaler[\"']?", p, re.M
    )]
    if not kept:
        return text
    out = kept[0]
    for doc in kept[1:]:
        out += "---\n" + doc
    return out


def ensure_replicas_without_hpa(text: str) -> str:
    """After removing HPA, set static replica counts (match former minReplicas)."""
    text = text.replace(
        """    app.kubernetes.io/version: v18.10.1
  annotations:
    
spec:
  selector:
    matchLabels:
      app: gitlab-shell
      release: gitlab
      
  template:""",
        """    app.kubernetes.io/version: v18.10.1
  annotations:
    
spec:
  replicas: 1
  selector:
    matchLabels:
      app: gitlab-shell
      release: gitlab
      
  template:""",
        1,
    )
    text = text.replace(
        """    app.kubernetes.io/version: v18.10.1
  annotations:
    
spec:
  selector:
    matchLabels:
      app: kas
      release: gitlab
      
  template:""",
        """    app.kubernetes.io/version: v18.10.1
  annotations:
    
spec:
  replicas: 1
  selector:
    matchLabels:
      app: kas
      release: gitlab
      
  template:""",
        1,
    )
    text = text.replace(
        """    queue-pod-name: all-in-1
  annotations:
    
spec:
  selector:
    matchLabels:
      app: sidekiq
      release: gitlab
      
      queue-pod-name: all-in-1
  template:""",
        """    queue-pod-name: all-in-1
  annotations:
    
spec:
  replicas: 1
  selector:
    matchLabels:
      app: sidekiq
      release: gitlab
      
      queue-pod-name: all-in-1
  template:""",
        1,
    )
    text = text.replace(
        """spec:
  # Don't provide replicas when HPA are present
  # replicas: 2
  selector:
    matchLabels:
      app: webservice
      release: gitlab
      
      
      gitlab.com/webservice-name: default
  template:""",
        """spec:
  replicas: 1
  selector:
    matchLabels:
      app: webservice
      release: gitlab
      
      
      gitlab.com/webservice-name: default
  template:""",
        1,
    )
    text = text.replace(
        """spec:
  # Don't provide replicas when HPA are present
  # replicas: 2
  selector:
    matchLabels:
      app: registry
      release: gitlab
  template:""",
        """spec:
  replicas: 1
  selector:
    matchLabels:
      app: registry
      release: gitlab
  template:""",
        1,
    )
    return text


ROLE_CLUSTER_REPLACEMENT = """# Source: gitlab/charts/nginx-ingress/templates/clusterrole.yaml (namespaced Role; aligns with gitlab-in-olares)
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  labels:
    app: nginx-ingress
    chart: nginx-ingress-4.14.3
    release: gitlab
    heritage: Helm

    helm.sh/chart: nginx-ingress-4.14.3
    app.kubernetes.io/version: "1.14.3"
    app.kubernetes.io/part-of: nginx-ingress
    app.kubernetes.io/managed-by: Helm
  name: gitlab-nginx-ingress-cluster
  namespace: {{ .Release.Namespace }}
rules:
  - apiGroups:
      - ""
    resources:
      - configmaps
      - endpoints
      - nodes
      - pods
      - secrets
    verbs:
      - list
      - watch
  - apiGroups:
      - coordination.k8s.io
    resources:
      - leases
    verbs:
      - list
      - watch
  - apiGroups:
      - ""
    resources:
      - nodes
    verbs:
      - get
  - apiGroups:
      - ""
    resources:
      - services
    verbs:
      - get
      - list
      - watch
  - apiGroups:
      - networking.k8s.io
    resources:
      - ingresses
    verbs:
      - get
      - list
      - watch
  - apiGroups:
      - ""
    resources:
      - events
    verbs:
      - create
      - patch
  - apiGroups:
      - networking.k8s.io
    resources:
      - ingresses/status
    verbs:
      - update
  - apiGroups:
      - networking.k8s.io
    resources:
      - ingressclasses
    verbs:
      - get
      - list
      - watch
  - apiGroups:
      - discovery.k8s.io
    resources:
      - endpointslices
    verbs:
      - list
      - watch
      - get
---
# Source: gitlab/charts/nginx-ingress/templates/clusterrolebinding.yaml (namespaced RoleBinding; aligns with gitlab-in-olares)
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  labels:
    app: nginx-ingress
    chart: nginx-ingress-4.14.3
    release: gitlab
    heritage: Helm

    helm.sh/chart: nginx-ingress-4.14.3
    app.kubernetes.io/version: "1.14.3"
    app.kubernetes.io/part-of: nginx-ingress
    app.kubernetes.io/managed-by: Helm
  name: gitlab-nginx-ingress-cluster
  namespace: {{ .Release.Namespace }}
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: Role
  name: gitlab-nginx-ingress-cluster
subjects:
  - kind: ServiceAccount
    name: gitlab-nginx-ingress
    namespace: "{{ .Release.Namespace }}"
---
"""


def main() -> None:
    path_in = sys.argv[1]
    path_out = sys.argv[2]
    with open(path_in, encoding="utf-8") as f:
        text = f.read()

    if CLUSTER_ROLE_START not in text or CTRL_ROLE_START not in text:
        print("ERROR: expected nginx ClusterRole/controller-role markers missing", file=sys.stderr)
        sys.exit(1)

    pre, rest = text.split(CLUSTER_ROLE_START, 1)
    _, post_ctrl = rest.split(CTRL_ROLE_START, 1)
    text = pre + ROLE_CLUSTER_REPLACEMENT + CTRL_ROLE_START + post_ctrl

    # Namespace and in-cluster DNS
    text = re.sub(r"(?m)^(\s*)namespace: gitlab$", r"\1namespace: {{ .Release.Namespace }}", text)
    text = text.replace('namespace: "gitlab"', "namespace: {{ .Release.Namespace }}")
    text = text.replace(".gitlab.svc", ".{{ .Release.Namespace }}.svc")
    # Full cluster DNS FQDN: bare *.svc can cause ndots/DNS lookup timeouts; skip if already .svc.cluster.local
    text = re.sub(
        r"(\{\{ \.Release\.Namespace \}\})\.svc(?!\.cluster\.local)",
        r"\1.svc.cluster.local",
        text,
    )
    # ConfigMap cross-ref: namespace/name (not chart paths like gitlab/charts/...)
    text = re.sub(
        r"(?<![\w/])gitlab/gitlab-",
        "{{ .Release.Namespace }}/gitlab-",
        text,
    )
    # shared-secrets generate-secrets script: kubectl must target install NS (not helm template default "gitlab")
    text = text.replace("namespace=gitlab\n", "namespace={{ .Release.Namespace }}\n")
    # selfsign job: kubectl label uses $namespace; helm output may omit assignment (rely on empty = fragile)
    _selfsign_prefix = (
        "          certname=gitlab-wildcard-tls\n"
        "          # create wildcard certificate secret\n"
        "          kubectl create secret tls $certname"
    )
    _selfsign_prefix_fixed = (
        "          namespace={{ .Release.Namespace }}\n"
        "          certname=gitlab-wildcard-tls\n"
        "          # create wildcard certificate secret\n"
        "          kubectl create secret tls $certname"
    )
    if _selfsign_prefix in text and "namespace={{ .Release.Namespace }}\n          certname=gitlab-wildcard-tls" not in text:
        text = text.replace(_selfsign_prefix, _selfsign_prefix_fixed, 1)

    # Olares: nginx controller Deployment name matches previous chart (Service stays gitlab-nginx-ingress-controller)
    text = re.sub(
        r"(# Source: gitlab/charts/nginx-ingress/templates/controller-deployment\.yaml\n"
        r"apiVersion: apps/v1\n"
        r"kind: Deployment\n"
        r"metadata:\n"
        r"  labels:[\s\S]*?\n  name: )gitlab-nginx-ingress-controller\n",
        r"\1gitlab\n",
        text,
        count=1,
    )

    # Match IngressClass name gitlab-nginx (chart default class name; controller arg must agree)
    text = text.replace("- --ingress-class=nginx\n", "- --ingress-class=gitlab-nginx\n")

    # Mitigate pthread_create EAGAIN under small limits (same idea as prior gitlab-in-olares patch)
    if "worker-processes:" not in text:
        text = text.replace(
            "data:\n  add-headers:",
            "data:\n  worker-processes: \"1\"\n  add-headers:",
            1,
        )
    text = text.replace(
        """          resources: 
            requests:
              cpu: 100m
              memory: 100Mi
      
      serviceAccountName: gitlab-nginx-ingress""",
        """          resources: 
            requests:
              cpu: 100m
              memory: 256Mi
            limits:
              cpu: 500m
              memory: 512Mi
      
      serviceAccountName: gitlab-nginx-ingress""",
        1,
    )

    # Helm 9.x emits HPAs by default; strip to align with legacy single-file manifest
    text = strip_horizontal_pod_autoscalers(text)
    text = ensure_replicas_without_hpa(text)

    # Kubernetes 1.25+ / Olares: deprecated API versions removed from apiserver
    text = upgrade_k8s_api_versions(text)

    with open(path_out, "w", encoding="utf-8") as f:
        f.write(text)
    print(f"Wrote {path_out}")


def upgrade_k8s_api_versions(text: str) -> str:
    """Align rendered manifests with modern clusters (no policy/v1beta1, extensions/v1beta1 Ingress, etc.)."""
    text = text.replace("apiVersion: policy/v1beta1", "apiVersion: policy/v1")
    text = text.replace("apiVersion: autoscaling/v2beta1", "apiVersion: autoscaling/v2")
    # Ingress: extensions/v1beta1 -> networking.k8s.io/v1 (same blocks as templates/gitlab.yaml)
    if "apiVersion: extensions/v1beta1" in text:
        text = text.replace(
            """# Source: gitlab/charts/gitlab/charts/kas/templates/ingress.yaml
apiVersion: extensions/v1beta1
kind: Ingress
metadata:
  name: gitlab-kas
  namespace: {{ .Release.Namespace }}
  labels:
    app: kas
    chart: kas-9.10.1
    release: gitlab
    heritage: Helm
    
  annotations:
    kubernetes.io/ingress.class: "gitlab-nginx"
    kubernetes.io/ingress.provider: "nginx"
    nginx.ingress.kubernetes.io/proxy-buffering: "off"
    nginx.ingress.kubernetes.io/custom-http-errors: ""
    
spec:
  
  rules:
    - host: kas.example.com
      http:
        paths:
          - path: "/k8s-proxy/"
            backend:
              serviceName: gitlab-kas
              servicePort: 8154
          - path: "/"
            backend:
              serviceName: gitlab-kas
              servicePort: 8150
          
          
  tls:
    - hosts:
      - kas.example.com
      secretName: gitlab-wildcard-tls""",
            """# Source: gitlab/charts/gitlab/charts/kas/templates/ingress.yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: gitlab-kas
  namespace: {{ .Release.Namespace }}
  labels:
    app: kas
    chart: kas-9.10.1
    release: gitlab
    heritage: Helm
    
  annotations:
    kubernetes.io/ingress.class: "gitlab-nginx"
    kubernetes.io/ingress.provider: "nginx"
    nginx.ingress.kubernetes.io/proxy-buffering: "off"
    nginx.ingress.kubernetes.io/custom-http-errors: ""
    
spec:
  ingressClassName: gitlab-nginx
  rules:
    - host: kas.example.com
      http:
        paths:
          - path: "/k8s-proxy/"
            pathType: Prefix
            backend:
              service:
                name: gitlab-kas
                port:
                  number: 8154
          - path: "/"
            pathType: Prefix
            backend:
              service:
                name: gitlab-kas
                port:
                  number: 8150
  tls:
    - hosts:
      - kas.example.com
      secretName: gitlab-wildcard-tls""",
            1,
        )
        text = text.replace(
            """# Source: gitlab/charts/gitlab/charts/webservice/templates/ingress.yaml
apiVersion: extensions/v1beta1
kind: Ingress
metadata:
  name: gitlab-webservice-default
  namespace: {{ .Release.Namespace }}
  labels:
    app: webservice
    chart: webservice-9.10.1
    release: gitlab
    heritage: Helm
    gitlab.com/webservice-name: default
    
  annotations:
    kubernetes.io/ingress.class: "gitlab-nginx"
    kubernetes.io/ingress.provider: "nginx"
    
    nginx.ingress.kubernetes.io/proxy-body-size: "512m"
    nginx.ingress.kubernetes.io/proxy-connect-timeout: "15"
    nginx.ingress.kubernetes.io/proxy-read-timeout: "600"
    nginx.ingress.kubernetes.io/service-upstream: "true"
spec:
  
  rules:
    - host: gitlab.example.com
      http:
        paths:
          - path: /
            backend:
              serviceName: gitlab-webservice-default
              servicePort: 8181
  tls:
    - hosts:
      - gitlab.example.com
      secretName: gitlab-wildcard-tls""",
            """# Source: gitlab/charts/gitlab/charts/webservice/templates/ingress.yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: gitlab-webservice-default
  namespace: {{ .Release.Namespace }}
  labels:
    app: webservice
    chart: webservice-9.10.1
    release: gitlab
    heritage: Helm
    gitlab.com/webservice-name: default
    
  annotations:
    kubernetes.io/ingress.class: "gitlab-nginx"
    kubernetes.io/ingress.provider: "nginx"
    
    nginx.ingress.kubernetes.io/proxy-body-size: "512m"
    nginx.ingress.kubernetes.io/proxy-connect-timeout: "15"
    nginx.ingress.kubernetes.io/proxy-read-timeout: "600"
    nginx.ingress.kubernetes.io/service-upstream: "true"
spec:
  ingressClassName: gitlab-nginx
  rules:
    - host: gitlab.example.com
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: gitlab-webservice-default
                port:
                  number: 8181
  tls:
    - hosts:
      - gitlab.example.com
      secretName: gitlab-wildcard-tls""",
            1,
        )
        text = text.replace(
            """# Source: gitlab/charts/minio/templates/ingress.yaml
apiVersion: extensions/v1beta1
kind: Ingress
metadata:
  name: gitlab-minio
  namespace: {{ .Release.Namespace }}
  labels:
    app: minio
    chart: minio-0.4.3
    release: gitlab
    heritage: Helm
    
  annotations:
    kubernetes.io/ingress.class: "gitlab-nginx"
    kubernetes.io/ingress.provider: "nginx"
    nginx.ingress.kubernetes.io/proxy-body-size: "0"
    nginx.ingress.kubernetes.io/proxy-read-timeout: "900"
    nginx.ingress.kubernetes.io/proxy-request-buffering: "off"
    nginx.ingress.kubernetes.io/proxy-buffering: "off"
    
spec:
  
  rules:
    - host: minio.example.com
      http:
        paths:
          - path: /
            backend:
              serviceName: gitlab-minio-svc
              servicePort: 9000
  tls:
    - hosts:
      - minio.example.com
      secretName: gitlab-wildcard-tls""",
            """# Source: gitlab/charts/minio/templates/ingress.yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: gitlab-minio
  namespace: {{ .Release.Namespace }}
  labels:
    app: minio
    chart: minio-0.4.3
    release: gitlab
    heritage: Helm
    
  annotations:
    kubernetes.io/ingress.class: "gitlab-nginx"
    kubernetes.io/ingress.provider: "nginx"
    nginx.ingress.kubernetes.io/proxy-body-size: "0"
    nginx.ingress.kubernetes.io/proxy-read-timeout: "900"
    nginx.ingress.kubernetes.io/proxy-request-buffering: "off"
    nginx.ingress.kubernetes.io/proxy-buffering: "off"
    
spec:
  ingressClassName: gitlab-nginx
  rules:
    - host: minio.example.com
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: gitlab-minio-svc
                port:
                  number: 9000
  tls:
    - hosts:
      - minio.example.com
      secretName: gitlab-wildcard-tls""",
            1,
        )
        text = text.replace(
            """# Source: gitlab/charts/registry/templates/ingress.yaml
apiVersion: extensions/v1beta1
kind: Ingress
metadata:
  name: gitlab-registry
  namespace: {{ .Release.Namespace }}
  labels:
    app: registry
    chart: registry-0.7.0
    release: gitlab
    heritage: Helm
    
  annotations:
    kubernetes.io/ingress.class: "gitlab-nginx"
    kubernetes.io/ingress.provider: "nginx"
    nginx.ingress.kubernetes.io/proxy-body-size: "0"
    nginx.ingress.kubernetes.io/proxy-read-timeout: "900"
    nginx.ingress.kubernetes.io/proxy-request-buffering: "off"
    nginx.ingress.kubernetes.io/proxy-buffering: "off"
    
spec:
  
  rules:
    - host: registry.example.com
      http:
        paths:
          - path: /
            backend:
              serviceName: gitlab-registry
              servicePort: 5000
  tls:
    - hosts:
      - registry.example.com
      secretName: gitlab-wildcard-tls""",
            """# Source: gitlab/charts/registry/templates/ingress.yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: gitlab-registry
  namespace: {{ .Release.Namespace }}
  labels:
    app: registry
    chart: registry-0.7.0
    release: gitlab
    heritage: Helm
    
  annotations:
    kubernetes.io/ingress.class: "gitlab-nginx"
    kubernetes.io/ingress.provider: "nginx"
    nginx.ingress.kubernetes.io/proxy-body-size: "0"
    nginx.ingress.kubernetes.io/proxy-read-timeout: "900"
    nginx.ingress.kubernetes.io/proxy-request-buffering: "off"
    nginx.ingress.kubernetes.io/proxy-buffering: "off"
    
spec:
  ingressClassName: gitlab-nginx
  rules:
    - host: registry.example.com
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: gitlab-registry
                port:
                  number: 5000
  tls:
    - hosts:
      - registry.example.com
      secretName: gitlab-wildcard-tls""",
            1,
        )
    return text


if __name__ == "__main__":
    main()
