# PPTX Converter Reference Example

This directory contains the reference input and output for the Futurdata
JSON-to-PPTX converter.

- `example_air_fryer.json` is a normalized Loader IR source model.
- `example_air_fryer.pptx` is the editable PowerPoint generated from that JSON.

The implementation and operational README are located in:

```text
src/main/pptx-converter/
```

To regenerate the example from the repository root:

```powershell
python "src/main/pptx-converter/main.py"
```
