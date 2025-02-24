"""
This script is used by Makefile to generate code from protobuf files.
"""
import glob
import os
import re
import shutil
from pathlib import Path

from grpc_tools import protoc
from importlib import metadata
grpc_tools_version = metadata.version('grpcio-tools')

DEST_FOLDER_NAME = 'generated'


def protos(src_dir: str) -> str:
    print(f'============================== Starting at src_dir: {src_dir}')
    if not os.path.exists(src_dir):
        print(
            f'src_dir `{src_dir}` does not exist in the current directory, '
            f'please run this script from the root directory of the project')

    for root, _, files in os.walk(src_dir):
        for file in files:
            if file.endswith('.proto'):
                file_path = os.path.normpath(os.path.join(root))
                yield file, file_path


def codegen(proto_location: str):
    out_path = os.path.normpath(os.path.join(proto_location, DEST_FOLDER_NAME))
    if not os.path.exists(out_path):
        os.mkdir(out_path)
    else:
        shutil.rmtree(out_path)
        os.mkdir(out_path)
    Path((os.path.join(out_path, '__init__.py'))).touch()
    protoc.main(['grpc_tools.protoc',
                 f'--proto_path={proto_location}',
                 f'--python_out={out_path}',
                 f'--grpc_python_out={out_path}',
                 f'--pyi_out={out_path}',
                 ] + list(glob.iglob(f'{proto_location}/*.proto')))

    search_path = os.path.join(out_path, '*.py')
    for py_file in glob.iglob(os.path.join(search_path)):
        Path(os.path.join(os.path.dirname(py_file), '__init__.py')).touch()
        with open(py_file, 'r+') as file:
            code = file.read()
            file.seek(0)
            replaced_inplace = re.sub(r'(\nimport) (.+_pb2.*)', 'from . import \\2', code)
            file.write(replaced_inplace)
            file.truncate()

def main():
    for proto_name, proto_path in protos(src_dir='baseline/proto'):
        if proto_name == 'empty.proto':
            print('Skipping `empty.proto` since its a hacky workaround for grpcio-tools')
            continue
        print(f'Resolving `{proto_name}` at `{proto_path}`')
        codegen(proto_location=proto_path)
    else:
        print('============================== Finished ==============================')


if __name__ == '__main__':
    main()
