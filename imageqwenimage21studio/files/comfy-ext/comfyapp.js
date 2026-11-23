// Open a studio flow instead of ComfyUI's default graph: on a browser's first
// visit (the first flow), and whenever the page is opened as
// /comfy/?comfyapp=<mode> (the studio's "Open in ComfyUI"). The flow's model
// filenames are rewritten to the installed variant's.
import { app } from "../../scripts/app.js";

const SHOWN = "comfyapp.workflowShown";

const getJSON = (f) =>
  fetch(new URL(f, import.meta.url)).then((r) => (r.ok ? r.json() : null)).catch(() => null);

function replaceModels(node, replace) {
  if (!Array.isArray(node.widgets_values)) return;
  node.widgets_values = node.widgets_values.map((v) => (typeof v === "string" && replace[v]) || v);
}

app.registerExtension({
  name: "comfyapp.defaultWorkflow",
  async setup() {
    const url = new URL(location.href);
    const forced = url.searchParams.has("comfyapp");
    const asked = url.searchParams.get("comfyapp") || "";
    if (forced) {
      url.searchParams.delete("comfyapp");
      history.replaceState(history.state, "", url);
    }
    let shown = false;
    try { shown = localStorage.getItem(SHOWN) === "1"; } catch {}
    if (shown && !forced) return;

    const [cfg, status] = await Promise.all([
      getJSON("./app.json"),
      fetch("/studio/api/health").then((r) => (r.ok ? r.json() : null)).catch(() => null),
    ]);
    const flows = status?.flows || [];
    const mode = flows.some((f) => f.mode === asked) ? asked : flows[0]?.mode || "main";
    const wf = await getJSON(`./flows/${encodeURIComponent(mode)}.json`) || await getJSON("./workflow.json");
    if (!wf) return;
    const replace = status?.replace || {};
    if (Object.keys(replace).length) {
      for (const n of wf.nodes || []) replaceModels(n, replace);
      for (const sg of wf.definitions?.subgraphs || []) for (const n of sg.nodes || []) replaceModels(n, replace);
    }
    const label = flows.find((f) => f.mode === mode)?.label;
    await app.loadGraphData(wf, true, true, [cfg?.name || "workflow", label].filter(Boolean).join(" · "));
    try { localStorage.setItem(SHOWN, "1"); } catch {}
  },
});
