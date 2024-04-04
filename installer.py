import os
import io
import sys
import platform
import subprocess
import string
import json
import random
import zipfile
from xml.etree import ElementTree as ET

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

VERSION_STR = "1.0.0"

ACC_URL = "https://cdn-ffc.oobesaas.adobe.com/core/v1/applications?name=CreativeCloud&name=CCLBS&osVersion={osVersion}&platform={osPlatform}&version={appVersion}"

ADOBE_REQ_HEADERS = {
    "X-Adobe-App-Id": "accc-apps-panel-desktop",
    "User-Agent": "Adobe Application Manager 2.0",
    "X-Api-Key": "CC_HD_ESD_1_0",
    "Cookie": "fg="
    + "".join(random.choice(string.ascii_uppercase + string.digits) for _ in range(26))
    + "======",
}

ADOBE_DL_HEADERS = {"User-Agent": "Creative Cloud"}

CURR_PATH = os.path.dirname(os.path.abspath(__file__))

ADOBE_SETUP_BIN = os.path.join(CURR_PATH, "Set-up.exe")

session = requests.sessions.Session()


def setup_version():
    jsonFromPowerShell = subprocess.run(
        [
            "powershell.exe",
            "(Get-Item '"
            + ADOBE_SETUP_BIN
            + "').VersionInfo.FileVersion | ConvertTo-Json",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        shell=True,
    ).stdout
    return json.loads(jsonFromPowerShell)


def os_data():
    osVersionData = sys.getwindowsversion()
    osFullVer = "{}.{}.0.{}".format(
        osVersionData.major, osVersionData.minor, osVersionData.build
    )
    osVer = "{}.{}.0".format(osVersionData.major, osVersionData.minor)

    osPlatform = "win32"
    if platform.machine().endswith("64") == True:
        osPlatform = "win64"

    return osFullVer, osVer, osPlatform


def get_xml_data(url):
    response = session.get(url, stream=True, headers=ADOBE_REQ_HEADERS)
    response.encoding = "utf-8"
    return ET.fromstring(response.content)


def extract_zip(zip):
    zipName = os.path.basename(zip)
    print(f"Extracting {zipName} contents\n")
    fpath = os.path.dirname(zip)
    with zipfile.ZipFile(zip, "r") as cp:
        for f in cp.namelist():
            bname = os.path.basename(f)
            if bname is not "":
                fname = os.path.join(fpath, bname)
                unpacked = open(fname, "wb")
                unpacked.write(cp.read(f))
                unpacked.close()


def file_download(url, dest_dir):
    response = session.get(url, stream=True, headers=ADOBE_REQ_HEADERS)
    total_size_in_bytes = int(response.headers.get("content-length", 0))

    if total_size_in_bytes > 0:
        name = os.path.basename(url)
        dest_dir = os.path.join(dest_dir, name)

        if (
            os.path.isfile(dest_dir)
            and os.path.getsize(dest_dir) == total_size_in_bytes
        ):
            extract_zip(dest_dir)
            print("Downloaded file is OK. Skipping ...")
            return

        block_size = 1024  # 1 Kibibyte
        progress_bar = tqdm(total=total_size_in_bytes, unit="iB", unit_scale=True)
        with open(dest_dir, "wb") as file:
            for data in response.iter_content(block_size):
                progress_bar.update(len(data))
                file.write(data)
        progress_bar.close()
        if total_size_in_bytes != 0 and progress_bar.n != total_size_in_bytes:
            print("ERROR, something went wrong")

        extract_zip(dest_dir)


def get_packages():
    setupVersion = setup_version()

    print("\nGet Required packages for Adobe Installer v-{}".format(setupVersion))

    winFullVer, winVer, winPlatform = os_data()
    acc_xml_url = ACC_URL.format(
        osVersion=winFullVer, osPlatform=winPlatform, appVersion=setupVersion
    )

    xml_data = get_xml_data(acc_xml_url)

    accVersion = xml_data.find(".//application/version").text

    if accVersion != setupVersion:
        print(
            "\nYour installer will not work! Please try Adobe Installer version 5x or 6x\n"
        )
        exit(1)

    package_cdn = xml_data.find(".//cdn/secure").text
    packageSets = xml_data.findall(".//packageSets/packageSet")

    # sort by packageSet name
    packageSets[:] = sorted(
        packageSets, key=lambda packageSets: packageSets.findtext("sequenceNumber")
    )

    # appinfo data
    xml_root = ET.Element("application")

    for key, val in dict(
        {
            "name": xml_data.find(".//application/name").text,
            "platform": xml_data.find(".//application/platform").text,
            "lbsurl": "http://ccmdl.adobe.com/AdobeProducts/KCCC/1/win32/CreativeCloudSet-Up.exe",
        }
    ).items():
        child = ET.Element(key)
        child.text = str(val)
        xml_root.append(child)

    xml_packagesets = ET.SubElement(xml_root, "packageSets")

    # create packages dir
    packages_dir = os.path.join(CURR_PATH, "packages")
    os.makedirs(packages_dir, exist_ok=True)

    for set in packageSets:
        setName = set.find("name").text

        installPath = set.find("installPath").text
        if installPath == "[NOT-USED]":
            continue

        xml_packageSet = ET.SubElement(xml_packagesets, "packageSet")
        for key, val in dict(
            {
                "name": setName,
                "installPath": installPath,
                "sequenceNumber": set.find("sequenceNumber").text,
            }
        ).items():
            child = ET.Element(key)
            child.text = str(val)
            xml_packageSet.append(child)

        # create package
        pkg_dir = os.path.join(packages_dir, setName)
        os.makedirs(pkg_dir, exist_ok=True)
        packages = set.findall(".//packages/package")

        # sort by packageSet name
        packages[:] = sorted(
            packages, key=lambda packages: int(packages.findtext("sequenceNumber"))
        )

        xml_packages = ET.SubElement(xml_packageSet, "packages")
        for pk in packages:
            packageName = pk.find("name").text
            manifestUrl = pk.find("manifestUrl").text
            manifestXml = get_xml_data(package_cdn + manifestUrl)

            # download sub package
            sub_pkg_dir = os.path.join(pkg_dir, packageName)
            os.makedirs(sub_pkg_dir, exist_ok=True)
            assets = manifestXml.find(".//asset_list/asset/asset_path").text
            print("\nDownloading package: " + packageName)
            file_download(assets, sub_pkg_dir)

            xml_package = ET.SubElement(xml_packages, "package")
            for key, val in dict(
                {
                    "name": packageName,
                    "sequenceNumber": pk.find("sequenceNumber").text,
                    "optional": pk.find("optional").text,
                    "pimxPath": "/"
                    + "/".join([setName, packageName, packageName + ".pimx"]),
                }
            ).items():
                child = ET.Element(key)
                child.text = str(val)
                xml_package.append(child)

            if pk.find("additionalInfo") is not None:
                adInfo = pk.find("additionalInfo")
                xml_pkg_adn = ET.SubElement(xml_package, "additionalInfo")
                for elem in adInfo:
                    xml_pkg_adn.append(elem)

        xml_filters = ET.SubElement(xml_packageSet, "filters")
        xml_filter = ET.SubElement(xml_filters, "filter")
        xml_filter.set("type", "operatingSystem")
        xml_filter_config = ET.SubElement(xml_filter, "config")
        xml_filter_config.text = winVer

        if set.find("additionalInfo") is not None:
            adInfo = set.find("additionalInfo")
            xml_pkgSet_adn = ET.SubElement(xml_packageSet, "additionalInfo")
            for elem in adInfo:
                xml_pkgSet_adn.append(elem)

    pkg_version = ET.SubElement(xml_root, "version")
    pkg_version.text = xml_data.find(".//application/version").text

    print("\nCreating ApplicationInfo.xml")
    tree = ET.ElementTree(xml_root)
    ET.indent(tree, space="    ", level=0)
    xml_file = os.path.join(packages_dir, "ApplicationInfo.xml")
    tree.write(xml_file, encoding="utf-8", xml_declaration=True)

    get_pim_dll(packages_dir)


def get_pim_dll(packages_dir):
    print("\nGetting AdobePIM.dll")
    res_dir = "resources"
    os.makedirs(res_dir, exist_ok=True)

    core_package = os.path.join(packages_dir, "ADC", "Core", "Core.zip")
    with zipfile.ZipFile(core_package, "r") as cp:
        for file in cp.namelist():
            if file.endswith("AdobePIM.dll"):
                cp.extract(file, res_dir)
            elif file.endswith("Core.pima"):
                pimaData = io.BytesIO(cp.read(file))
                with zipfile.ZipFile(pimaData) as pima:
                    for pim in pima.namelist():
                        if pim.endswith("AdobePIM.dll"):
                            pima.extract(pim, res_dir)


if __name__ == "__main__":
    ye = int((32 - len(VERSION_STR)) / 2)
    print("=================================")
    print("=     Build Adobe Installer     =")
    print(
        "{} {} {}\n".format("=" * ye, VERSION_STR, "=" * (31 - len(VERSION_STR) - ye))
    )

    get_packages()

    print("\nSuccessfully downloaded installer files\n")
