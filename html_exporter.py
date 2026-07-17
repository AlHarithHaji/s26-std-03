import os
from disassembly_loader import build_guide


def export_to_html(json_path, include_bom=False):
    """
    Generates an interactive HTML disassembly guide with
    collapsible step cards and an embedded Dark/Light mode toggle.
    """
    guide = build_guide(json_path, include_bom=include_bom)

    # Pre-collect active parent components for pipeline continuity
    active_parent_names = set()
    for step in guide.steps:
        source_name = guide.product.name if step.index == 1 or not guide.steps[step.index - 2].continues_as else \
        guide.steps[step.index - 2].continues_as.name
        active_parent_names.add(source_name)

    # Core HTML structure, CSS layout variables, and custom themes
    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Disassembly Guide - {guide.product.name}</title>
    <style>
        :root {{
            --bg-color: #f4f7f6;
            --card-bg: #ffffff;
            --text-color: #333333;
            --primary-color: #2c3e50;
            --accent-color: #e74c3c;
            --warning-bg: #fff3cd;
            --warning-border: #ffeeba;
            --warning-text: #856404;
            --border-color: #dddddd;
        }}
        [data-theme="dark"] {{
            --bg-color: #1e1e24;
            --card-bg: #2a2a35;
            --text-color: #e0e0e0;
            --primary-color: #34495e;
            --accent-color: #ff6b6b;
            --warning-bg: #3a331a;
            --warning-border: #66511a;
            --warning-text: #ffe082;
            --border-color: #444455;
        }}
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background-color: var(--bg-color);
            color: var(--text-color);
            margin: 0;
            padding: 20px;
            transition: all 0.3s ease;
        }}
        .container {{ max-width: 900px; margin: 0 auto; }}
        header {{ display: flex; justify-content: space-between; align-items: center; border-bottom: 2px solid var(--accent-color); padding-bottom: 10px; margin-bottom: 20px; }}
        h1 {{ margin: 0; color: var(--accent-color); }}
        .theme-toggle {{ background-color: var(--primary-color); color: white; border: none; padding: 10px 15px; border-radius: 5px; cursor: pointer; font-weight: bold; }}
        .warning-box {{ background-color: var(--warning-bg); border: 1px solid var(--warning-border); color: var(--warning-text); padding: 15px; border-radius: 5px; margin-bottom: 25px; }}
        .step-card {{ background-color: var(--card-bg); border: 1px solid var(--border-color); border-radius: 8px; margin-bottom: 15px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); overflow: hidden; }}
        .step-header {{ background-color: var(--primary-color); color: white; padding: 15px; cursor: pointer; display: flex; justify-content: space-between; align-items: center; font-weight: bold; }}
        .step-content {{ padding: 20px; display: block; }}
        .tools-badge {{ background-color: var(--accent-color); color: white; padding: 3px 8px; border-radius: 4px; font-size: 0.9em; display: inline-block; margin-bottom: 10px; }}
        ul {{ padding-left: 20px; }}
        li {{ margin-bottom: 8px; }}
        .resume-text {{ color: var(--accent-color); font-weight: bold; margin-top: 15px; font-style: italic; }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>Disassembly Wizard: {guide.product.name}</h1>
            <button class="theme-toggle" onclick="toggleTheme()">Toggle Dark Mode</button>
        </header>
"""

    # Add Pipeline Validation Warnings block if any exist
    if guide.warnings:
        html_content += '<div class="warning-box"><h3>⚠️ Validation Warnings</h3><ul>'
        for warning in guide.warnings:
            html_content += f"<li><strong>[{warning.severity.upper()}]</strong> Rule '{warning.rule}': {warning.message}</li>"
        html_content += '</ul></div>'

    # Inietta la Bill of Materials se richiesta
    if hasattr(guide, 'bill_of_materials') and guide.bill_of_materials:
        html_content += f"""
        <div class="step-card">
            <div class="step-header" onclick="toggleStep(this)">
                <span>📋 Bill of Materials (BoM)</span>
                <span>▼</span>
            </div>
            <div class="step-content">
                <table style="width: 100%; border-collapse: collapse; text-align: left;">
                    <tr style="border-bottom: 2px solid var(--primary-color);">
                        <th style="padding: 8px;">Component</th>
                        <th style="padding: 8px;">Weight</th>
                        <th style="padding: 8px;">Material</th>
                        <th style="padding: 8px;">Color</th>
                    </tr>
        """
        for item in guide.bill_of_materials:
            w_str = f"{int(item.weight) if isinstance(item.weight, float) and item.weight.is_integer() else item.weight} g" if item.weight is not None else "—"
            m_str = str(item.material) if item.material is not None else "—"
            col_str = str(item.color) if item.color is not None else "—"
            html_content += f"""
                    <tr style="border-bottom: 1px solid var(--border-color);">
                        <td style="padding: 8px;">{item.name}</td>
                        <td style="padding: 8px;">{w_str}</td>
                        <td style="padding: 8px;">{m_str}</td>
                        <td style="padding: 8px;">{col_str}</td>
                    </tr>
            """
        html_content += "</table></div></div>"

    html_content += '<div class="steps-container">'

    # Render data loop matching Simone's file output logic 1:1
    for step in guide.steps:
        current_source = guide.product.name if step.index == 1 or not guide.steps[step.index - 2].continues_as else \
        guide.steps[step.index - 2].continues_as.name
        html_content += f"""
        <div class="step-card">
            <div class="step-header" onclick="toggleStep(this)">
                <span>Action {step.index}: {step.operation} (From: {current_source})</span>
                <span>▼</span>
            </div>
            <div class="step-content">
        """

        if step.tools_required:
            tools_str = ", ".join(step.tools_required)
            html_content += f'<div class="tools-badge">Tools Required: {tools_str}</div>'

        if step.actions:
            html_content += '<ul>'
            for action in step.actions:
                html_content += f"<li>{action.text}</li>"
            html_content += '</ul>'

        # Sub-branch execution tracking
        collected_sub_roots = []
        if step.continues_as and step.continues_as.name in active_parent_names:
            collected_sub_roots.append(step.continues_as.name)
        for out_component in step.outputs:
            if out_component.name in active_parent_names and out_component.name not in collected_sub_roots:
                collected_sub_roots.append(out_component.name)

        if collected_sub_roots:
            resume_phrases = [f'"{name}"' for name in collected_sub_roots]
            html_content += f'<p class="resume-text">➡️ Then resume disassembling from: {", ".join(resume_phrases)}</p>'

        html_content += "</div></div>"

    # Interactive JavaScript functions embedded natively
    html_content += """
        </div>
    </div>
    <script>
        function toggleTheme() {
            const body = document.body;
            if (body.getAttribute('data-theme') === 'dark') {
                body.removeAttribute('data-theme');
            } else {
                body.setAttribute('data-theme', 'dark');
            }
        }
        function toggleStep(headerElement) {
            const content = headerElement.nextElementSibling;
            const arrow = headerElement.querySelector('span:last-child');
            if (content.style.display === 'none') {
                content.style.display = 'block';
                arrow.innerText = '▼';
            } else {
                content.style.display = 'none';
                arrow.innerText = '►';
            }
        }
    </script>
</body>
</html>
"""

    base_name = os.path.splitext(os.path.basename(json_path))[0]
    output_filename = f"{base_name}_guide.html"
    with open(output_filename, "w", encoding="utf-8") as f:
        f.write(html_content)

    return os.path.abspath(output_filename)