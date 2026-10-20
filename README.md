# PPTX Converter

This repository contains a PowerPoint export tool for the Futurdata disassembly guide.
The main converter code lives in `src/main/pptx-converter`, and the tests run from `src/tests`.

## What this project does

- Loads a normalized disassembly JSON model
- Validates the guide data
- Exports a PowerPoint presentation (`.pptx`) with steps, bill of materials, warnings, and images

## Repository structure

- `src/main/pptx-converter/`
  - `pptx_exporter.py` — public entry point for export functions
  - `pptx_core/` — internal exporter engine, models, validation, and registry
  - `data/` — sample JSON input files
  - `output/` — default export destination for local runs
- `src/tests/` — automated pytest regression tests

## Requirements

This project requires Python 3.11+ and the Python packages listed in:

- `src/main/pptx-converter/requirements.txt`

Install them with:

```powershell
cd "C:\Users\brahi\Downloads\s26-std-03-main\s26-std-03-main\src\main\pptx-converter"
python -m pip install -r requirements.txt
```

## How to run the converter

From the project root (`C:\Users\brahi\Downloads\s26-std-03-main\s26-std-03-main`), run:

```powershell
cd "C:\Users\brahi\Downloads\s26-std-03-main\s26-std-03-main\src\main\pptx-converter"
python pptx_exporter.py "data/example_air_fryer.json" "output/example_air_fryer.pptx"
```

Or run the wrapper script from the same folder:

```powershell
python main.py "data/example_air_fryer.json" "output/example_air_fryer.pptx"
```

### Example command

```powershell
python main.py "data/Nespresso.json" "output/Nespresso.pptx"
```

## How to run tests

From the repository root, run:

```powershell
cd "C:\Users\brahi\Downloads\s26-std-03-main\s26-std-03-main"
python -m pytest -q
```

This will execute the tests under `src/tests`.

## Notes

- The project uses a directory named `pptx-converter`, so some scripts add that folder directly to `sys.path`.
- Keep the converter directory structure in place when running the code.
