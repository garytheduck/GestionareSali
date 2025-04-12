import os
import subprocess
import glob

# Creează directorul pentru imagini dacă nu există
output_dir = "diagrams/images"
os.makedirs(output_dir, exist_ok=True)

# Găsește toate fișierele .txt din directorul diagrams
diagram_files = glob.glob("diagrams/*.txt")

# Verifică dacă există fișiere de diagramă
if not diagram_files:
    print("Nu s-au găsit fișiere de diagramă în directorul 'diagrams/'")
    exit(1)

print(f"S-au găsit {len(diagram_files)} fișiere de diagramă.")

# Încearcă să ruleze PlantUML pentru fiecare fișier
for diagram_file in diagram_files:
    base_name = os.path.basename(diagram_file).replace('.txt', '')
    output_file = f"{output_dir}/{base_name}.png"
    
    print(f"Procesare {diagram_file} -> {output_file}")
    
    try:
        # Folosește comanda plantuml dacă este instalată global
        subprocess.run(["plantuml", "-tpng", "-o", f"../images", diagram_file], check=True)
        print(f"  ✓ Diagramă generată cu succes: {output_file}")
    except (subprocess.SubprocessError, FileNotFoundError):
        print(f"  ✗ Eroare la generarea diagramei. Asigură-te că PlantUML este instalat corect.")
        print("    Poți folosi extensia VS Code pentru a vizualiza și exporta diagramele manual.")

print("\nProcesare completă. Verifică directorul 'diagrams/images/' pentru diagramele generate.")
print("Alternativ, deschide fișierele .txt în VS Code și folosește extensia PlantUML pentru previzualizare.")
