"""
Experiment 06: Export LangGraph Mermaid Graph to PNG and MMD
Uses `agent_graph.get_graph().draw_mermaid_png()` and `.draw_mermaid()`
Saves output cleanly to `docs/assets/agent_graph.png` and `docs/assets/agent_graph.mmd`.
"""

import os
import sys
from pathlib import Path

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from sketchflow.agent.graph import agent_graph

def export_graph_assets(output_dir: Path = None):
    if output_dir is None:
        output_dir = PROJECT_ROOT / "docs" / "assets"
    
    output_dir.mkdir(parents=True, exist_ok=True)
    
    png_path = output_dir / "agent_graph.png"
    mmd_path = output_dir / "agent_graph.mmd"

    print("=" * 60)
    print("SketchFlow Agent Graph Asset Exporter")
    print("=" * 60)
    
    graph = agent_graph.get_graph()
    
    # 1. Export Mermaid markup
    print("[1/2] Generating Mermaid diagram specification...")
    mermaid_markup = graph.draw_mermaid()
    with open(mmd_path, "w", encoding="utf-8") as f:
        f.write(mermaid_markup)
    print(f"  -> Saved Mermaid markup to: {mmd_path} ({len(mermaid_markup)} chars)")

    # 2. Export PNG
    print("[2/2] Rendering LangGraph topology to PNG...")
    try:
        png_bytes = graph.draw_mermaid_png()
        with open(png_path, "wb") as f:
            f.write(png_bytes)
        print(f"  -> Successfully generated PNG: {png_path} ({len(png_bytes):,} bytes)")
    except Exception as e:
        print(f"  [!] Remote mermaid.ink rendering encountered an error: {e}")
        print("  [i] Mermaid text markup is preserved at:", mmd_path)
        raise e

    print("=" * 60)
    print("Export complete! Assets ready in docs/assets/")
    print("=" * 60)

if __name__ == "__main__":
    export_graph_assets()
