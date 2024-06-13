# STL
import os
import json
import argparse


def load(filename: str) -> dict[str, int]:
    with open(filename, "r") as f:
        content = f.read()
        data = json.loads(content)
    return data


def main(argv: argparse.Namespace):
    prim = load(argv.f1)
    sec = load(argv.f2)
    # prim = toki pona
    # sec = all

    for k, v in prim.items():
        if k in sec:
            ratio = (sec[k] - v) / sec[k]
            # all - toki pona / all
            print(f"{k}: {ratio:.3f}")


if __name__ == "__main__":

    def existing_directory(dir_path: str) -> str:
        if os.path.isdir(dir_path):
            return dir_path
        raise NotADirectoryError(dir_path)

    def existing_file(file_path: str) -> str:
        if os.path.isfile(file_path):
            return file_path
        raise FileNotFoundError(file_path)

    parser = argparse.ArgumentParser()

    _ = parser.add_argument(
        "--f1",
        help="primary file",
        dest="f1",
        required=True,
        type=existing_file,
    )
    _ = parser.add_argument(
        "--f2",
        help="secondary file",
        dest="f2",
        required=True,
        type=existing_file,
    )

    argv = parser.parse_args()

    main(argv)
