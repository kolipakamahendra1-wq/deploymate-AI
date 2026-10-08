import { useEffect, useId, useState } from "react";

/** Renders Mermaid source to SVG. The mermaid bundle loads only when this mounts. */
export default function MermaidDiagram({ source }: { source: string }) {
  const id = useId().replace(/[^a-zA-Z0-9]/g, "");
  const [svg, setSvg] = useState("");
  const [err, setErr] = useState("");

  useEffect(() => {
    let alive = true;
    import("mermaid").then(async ({ default: mermaid }) => {
      mermaid.initialize({
        startOnLoad: false,
        securityLevel: "strict",
        theme: "base",
        themeVariables: {
          fontFamily: "Public Sans, system-ui, sans-serif",
          primaryColor: "#F7F9FA", primaryBorderColor: "#2B4EFF", primaryTextColor: "#16222C",
          lineColor: "#46555F", clusterBkg: "#E9EEF2", clusterBorder: "#8A97A1",
        },
      });
      try {
        const out = await mermaid.render(`m${id}`, source);
        if (alive) { setSvg(out.svg); setErr(""); }
      } catch (e) {
        if (alive) setErr(e instanceof Error ? e.message : "Could not render diagram");
      }
    });
    return () => { alive = false; };
  }, [source, id]);

  if (err) return <p role="alert" className="text-sm text-[#9b1c1c]">{err}</p>;
  if (!svg) return <p className="text-sm text-ink-soft">Rendering diagram…</p>;
  // Mermaid output with securityLevel "strict" is sanitised before it reaches here.
  return <div role="img" aria-label="Architecture diagram" className="overflow-x-auto [&_svg]:mx-auto [&_svg]:max-w-full" dangerouslySetInnerHTML={{ __html: svg }} />;
}
