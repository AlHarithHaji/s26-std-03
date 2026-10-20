from pathlib import Path

from exporters.txt_exporter import TXTExporter


def main():
    base_dir = Path(__file__).parent

    input_path = base_dir / "data" / "AirFryer_Philips_HD9252.json"
    output_path = base_dir / "output" / "AirFryer_Philips_HD9252.txt"

    exporter = TXTExporter()

    exporter.export(
        str(input_path),
        str(output_path)
    )


if __name__ == "__main__":
    main()