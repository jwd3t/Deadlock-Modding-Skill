#!/usr/bin/env python3
"""
Standalone Source 2 VPK (v1) Packager for Valve's Deadlock.
Builds a valid pak01_dir.vpk from a directory without external dependencies.
"""

import os
import sys
import struct
import zlib
import zipfile
import argparse

def build_vpk(file_dict: dict[str, bytes], output_path: str):
    """
    Packages a dictionary of {internal_relative_path: file_bytes} into a valid Source 2 VPK v1.
    """
    tree = {}
    for path, data in file_dict.items():
        dirname, basename = os.path.split(path)
        name, ext = os.path.splitext(basename)
        ext = ext.lstrip('.')
        tree.setdefault(ext, {}).setdefault(dirname, {})[name] = data

    data_blobs = []
    current_offset = 0
    dir_entries = []

    for ext, dirs in tree.items():
        for dirname, files in dirs.items():
            for name, data in files.items():
                crc = zlib.crc32(data) & 0xffffffff
                length = len(data)
                dir_entries.append((ext, dirname, name, crc, current_offset, length))
                data_blobs.append(data)
                current_offset += length

    tree_bytes = bytearray()
    for ext, dirs in tree.items():
        tree_bytes.extend(ext.encode('utf-8') + b'\x00')
        for dirname, files in dirs.items():
            dir_str = dirname.replace('\\', '/') if dirname else ' '
            tree_bytes.extend(dir_str.encode('utf-8') + b'\x00')
            for name in files:
                for e in dir_entries:
                    if e[0] == ext and e[1] == dirname and e[2] == name:
                        tree_bytes.extend(name.encode('utf-8') + b'\x00')
                        tree_bytes.extend(struct.pack('<IHHIIH', e[3], 0, 0x7fff, e[4], e[5], 0xffff))
                        break
            tree_bytes.append(0)
        tree_bytes.append(0)
    tree_bytes.append(0)

    header = struct.pack('<III', 0x55aa1234, 1, len(tree_bytes))
    with open(output_path, 'wb') as f:
        f.write(header)
        f.write(tree_bytes)
        for blob in data_blobs:
            f.write(blob)

def pack_directory(source_dir: str, output_vpk: str, output_zip: str = None):
    if not os.path.isdir(source_dir):
        raise FileNotFoundError(f"Source directory not found: {source_dir}")

    files_to_pack = {}
    for root, _, files in os.walk(source_dir):
        for f in files:
            full_path = os.path.join(root, f)
            rel_path = os.path.relpath(full_path, source_dir).replace('\\', '/')
            with open(full_path, 'rb') as fp:
                files_to_pack[rel_path] = fp.read()

    os.makedirs(os.path.dirname(os.path.abspath(output_vpk)), exist_ok=True)
    build_vpk(files_to_pack, output_vpk)
    print(f"[OK] Generated VPK: {output_vpk} ({os.path.getsize(output_vpk)} bytes, {len(files_to_pack)} files)")

    if output_zip:
        os.makedirs(os.path.dirname(os.path.abspath(output_zip)), exist_ok=True)
        with zipfile.ZipFile(output_zip, 'w', zipfile.ZIP_DEFLATED) as z:
            z.write(output_vpk, arcname=os.path.basename(output_vpk))
        print(f"[OK] Generated ZIP for Deadlock Mod Manager: {output_zip} ({os.path.getsize(output_zip)} bytes)")

def main():
    parser = argparse.ArgumentParser(description="Standalone Source 2 VPK Packager for Deadlock Mods")
    parser.add_argument("source_dir", help="Path to the directory containing mod folders (materials, particles, sounds, etc.)")
    parser.add_argument("-o", "--output", default="pak01_dir.vpk", help="Output VPK file path (default: pak01_dir.vpk)")
    parser.add_argument("-z", "--zip", help="Optional output ZIP file for Deadlock Mod Manager")
    args = parser.parse_args()

    pack_directory(args.source_dir, args.output, args.zip)

if __name__ == "__main__":
    main()
