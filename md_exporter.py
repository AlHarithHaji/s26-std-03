import os
import sys
from disassembly_loader import build_guide

# Controllo degli argomenti in input
if len(sys.argv) < 2:
    print("Error: You have to pass the path of the json file you want to disassemble")
    print("Usage: python3 md-generator.py <filename>.json")
    sys.exit(1) 

json_path = sys.argv[1]

try:
    # Caricamento della guida forzando la creazione della BOM
    guide = build_guide(json_path, include_bom=True)
    
    # Preparazione del nome del file di output
    base_name = os.path.splitext(os.path.basename(json_path))[0]
    md_path = f"{base_name}.md"
    
    # Apriamo il file in scrittura (con encoding utf-8 per le emoji e i caratteri speciali)
    with open(md_path, "w", encoding="utf-8") as f:
        
        # === 1. TITOLO E METADATI (Product Card) ===
        f.write(f"# Disassembly Guide — {guide.product.name}\n\n")
        
        total_weight = guide.product.weight if guide.product.weight else 0
        steps_count = len(guide.steps)
        depth_str = str(guide.depth.value) if hasattr(guide, 'depth') and hasattr(guide.depth, 'value') else "full"
        
        
        
        f.write(f"**Total weight:** {total_weight} g · **Disassembly depth:** `{depth_str}` · **Steps:** {steps_count}\n\n")
        
        # === 2. VALIDATION WARNINGS ===
        if guide.warnings:
            f.write("<a id=\"warnings\"></a>\n")
            f.write("## ⚠ Validation warnings\n\n")
            for w in guide.warnings:
                f.write(f"> ⚠️ **{w.severity.upper()}** — `{w.rule}`: {w.message}\n\n")
        
        # === 3. BILL OF MATERIALS ===
        if hasattr(guide, 'bill_of_materials') and guide.bill_of_materials:
            f.write("<a id=\"bom\"></a>\n")
            f.write("## Bill of Materials\n\n")
            f.write("| Component | Weight | Material | Color |\n")
            f.write("| --- | --- | --- | --- |\n")
            
            for item in guide.bill_of_materials:
                # Formattazione pulita per evitare .0 sui pesi interi
                w_str = f"{int(item.weight) if isinstance(item.weight, float) and item.weight.is_integer() else item.weight} g" if item.weight is not None else "—"
                m_str = str(item.material) if item.material is not None else "—"
                col_str = str(item.color) if item.color is not None else "—"
                
                f.write(f"| {item.name} | {w_str} | {m_str} | {col_str} |\n")
            f.write("\n")
        
        # === 4. INDICE DEI CONTENUTI (Contents) ===
        f.write("## Contents\n\n")
        for step in guide.steps:
            f.write(f"{step.index}. [{step.operation}](#step-{step.index})\n")
        f.write("\n---\n\n")
        
        # === 5. CICLO DEGLI STEP ===
        for step in guide.steps:
            f.write(f"<a id=\"step-{step.index}\"></a>\n")
            f.write(f"## Step {step.index} — {step.operation}\n\n")
            
            # Attrezzi richiesti
            if step.tools_required:
                f.write(f"**Tools required:** {', '.join(step.tools_required)}\n\n")
            
            # Lista delle azioni
            if step.actions:
                for i, action in enumerate(step.actions, 1):
                    text = action.text
                    # Rilevamento automatico parole di pericolo
                    is_danger = any(word in text.upper() for word in ["ATTENZIONE", "PERICOLO", "WARNING", "CAUTION", "DANGER"])
                    
                    if is_danger:
                        f.write(f"{i}. ⚠️ **{text}**\n")
                    else:
                        f.write(f"{i}. {text}\n")
                f.write("\n")
                
            # Componenti estratti (Parts obtained)
            if step.outputs:
                f.write("### Parts obtained\n\n")
                for out in step.outputs:
                    details = []
                    if out.weight is not None:
                        details.append(f"{int(out.weight) if isinstance(out.weight, float) and out.weight.is_integer() else out.weight} g")
                    if out.material is not None:
                        details.append(str(out.material))
                    if out.color is not None:
                        details.append(str(out.color))
                        
                    detail_str = f" ({', '.join(details)})" if details else ""
                    f.write(f"- **{out.name}**{detail_str}\n")
                f.write("\n")
                
            # Logica di continuazione o fine ramo
            if step.continues_as:
                # Punta allo step successivo per la continuazione
                next_step_idx = step.index + 1
                f.write(f"➡️ Continue disassembling **{step.continues_as.name}** in [Step {next_step_idx}](#step-{next_step_idx})\n\n")
            else:
                f.write("🏁 *End of this disassembly branch.*\n\n")
            
            # Linea di separazione tra gli step
            f.write("---\n\n")
            
    print(f"Markdown (.md) file created: {os.path.abspath(md_path)}")

except Exception as e:
    print(f"Error: {e}")