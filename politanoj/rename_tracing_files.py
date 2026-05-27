#!/usr/bin/env python3
import argparse
import os
import shutil


def strip_leading_zeros(filename: str) -> str:
    """Return filename with leading zeros removed from the stem."""
    stem, ext = os.path.splitext(filename)
    new_stem = stem.lstrip("0") or "0"
    return new_stem + ext


def copy_files_without_leading_zeros(input_dir: str, output_dir: str) -> None:
    if not os.path.isdir(input_dir):
        raise FileNotFoundError(f"Input directory not found: {input_dir}")

    os.makedirs(output_dir, exist_ok=True)
    seen = {}

    for entry in sorted(os.listdir(input_dir)):
        if not entry.lower().endswith(".txt"):
            continue

        src_path = os.path.join(input_dir, entry)
        if not os.path.isfile(src_path):
            continue

        target_name = strip_leading_zeros(entry)
        dst_path = os.path.join(output_dir, target_name)

        if target_name in seen:
            raise RuntimeError(
                f"Duplicate target filename after removing leading zeros: {target_name}\n"
                f"Conflicting sources: {seen[target_name]} and {src_path}"
            )

        shutil.copy2(src_path, dst_path)
        seen[target_name] = src_path
        print(f"Copied {src_path} -> {dst_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Copy tracing .txt files into a directory with leading zeros removed from filenames"
    )
    parser.add_argument(
        "--input_dir",
        required=True,
        help="Directory containing original .txt tracing files",
    )
    parser.add_argument(
        "--output_dir",
        required=True,
        help="Directory where renamed .txt files will be written",
    )
    args = parser.parse_args()

    copy_files_without_leading_zeros(args.input_dir, args.output_dir)
