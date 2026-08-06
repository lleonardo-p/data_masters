#!/usr/bin/env python3

"""Baixa os arquivos oficiais de dengue e os converte para CSV Gzip."""

from __future__ import annotations

import argparse
import gzip
import os
import shutil
import time
import urllib.request
import zipfile
from pathlib import Path


BASE_URL = (
    "https://s3.sa-east-1.amazonaws.com/"
    "ckan.saude.gov.br/SINAN/Dengue/csv"
)
SOURCE_FILES = (
    "DENGBR24.csv.zip",
    "DENGBR25.csv.zip",
    "DENGBR26.csv.zip",
)
CHUNK_SIZE = 1024 * 1024
DOWNLOAD_ATTEMPTS = 3


def download_file(url: str, destination: Path) -> None:
    temporary_path = destination.with_name(f"{destination.name}.part")

    for attempt in range(1, DOWNLOAD_ATTEMPTS + 1):
        try:
            request = urllib.request.Request(
                url,
                headers={"User-Agent": "BAIP-source-installer/1.0"},
            )

            with urllib.request.urlopen(request, timeout=120) as response:
                expected_size = int(response.headers.get("Content-Length", 0))
                downloaded_size = 0

                with temporary_path.open("wb") as target:
                    while chunk := response.read(CHUNK_SIZE):
                        target.write(chunk)
                        downloaded_size += len(chunk)

            if expected_size and downloaded_size != expected_size:
                raise OSError(
                    "Download incompleto: "
                    f"esperado={expected_size}, recebido={downloaded_size}"
                )

            os.replace(temporary_path, destination)
            return
        except Exception:
            temporary_path.unlink(missing_ok=True)
            if attempt == DOWNLOAD_ATTEMPTS:
                raise
            time.sleep(2**attempt)


def csv_member(archive: zipfile.ZipFile, expected_name: str) -> str:
    members = [
        member
        for member in archive.namelist()
        if not member.endswith("/") and Path(member).suffix.lower() == ".csv"
    ]

    exact_matches = [
        member
        for member in members
        if Path(member).name.casefold() == expected_name.casefold()
    ]

    if exact_matches:
        return exact_matches[0]
    if len(members) == 1:
        return members[0]

    raise ValueError(
        f"O arquivo ZIP não contém um único CSV compatível com {expected_name}."
    )


def validate_archive(archive_path: Path, expected_name: str) -> str:
    with zipfile.ZipFile(archive_path) as archive:
        member = csv_member(archive, expected_name)
        if archive.getinfo(member).file_size == 0:
            raise ValueError(f"CSV vazio dentro de {archive_path.name}.")
        return member


def convert_archive(
    archive_path: Path,
    destination: Path,
    expected_name: str,
) -> None:
    temporary_path = destination.with_name(f"{destination.name}.part")

    try:
        with zipfile.ZipFile(archive_path) as archive:
            member = csv_member(archive, expected_name)
            with archive.open(member) as source:
                with temporary_path.open("wb") as compressed_file:
                    with gzip.GzipFile(
                        filename="",
                        mode="wb",
                        compresslevel=6,
                        fileobj=compressed_file,
                        mtime=0,
                    ) as target:
                        shutil.copyfileobj(source, target, length=CHUNK_SIZE)

        with gzip.open(temporary_path, "rb") as prepared_file:
            header = prepared_file.readline()

        if b"DT_NOTIFIC" not in header:
            raise ValueError(
                f"Cabeçalho inválido no arquivo convertido: {destination.name}"
            )

        os.replace(temporary_path, destination)
    except Exception:
        temporary_path.unlink(missing_ok=True)
        raise


def prepare_file(data_directory: Path, source_name: str) -> None:
    archive_path = data_directory / source_name
    csv_name = source_name.removesuffix(".zip")
    gzip_path = data_directory / f"{csv_name}.gz"
    source_url = f"{BASE_URL}/{source_name}"

    if not archive_path.exists():
        print(f"Baixando {source_name}...")
        download_file(source_url, archive_path)
    else:
        print(f"Download já existente: {archive_path.name}")

    member = validate_archive(archive_path, csv_name)
    print(f"Arquivo ZIP validado: {archive_path.name} ({member})")

    if not gzip_path.exists():
        print(f"Convertendo {archive_path.name} para {gzip_path.name}...")
        convert_archive(archive_path, gzip_path, csv_name)
    else:
        print(f"Arquivo preparado já existente: {gzip_path.name}")


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Baixa DENGBR24, DENGBR25 e DENGBR26 e converte os arquivos "
            "CSV ZIP para CSV Gzip."
        )
    )
    parser.add_argument(
        "--data-dir",
        type=Path,
        required=True,
        help="Diretório que receberá os arquivos da fonte.",
    )
    return parser.parse_args()


def main() -> None:
    arguments = parse_arguments()
    data_directory = arguments.data_dir.resolve()
    data_directory.mkdir(parents=True, exist_ok=True)

    for source_name in SOURCE_FILES:
        prepare_file(data_directory, source_name)

    print(f"Dados preparados em: {data_directory}")


if __name__ == "__main__":
    main()
