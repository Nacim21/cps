"""Compile and execute actual MatIEC-generated ST using a built OpenPLC checkout."""
import argparse
from pathlib import Path
import subprocess
import tempfile

root = Path(__file__).resolve().parents[1]
p = argparse.ArgumentParser()
p.add_argument('--openplc-source', type=Path, required=True)
a = p.parse_args()
source = a.openplc_source.resolve()
compiler = source / 'utils/matiec_src/iec2c'
with tempfile.TemporaryDirectory(prefix='spillway-st-') as directory:
    out = Path(directory)
    subprocess.run([str(compiler), '-I', str(source/'webserver/lib'), '-T', str(out),
                    '-f', '-l', '-p', '-r', '-R', '-a', str(root/'plc/spillway.st')], check=True)
    subprocess.run(['g++', '-std=gnu++11', '-O2', '-w', '-Wno-narrowing', '-include', 'sys/types.h', '-I', str(source/'webserver/core/lib'),
                    '-I', str(out), str(out/'Config0.c'), str(out/'Res0.c'),
                    str(root/'tests/st_harness.cpp'), '-o', str(out/'st-check')], check=True)
    subprocess.run([str(out/'st-check')], check=True)
