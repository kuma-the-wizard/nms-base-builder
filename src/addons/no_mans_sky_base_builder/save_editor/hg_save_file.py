import os
import json
import struct
import lz4.block
from pathlib import Path
import shutil

MAGIC = 0xFEEDA1E5
CHUNK_SIZE = 0x80000  # 524288 bytes

class HGFile:
    def __init__(self, path):
        self.path = Path(path)
        self.json_data = None

    # LOAD HG FILE
    def load(self):
        with open(self.path, "rb") as f:
            raw = f.read()
        offset = 0
        decompressed = bytearray()
        while offset < len(raw):
            if offset + 16 > len(raw):
                raise ValueError("Invalid HG block header")
            magic, comp_size, decomp_size, _ = struct.unpack(  "<IIII", raw[offset:offset + 16])
            if magic != MAGIC:
                raise ValueError(f"Invalid magic at offset {offset}: {hex(magic)}")
            offset += 16
            comp_data = raw[offset:offset + comp_size]
            offset += comp_size
            chunk = lz4.block.decompress(comp_data,uncompressed_size=decomp_size)
            decompressed.extend(chunk)

        # FIND JSON SECTION

        data = bytes(decompressed)
        json_start = data.find(b'{')
        json_end = data.rfind(b'}')
        if json_start == -1 or json_end == -1:
            raise ValueError("Could not locate JSON data")
        json_bytes = data[json_start:json_end + 1]

        # safer decoding
        json_text = json_bytes.decode("utf-8", errors="replace")
        self.json_data = json.loads(json_text)
        return self.json_data
    
    # SAVE HG FILE
    def save(self, output_path=None):
        if self.json_data is None:
            raise ValueError("No JSON data loaded")

        output_path = output_path or self.path
        json_bytes = json.dumps(
            self.json_data,
            separators=(",", ":"),
            ensure_ascii=False
        ).encode("utf-8")

        blocks = []

        for i in range(0, len(json_bytes), CHUNK_SIZE):
            chunk = json_bytes[i:i + CHUNK_SIZE]
            compressed = lz4.block.compress( chunk, store_size=False)
            header = struct.pack(
                "<IIII",
                MAGIC,
                len(compressed),
                len(chunk),
                0
            )
            blocks.append(header + compressed)
        with open(output_path, "wb") as f:
            for block in blocks:
                f.write(block)
                
    def make_backup(self, output_path = None):
        path  = self.path
        folder = os.path.dirname(path)
        name, ext = os.path.splitext(os.path.basename(path))
        
        backup_folder = os.path.join(
            folder,"blender_backup"
        )
        os.makedirs(backup_folder, exist_ok=True)
        
        backup_file = os.path.join(
            backup_folder,
            f"{name}{ext}.blender.bak"
        )
        shutil.copy2(path, backup_file)

    # HELPER FUNCTIONS
    def export_json(self, path):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.json_data, f, indent=4)

    def import_json(self, path):
        with open(path, "r", encoding="utf-8") as f:
            self.json_data = json.load(f)