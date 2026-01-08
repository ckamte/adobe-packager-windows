"""
This is the downloader for required packages for Adobe Setup.

v 1.2.0
Change download type

v 1.1.0
Add support for Adobe CC 6.2.0.x

Download packages only!
"""

import os
import sys
import argparse
import zipfile

try:
    import requests
except ImportError:
    sys.exit(
        """You need requests module!
        install it from https://pypi.org/project/requests/
        or run: pip3 install requests."""
    )

try:
    from tqdm.auto import tqdm
except ImportError:
    sys.exit(
        """You need tqdm module!
        install it from https://pypi.org/project/tqdm/
        or run: pip3 install tqdm."""
    )

try:
    import pefile
except ImportError:
    sys.exit(
        """You need pefile module!
        install it from https://pypi.org/project/pefile/
        or run: pip3 install pefile."""
    )

SCRIPT_NAME = "Adobe Creative Cloud package downloader"
VERSION_STR = "1.2.0"

ADOBE_DL_HEADERS = {"User-Agent": "Creative Cloud"}

ACC_URL = "https://ccmdls.adobe.com/AdobeProducts/StandaloneBuilds/ACCC/ESD/{mainVer}/{buildVer}/{platform}/{fileName}"

CURR_PATH = os.path.dirname(os.path.abspath(__file__))

ADOBE_SETUP_BIN = os.path.join(CURR_PATH, "Set-up.exe")

session = requests.sessions.Session()


def show_info(name: str, version: str, pad: int, bdr: str) -> None:
    """Show script information"""
    tl = len(name) + (pad * 2)
    print(bdr * tl)
    print(bdr + name.center(tl - 2) + bdr)
    print(version.center(tl, bdr))


def extract_zip(zip):
    zipName = os.path.basename(zip)
    print(f"Extracting {zipName} contents")


def get_version():
    version = args.setupVersion

    if version is None:
        if not os.path.exists(ADOBE_SETUP_BIN):
            sys.exit("File not found")

        try:
            pe = pefile.PE(ADOBE_SETUP_BIN)
            if hasattr(pe, 'VS_FIXEDFILEINFO'):
                info = pe.VS_FIXEDFILEINFO[0]
                # Extracting version info
                major = info.FileVersionMS >> 16
                minor = info.FileVersionMS & 0xFFFF
                patch = info.FileVersionLS >> 16
                build = info.FileVersionLS & 0xFFFF
                version = f"{major}.{minor}.{patch}.{build}"

        except pefile.PEFormatError:
            sys.exit("Not a valid PE file (likely not a Windows executable)")
        except Exception as e:
            sys.exit(f"An error occurred: {e}")

    return version


def do_download(dFile, url):
    try:
        # get file size
        response = session.head(url, stream=False, headers=ADOBE_DL_HEADERS)
        lengthInBytes = int(response.headers.get("content-length", 0))

        if lengthInBytes < 2048:
            sys.exit(
                f"\nFound nothing for this version. Please try another version.")

        if (
            os.path.isfile(dFile)
            and os.path.getsize(dFile) == lengthInBytes
        ):
            print(f"\nDownloaded file seems OK, skipping...")
            return

        # download file
        response = session.get(url, stream=True, headers=ADOBE_DL_HEADERS)

        blockSize = 1024  # 1 Kilobyte
        with tqdm(total=lengthInBytes, unit="iB", unit_scale=True) as pBar:
            with open(dFile, "wb") as file:
                for data in response.iter_content(blockSize):
                    pBar.update(len(data))
                    file.write(data)
    except Exception as e:
        print(e)
        sys.exit("\nCannot download file!")


def accc_download():
    '''Download Adobe Creative Cloud package'''
    version = get_version()
    print(f"\nDownloading ACCC version: {version}")
    v = version.split(".")
    mainVer = ".".join([v[0], v[1], v[2]])
    buildVer = str(v[3])

    platform = args.platform or "win64"
    fileName = f"ACCCx{"_".join(v)}.zip"
    url = ACC_URL.format(
        mainVer=mainVer, buildVer=buildVer, platform=platform, fileName=fileName
    )

    tmpDir = os.path.join(CURR_PATH, "acc_tmp")
    os.makedirs(tmpDir, exist_ok=True)

    zipFile = os.path.join(tmpDir, fileName)

    do_download(zipFile, url)

    with zipfile.ZipFile(zipFile, 'r') as zr:
        for f in zr.infolist():
            if f.filename.startswith("packages") or f.filename.startswith("resources/AdobePIM.dll"):
                zr.extract(f, CURR_PATH)

    print("\nSuccessfully downloaded and extracted accc package data")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-v", "--setupVersion", help="Version for Set-up.exe", action="store"
    )
    parser.add_argument(
        "-p", "--platform", help="ACCC platform", action="store"
    )
    args = parser.parse_args()

    show_info(SCRIPT_NAME, VERSION_STR, 6, '=')

    accc_download()
