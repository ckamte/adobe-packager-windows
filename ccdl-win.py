"""
This is the Adobe Offline Package downloader for Windows.

Download package only! (except acrobat pro) Installer not included

Based on https://github.com/Drovosek01/adobe-packager
"""

import os
import io
import string
import random
import argparse
import json
import locale
import ctypes
import sys
import operator
from pathlib import Path
from collections import OrderedDict
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


SCRIPT_NAME = "Adobe CC Packages Downloader For Windows"
VERSION_STR = "1.2.1"
CODE_QUALITY = "Really_AWFUL"

ADOBE_PRODUCTS_XML_URL = "https://prod-rel-ffc-ccm.oobesaas.adobe.com/adobe-ffc-external/core/v{urlVersion}/products/all?channel=ccm&channel=sti&platform={reqPlatforms}&productType=Desktop&_type=xml"
ADOBE_APPLICATION_JSON_URL = "https://cdn-ffc.oobesaas.adobe.com/core/v3/applications"

ADOBE_REQ_HEADERS = {
    "X-Adobe-App-Id": "accc-hdcore-desktop",
    "User-Agent": "Adobe Application Manager 2.0",
    "X-Api-Key": "CC_HD_ESD_1_0",
    "Cookie": "fg="
    + "".join(random.choice(string.ascii_uppercase + string.digits)
              for _ in range(26))
    + "======",
}

ADOBE_DL_HEADERS = {"User-Agent": "Creative Cloud"}

session = requests.sessions.Session()


def show_info(name: str, version: str, pad: int, bdr: str) -> None:
    """Show script information"""
    tl = len(name) + (pad * 2)
    print(bdr * tl)
    print(bdr + name.center(tl - 2) + bdr)
    print(version.center(tl, bdr))


def get_arguments() -> argparse.Namespace:
    """Get command-line parameters"""
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-l", "--installLanguage", help="Language code (eg. en_US). For more than one language us comma to separate languages", action="store"
    )
    parser.add_argument(
        "-o", "--osLanguage", help="OS Language code (eg. en_US)", action="store"
    )
    parser.add_argument(
        "-p", "--appPlatform", help="Application platform (eg. win64)", action="store"
    )
    parser.add_argument(
        "-s",
        "--sapCode",
        help="SAP code for desired product (eg. PHSP). For batch download use comma to separate products",
        action="store",
    )
    parser.add_argument(
        "-v",
        "--version",
        help="Version of desired product (eg. 21.0.3)",
        action="store",
    )
    parser.add_argument(
        "-d",
        "--destination",
        help="Directory to download installation files to",
        action="store",
    )
    parser.add_argument(
        "-u",
        "--urlVersion",
        help="Get app info from v4/v5/v6 url (eg. v6)",
        action="store",
    )
    parser.add_argument(
        "-A",
        "--Auth",
        help="Add a bearer_token to to authenticate your account, e.g. downloading Xd",
        action="store",
    )
    parser.add_argument(
        "-n",
        "--noRepeatPrompt",
        help="Don't prompt for additional downloads",
        action="store_true",
    )
    parser.add_argument(
        "-i",
        "--productIcons",
        help="Get app icons",
        action="store_true",
    )
    parser.add_argument(
        "-x",
        "--skipExisting",
        help="Skip existing files, e.g. resuming failed downloads",
        action="store_true",
    )
    return parser.parse_args()


def questiony(question: str) -> bool:
    """Question prompt default Y."""
    reply = None
    while reply not in ("", "y", "n"):
        reply = input(f"{question} (Y/n): ").lower()
    return reply in ("", "y")


def get_winver() -> str:
    winVer = sys.getwindowsversion()
    return "{}.{}.{}".format(winVer.major, winVer.minor, winVer.build)


def set_url_version(args: argparse.Namespace) -> str:
    """Set url version for downloading ffc.xml"""
    urlVersion = None
    acceptVers = ["v4", "v5", "v6", "4", "5", "6"]

    if args.urlVersion:
        if args.urlVersion.lower() in acceptVers:
            urlVersion = args.urlVersion[-1]
            print(f"\nUsing provided url version: {urlVersion}")
        else:
            print(
                f'Invalid argument "{args.urlVersion}" for URL version! Please select from version list below\n'
            )
            urlVersion = None

    while not urlVersion:
        versions = {
            "v4": "URL version 4",
            "v5": "URL version 5",
            "v6": "URL version 6",
        }
        print("Available URL versions")
        for p, v in versions.items():
            print("[{}]{}{}".format(p, (12 - len(p)) * " ", v))

        usrInput = (
            input(
                "\nPlease enter the URL version(v4/v5/v6), or nothing for v6: "
            )
            or "v6"
        )
        if usrInput in acceptVers:
            urlVersion = usrInput[-1]
        else:
            print(f"Invalid URL version: {usrInput}")

    return urlVersion


def set_app_platform(args: argparse.Namespace) -> str:
    """Set application platform"""
    winPlatforms = {
        "win32": "32 Bit Windows",
        "win64": "64 Bit Windows",
        "winarm64": "Windows ARM",
    }
    appPlatform = None
    if args.appPlatform:
        if args.appPlatform in winPlatforms:
            appPlatform = args.appPlatform
            print(f"\nUsing provided windows platform: {appPlatform}")
        else:
            print(
                f"Invalid windows platform [{args.appPlatform}]! Please select form list below\n"
            )
            appPlatform = None

    while not appPlatform:
        print("Available Platforms")
        for p, v in winPlatforms.items():
            print("[{}]{}{}".format(p, (12 - len(p)) * " ", v))

        val = (
            input(
                "\nPlease enter application platform (eg win32), or nothing for win64: "
            )
            or "win64"
        )
        if val in winPlatforms:
            appPlatform = val
        else:
            print(f"Invalid platform: {val}\n")

    return appPlatform


def set_config() -> dict:
    """Set configuration data from arguments"""
    # get arguments
    args = get_arguments()

    reqUrlVer = set_url_version(args)
    reqAppPlatform = set_app_platform(args)
    print(
        f"\nPrepare to download {reqAppPlatform} products form url version {reqUrlVer}")

    if args.Auth:
        ADOBE_REQ_HEADERS["Authorization"] = args.Auth

    allowedPlatforms = [reqAppPlatform]
    urlPlatforms = reqAppPlatform
    if reqAppPlatform == "win64":
        allowedPlatforms.append("win32")
        urlPlatforms += ",win32"

    # destination dir
    if args.destination:
        print(f"\nUsing provided destination: {args.destination}")
        dest = args.destination
    else:
        dest = os.path.dirname(os.path.realpath(__name__))

    # create products directory
    prodDir = os.path.join(dest, "products")
    os.makedirs(prodDir, exist_ok=True)

    winver = get_winver()
    print(f"\nSet windows version to {winver}. You may not install or run products on Windows version below: {winver}!")

    print(f"\nDownloaded files will be saved in: {prodDir}")

    return {
        "reqUrlVer": reqUrlVer,
        'urlPlatforms': urlPlatforms,
        "reqAppPlatform": reqAppPlatform,
        "allowedPlatforms": allowedPlatforms,
        "downIcons": args.productIcons,
        "noRepeat": args.noRepeatPrompt,
        "osLang": args.osLanguage,
        "reqLang": args.installLanguage,
        "toDown": args.sapCode,
        "reqVer": args.version,
        "productDir": prodDir,
        "skip": args.skipExisting,
        "osVersion": winver
    }


def create_xml(name: str, data) -> None:
    """Write data to xml file"""
    with open(name, "wb+") as f:
        f.write(data)


def create_json(name: str, data) -> None:
    """Write data to json file"""
    with open(name, "w") as f:
        json.dump(data, f)


def append_file(name: str, data: str | None) -> None:
    """Append data to existing file"""
    with open(name, "a+", encoding='utf-8') as f:
        if data is not None:
            f.write(data + "\n")


def download_data(url: str, header: dict) -> bytes:
    """Get raw data"""
    try:
        response = session.get(url, stream=True, headers=header)
        response.encoding = "utf-8"
        response.raise_for_status()

        total_size = int(response.headers.get("content-length", 0))
        chunk_size = 1024  # 1 KB chunks
        mem_file = io.BytesIO()
        with tqdm(total=total_size or None, unit="B", unit_scale=True, unit_divisor=1024) as pbar:
            for chunk in response.iter_content(chunk_size=chunk_size):
                mem_file.write(chunk)
                pbar.update(len(chunk))

        downData = mem_file.getvalue()
        mem_file.close()

    except requests.exceptions.HTTPError as err_h:
        print(f"Connection error occurred: {err_h}")

    except requests.exceptions.RequestException as err_r:
        print(f"Unexpected error occurred: {err_r}")

    else:
        return downData

    # exit on download error
    sys.exit("\nCannot download data!")


def download_json(url: str, header: dict, file: str | None = None) -> dict:
    """Download json data(use filename for testing)"""
    if file and Path(file).is_file():
        with open(file, "r") as f:
            return json.load(f)

    jsonData = download_data(url, header)

    if file:
        create_json(file, json.loads(jsonData.decode('utf-8')))

    return json.loads(jsonData.decode('utf-8'))


def download_xml(url: str, header: dict, file=None) -> ET.ElementTree:
    """Download xml data(use filename for testing)"""
    if file and Path(file).is_file():
        return ET.parse(file)

    xmlData = download_data(url, header)

    if file:
        create_xml(file, xmlData)

    return ET.fromstring(xmlData)


def product_icons(elem: dict) -> list[str]:
    """Get icons for product"""
    productIcons = []
    if len(elem.find("productIcons")):
        for icon in elem.findall("productIcons/icon"):
            productIcons.append(icon.text)
    return productIcons


def product_languages(elem: dict) -> list[str]:
    """Get supported language for product"""
    supportedLang = []
    if len(elem.find("locales")):
        for locale in elem.findall("locales/locale"):
            supportedLang.append(locale.get("name"))
    return supportedLang


def get_products(cfg: dict) -> dict:
    """Get all product and dependencies list"""
    # get products.xml
    products_xml_url = ADOBE_PRODUCTS_XML_URL.format(
        urlVersion=cfg["reqUrlVer"], reqPlatforms=cfg["urlPlatforms"]
    )

    print("\nDownloading all available products...")
    productXml = download_xml(products_xml_url, ADOBE_REQ_HEADERS)

    # add cdn address to config
    cfg['cdn'] = productXml.find(".//*/cdn/secure").text

    # parse xml data
    allProducts = {}
    for channel in productXml.findall(".//channel"):
        appType = "dep"
        if channel.attrib["name"] == "ccm":
            appType = "app"

        for product in channel.findall("./products/product"):
            sapCode = product.get("id")
            displayName = product.find("displayName").text
            for plat in [
                item
                for item in product.findall("./platforms/platform")
                if item.attrib["id"] in cfg["allowedPlatforms"]
            ]:
                appPlatform = plat.attrib["id"]
                # platform filter for main app
                if appType == "app" and appPlatform != cfg["reqAppPlatform"]:
                    continue

                if plat.findall(
                    "./languageSet[@packageType='hdPackage']"
                ) or plat.findall("./languageSet[@packageType='application']"):
                    if not allProducts.get(sapCode):
                        allProducts[sapCode] = {
                            "appType": appType,
                            "displayName": displayName,
                            "sapCode": sapCode,
                            "versions": OrderedDict(),
                        }

                    for ls in plat.findall("languageSet"):
                        languageSet = ls.attrib
                        productVersion = languageSet.get("productVersion")

                        manifestURL = ls.find(".//manifestURL")
                        if manifestURL is not None:
                            manifestURL = manifestURL.text

                        if (
                            productVersion is None
                            and ls.find(".//appVersion") is not None
                        ):
                            productVersion = ls.find(".//appVersion").text

                        # get product with version
                        if productVersion is not None:
                            allProducts[sapCode]["versions"][productVersion] = {
                                "sapCode": sapCode,
                                "displayName": displayName,
                                "appPlatform": appPlatform,
                                "productVersion": productVersion,
                                "supportedLanguages": product_languages(ls),
                                "buildGuid": languageSet.get("buildGuid"),
                                "manifestURL": manifestURL,
                            }
                            if cfg["downIcons"]:
                                allProducts[sapCode]["versions"][productVersion]['productIcons'] = product_icons(
                                    product)
                        else:
                            if int(cfg["reqUrlVer"]) >= 5:
                                allProducts.pop(sapCode, None)

    return allProducts


def select_product(allProducts: dict) -> str:
    """Select a product to down"""
    selectedProduct = None
    while selectedProduct is None:
        show_avail_products(allProducts)
        val = input(
            "\nPlease enter SAP Code for desired product: "
        ).upper()
        if allProducts.get(val):
            selectedProduct = val
        else:
            v = val or "empty"
            print(
                f"[{v}] is not available! Please use a value from the list below."
            )
    return selectedProduct


def get_last_version(versions: dict) -> str:
    """Ge last version of selected product"""
    last = None
    for v in reversed(versions.values()):
        if v["buildGuid"] is not None or v["manifestURL"] is not None:
            last = v["productVersion"]
        else:
            print("\nCannot determine latest version!\n")
    return last


def show_avail_products(allProducts: dict) -> None:
    """Show available products list"""
    availCodes = {}
    for p in allProducts.values():
        if p["appType"] == "app":
            versions = p["versions"]
            if get_last_version(versions):
                availCodes[p["sapCode"]] = p["displayName"]
    # print(f"{str(len(availCodes))} products found.")

    print("\n" + ("-" * 40))
    print("Available products and codes")
    print("-" * 40)
    for s, d in availCodes.items():
        print("[{}]{}{}".format(s, (10 - len(s)) * " ", d))


def download_list(allProducts: dict) -> list[str]:
    """Create products to download list"""
    codeList = []
    toDown = cfg["toDown"]
    # for batch download
    if toDown:
        toDown = toDown.upper().split(',')
        for prodToDown in toDown:
            if prodToDown in allProducts:
                print(f"\nAdd {prodToDown} to download list")
                codeList.append(prodToDown)

            else:
                print(f"\n{prodToDown} is not available!\n")
                answer = None
                while answer is None:
                    answer = input("Are you want to continue? (y/n): ")
                    if answer.lower() in ["y", "yes"]:
                        answer = select_product(allProducts)
                        # for duplicate entry
                        while answer in codeList:
                            print(
                                f"\nAdd [{answer}] already exist in download list")
                            answer = input(
                                "\nPlease enter the SAP Code of the desired product from the list above: "
                            ).upper()
                        else:
                            print(f"\nAdd [{answer}] to download list")
                            codeList.append(answer)
                    elif answer.lower() in ["n", "no"]:
                        print("\nBye!")
                        sys.exit()
                    else:
                        print("\nPlease enter yes or no!")
                        answer = None

    else:
        toDown = select_product(allProducts)
        codeList.append(toDown)

    return codeList


def select_app_version(product: dict, batch: bool) -> str:
    """Select version for product"""
    availVer = product["versions"]
    version = None
    if batch:
        version = get_last_version(availVer)
    elif cfg["reqVer"]:
        reqVersion = cfg["reqVer"]
        if availVer.get(reqVersion):
            print(f"\nUsing provided version: {reqVersion}")
            version = reqVersion
        else:
            print(f"\nProvided version not found: {reqVersion}")

    if not version:
        lastVersion = None
        print("\nAvailable versions list")
        for v in reversed(availVer.values()):
            if v["buildGuid"] is not None or v["manifestURL"] is not None:
                print(
                    "{} for {} - {}".format(
                        product["displayName"], v["appPlatform"], v["productVersion"]
                    )
                )
                lastVersion = v["productVersion"]

        while version is None:
            val = (
                input(
                    f"\nPlease enter the desired version. Nothing for [{lastVersion}]:"
                )
                or lastVersion
            )
            if availVer.get(val):
                version = val
            else:
                print(
                    f"{val} is not a valid version. Please use a value from the list above."
                )

    print(
        "\nPrepare to download Adobe {}, version {}".format(
            product["displayName"], version
        )
    )

    return availVer[version]


def select_language(appLangs: list, defLang: str) -> str:
    """Select language for product"""
    print("\nAvailable languages: {}".format(", ".join(appLangs)))
    selLang = None
    while selLang is None:
        val = (
            input(
                f"\nPlease enter the desired install language, or nothing for [{defLang}]: "
            )
            or defLang
        )
        if len(val) == 5:
            val = val[0:2].lower() + val[2] + val[3:5].upper()

        if val in appLangs:
            selLang = val
        else:
            print(
                f"{val} is not available. Please use a value from the list above."
            )

    if selLang.lower() == "all":
        selLang = "mul"

    return selLang


def install_language(appLangs: list[str]) -> list[str]:
    """Set language for product"""
    if "mul" in appLangs:
        appLangs[appLangs.index("mul")] = "all"
    else:
        if "all" not in appLangs:
            appLangs.append("all")
    appLangs.sort()

    osLang = cfg["osLang"]
    if osLang is None:
        # Detecting current language.
        windll = ctypes.windll.kernel32
        osLang = locale.windows_locale[windll.GetUserDefaultUILanguage()]

    # if os language in supported languages
    defLang = "all"
    if osLang in appLangs:
        defLang = osLang

    installLanguage = []
    if cfg["reqLang"]:
        # all means all
        if "all" in cfg["reqLang"]:
            cfg["reqLang"] = "all"

        reqLangs = cfg["reqLang"].split(",")
        for l in reqLangs:
            if l in appLangs:
                print(f"\nAdding provided language: {l}")
                installLanguage.append(l)
            else:
                print(f"\nProvided language not available: {l}")
                if len(appLangs) == 1:
                    print(f"\nSet language to available language {appLangs[0]}")
                    installLanguage = appLangs
                    break

                if questiony("\nDo you want to select another language?"):
                    newLang = select_language(appLangs, defLang)
                    # all (mul) means all languages
                    if newLang == "mul" or newLang == "all":
                        installLanguage = ["all"]
                        break

                    while newLang in installLanguage:
                        print(f"\n{newLang} already exist in your list!")
                        newLang = select_language(appLangs, defLang)

                    installLanguage.append(newLang)

        if installLanguage == []:
            if questiony("\nNo language selected. Do you want to quit?"):
                sys.exit("Bye!")
        # update configuration
        # cfg["reqLang"] = installLanguage

    else:
        installLanguage = [select_language(appLangs, defLang)]

    return installLanguage


def download_file(url: str, dest: str, prefix=None) -> bool:
    """Download package file"""
    filename = os.path.basename(url)
    if prefix:
        filename = prefix + filename

    destDir = os.path.join(dest, filename)

    try:
        # get file size
        response = session.head(url, stream=False, headers=ADOBE_DL_HEADERS)
        lengthInBytes = int(response.headers.get("content-length", 0))

        if (
            cfg["skip"]
            and os.path.isfile(destDir)
            and os.path.getsize(destDir) == lengthInBytes
        ):
            print(f"\nDownloaded file seems OK, skipping...")
            return True

        # download file
        response = session.get(url, stream=True, headers=ADOBE_REQ_HEADERS)

        blockSize = 1024  # 1 Kilobyte
        with tqdm(total=lengthInBytes, unit="iB", unit_scale=True) as pBar:
            with open(destDir, "wb") as file:
                for data in response.iter_content(blockSize):
                    pBar.update(len(data))
                    file.write(data)
    except Exception as e:
        print(f"An unexpected error occurred! {e}")
    else:
        return True

    return False


def download_icons(prodInfo: list) -> None:
    """Download product icons"""
    print("\nDownloading product icons...\n")

    iconsDir = os.path.join(cfg["productDir"], "icons")
    os.makedirs(iconsDir, exist_ok=True)

    icons = prodInfo["productIcons"]
    prefix = prodInfo["sapCode"].lower()

    for url in icons:
        download_file(url, iconsDir, prefix)


def language_filter(pkgJson: dict | list, language: list) -> dict:
    """Stripped out unnecessary data from json file"""
    # Source - # https://stackoverflow.com/questions/71543579/python-find-and-replace-all-values-under-a-certain-key-in-a-nested-dictionary
    # Posted by flakes
    # Retrieved 2025-12-03, License - CC BY-SA 4.0
    if "mul" in language or "all" in language:
        return pkgJson

    if isinstance(pkgJson, dict):
        key = "Language"
        # filter by locale
        for k, v in pkgJson.items():
            filtered = None
            if k == key:
                filtered = []
                for lc in v:
                    if lc["locale"] in language or lc["locale"] == "mul":
                        filtered.append(lc)

        # replace with filtered result
        pkgJson = {
            k: filtered if k == key and v else language_filter(v, language)
            for k, v in pkgJson.items()
        }

    if isinstance(pkgJson, list):
        pkgJson = [language_filter(v, language) for v in pkgJson]

    return pkgJson


def do_test(cond: str, key: str | list[str]) -> bool:
    """Test condition based on condition strings"""
    if "==" in cond:
        val = cond.split("==")
        opt = operator.eq
    elif "!=" in cond:
        val = cond.split("!=")
        opt = operator.ne
    elif "<=" in cond:
        val = cond.split("<=")
        opt = operator.le
    elif ">=" in cond:
        val = cond.split(">=")
        opt = operator.ge
    elif ">" in cond:
        val = cond.split(">")
        opt = operator.gt
    elif "<" in cond:
        val = cond.split("<")
        opt = operator.lt
    else:
        return True

    # stripped string
    cmp = val[1].strip()

    if "OSVersion" in val[0]:
        keys = key.split(".")
        cmps = cmp.split(".")
        idx = -1
        for c in cmps:
            idx = idx + 1
            if (idx > 0):
                c = float(f"0.{c}")
                k = float(f"0.{keys[idx]}")
            else:
                c = int(c)
                k = int(keys[idx])
            
            if opt(k, c) is not True:
                return False

    if isinstance(key, list):
        return cmp in key

    return opt(key, cmp)


def test_and(str: str, osProc: str, osver: str, langs: list[str]) -> bool:
    """Check AND (&&) test result"""
    conds = str.split("&&")
    for c in conds:
        if "OSProcessorFamily" in c:
            if do_test(c, osProc) is not True:
                return False

        if "OSVersion" in c:
            if do_test(c, osver) is not True:
                return False

        if "installLanguage" in c:
            if "all" in langs:
                return True

            if do_test(c, langs) is not True:
                return False

    return True


def test_or(str: str, osProc: str, osver: str, langs: list[str]) -> bool:
    """Check OR (||) test result"""
    conds = str.split("||")
    for c in conds:
        if "OSProcessorFamily" in c:
            if do_test(c, osProc) is True:
                return True

        if "OSVersion" in c:
            if do_test(c, osver) is True:
                return True

        if "installLanguage" in c:
            if "all" in langs:
                return True

            if do_test(c, langs) is True:
                return True

    return False


def condition_filter(pkgJson: dict, langs: list[str]) -> dict:
    """Filter packages by condition statements"""
    osver = cfg["osVersion"]
    osProc = "64-bit"
    if cfg["reqAppPlatform"] == "win32":
        osProc = "32-bit"

    packages = pkgJson["Packages"]["Package"]

    newPkgs = []
    for pkg in packages:
        # append_file("conditions.txt", pkg.get("Condition"))
        # continue

        if "Condition" in pkg:
            conds = pkg.get("Condition")
            if "||" in conds:
                if test_or(conds, osProc, osver, langs) == True:
                    newPkgs.append(pkg)
            else:
                if test_and(conds, osProc, osver, langs) == True:
                    newPkgs.append(pkg)

        # premiere pro
        elif "-esl_lp_" in pkg["PackageName"]:
            app, pproLang = pkg["PackageName"].split("-")
            pproLang = pproLang.replace("esl_lp_", "")
            for l in langs:
                if l == "all" or l == "mul":
                    continue
                main, locale = l.split("_")
                if main == pproLang:
                    newPkgs.append(pkg)
                # for china languages
                if main == "zh":
                    if pproLang == "cmn" or pproLang == "yue":
                        newPkgs.append(pkg)

        else:
            newPkgs.append(pkg)

    pkgJson["Packages"]["Package"] = newPkgs

    return pkgJson


def module_filter(pkgJson: dict) -> dict:
    """Rebuild module for selected packages"""
    if "Modules" in pkgJson:
        packageNames = []
        for names in pkgJson["Packages"]["Package"]:
            packageNames.append(names["PackageName"])

        allModules = pkgJson["Modules"]["Module"]
        newModules = []
        for module in allModules:
            refPackage = module["ReferencePackages"]["ReferencePackage"]
            for names in refPackage:
                if names in packageNames:
                    newModules.append(module)

        pkgJson["Modules"]["Module"] = newModules
    return pkgJson


def get_package_url(pkgJson: dict) -> list[str]:
    """Get package count and download url"""
    count = core = 0
    pkgUrl = []
    for pkg in pkgJson["Packages"]["Package"]:
        count += 1
        pkgUrl.append(pkg["Path"])
        if pkg.get("Type") == "core":
            core += 1

    print(f"\n{core} core and {count - core} none-core packages to download.")

    return pkgUrl


def package_filter(pkgJson: dict, lang: list[str]):
    """Filter and rebuild packages by conditions and languages"""

    # filter unused languages data
    pkgJson = language_filter(pkgJson, lang)

    # filter by conditions string
    pkgJson = condition_filter(pkgJson, lang)

    # filter unused module
    pkgJson = module_filter(pkgJson)

    # get package urls
    pkgUrl = get_package_url(pkgJson)

    return pkgJson, pkgUrl


def package_download(url: str, destDir: str, code: str, ver: str, name=None) -> None:
    """Download a product package"""
    if not name:
        name = os.path.basename(url)
    print("\n[{}_{}] Downloading {}".format(code, ver, name))
    download_file(url, destDir)


def get_appjson(prodInfo: list) -> dict:
    """Download package json file"""
    if "appType" in prodInfo and prodInfo["appType"] == "dep":
        dep_data = list(prodInfo["versions"].values())
        firstItem = dep_data[0]
        appGuid = firstItem["buildGuid"]
    else:
        appGuid = prodInfo["buildGuid"]

    """Retrieve JSON."""
    headers = ADOBE_REQ_HEADERS.copy()
    headers["x-adobe-build-guid"] = appGuid

    print("\nDownloading Application.json file ...")
    #fileName = prodInfo["sapCode"] + "_Application.json"
    return download_json(ADOBE_APPLICATION_JSON_URL, headers)


def write_driver_xml(pkgJson: dict, pkgDir: str) -> None:
    """Generate Diver.xml and save to product dir"""
    driverInfo = ET.Element("DriverInfo")
    productInfo = ET.SubElement(driverInfo, "ProductInfo")
    for key, val in dict(
        {
            "Name": "Adobe {}".format(pkgJson["Name"]),
            "SAPCode": pkgJson["SAPCode"],
            "CodexVersion": pkgJson["CodexVersion"],
            "BaseVersion": pkgJson["BaseVersion"],
            "Platform": pkgJson["Platform"],
            "EsdDirectory": (os.path.join("./", pkgJson["SAPCode"])),
        }
    ).items():
        child = ET.Element(key)
        child.text = str(val)
        productInfo.append(child)

    if "Dependencies" in pkgJson:
        depRoot = ET.SubElement(productInfo, "Dependencies")
        for d in pkgJson["Dependencies"]["Dependency"]:
            deps = ET.Element("Dependency")
            for key, val in dict(
                {
                    "SAPCode": d["SAPCode"],
                    "BaseVersion": d["BaseVersion"],
                    "EsdDirectory": (os.path.join("./", d["SAPCode"])),
                }
            ).items():
                child = ET.Element(key)
                child.text = str(val)
                deps.append(child)
            depRoot.append(deps)

    # for url > v5
    if "IsNonCCProduct" in pkgJson and "IsNglEnabled" in pkgJson:
        for key, val in dict(
            {
                "IsNonCCProduct": pkgJson["IsNonCCProduct"],
                "IsNglEnabled": True if "NglLicensingInfo" in pkgJson else False,
            }
        ).items():
            child = ET.Element(key)
            child.text = str(val)
            productInfo.append(child)

    langRoot = ET.SubElement(productInfo, "SupportedLanguages")
    for lg in pkgJson["SupportedLanguages"]["Language"]:
        for key, val in dict({"Language": ""}).items():
            child = ET.Element(key)
            child.set("locale", lg["locale"])
            langRoot.append(child)

    # suppress error on dep package download
    if "MinimumSupportedClientVersion" in pkgJson and "HDBuilderVersion" in pkgJson:
        for key, val in dict(
            {
                "MinimumSupportedClientVersion": pkgJson["MinimumSupportedClientVersion"],
                "HDBuilderVersion": pkgJson["HDBuilderVersion"],
            }
        ).items():
            child = ET.Element(key)
            child.text = str(val)
            productInfo.append(child)

    if pkgJson["SAPCode"] == "LTRM":
        requestInfo = ET.SubElement(driverInfo, "RequestInfo")
        reqSub = ET.SubElement(requestInfo, "IsEnterpriseDeployment")
        reqSub.text = "true"

    tree = ET.ElementTree(driverInfo)
    ET.indent(tree, space="    ", level=0)

    fileName = pkgJson["SAPCode"] + "-" + "Driver.xml"
    xml_file = os.path.join(pkgDir, fileName)
    tree.write(xml_file, encoding="utf-8", xml_declaration=True)


def product_download(prodInfo: list, allProducts: dict, reqLang: list) -> None:
    """Download product related packages"""
    sapCode = prodInfo["sapCode"]

    # create product packages dir
    pkgDir = os.path.join(cfg['productDir'], sapCode)
    os.makedirs(pkgDir, exist_ok=True)

    appJsonData = get_appjson(prodInfo)

    # filter out unused packages and resource urls
    appJsonData, urls = package_filter(appJsonData, reqLang)

    # download packages
    cdn = appJsonData["Cdn"]["Secure"]
    version = appJsonData["ProductVersion"]

    if allProducts[sapCode]["appType"] == "app":
        if appJsonData.get("AddRemoveInfo"):
            appName = appJsonData["AddRemoveInfo"]["DisplayName"]["Language"][0]["value"]
        else:
            appName = "Adobe " + appJsonData.get("FamilyName")

        print(f"\nDownloading packages for {appName}, version-{version}")

        print("\nCreating Driver.xml file...")
        write_driver_xml(appJsonData, cfg['productDir'])

    print("\nCreating Application.json file...")
    create_json(os.path.join(pkgDir, "Application.json"), appJsonData)

    for url in urls:
        url = cdn + url

        package_download(url, pkgDir, sapCode, version)

    if "Dependencies" in appJsonData:
        print("\nDownloading dependency packages...")
        for dependency in appJsonData["Dependencies"]["Dependency"]:
            depSap = dependency["SAPCode"]
            depPackage = allProducts.get(depSap)

            product_download(depPackage, allProducts, reqLang)


def download_acrobat(prodInfo, toDown):
    """Download acrobat installer or updates"""
    url = cfg['cdn'] + prodInfo["manifestURL"]

    print("\nDownloading manifest.xml ...")
    manifest = download_xml(url, ADOBE_REQ_HEADERS)

    # check available products
    assetList = manifest.findall("./asset_list/asset")
    productList = {}
    prodNum = 0
    availNums = []
    full = None
    for asset in assetList:
        prodNum += 1
        availNums.append(str(prodNum))
        assetPath = asset.find("./asset_path").text
        baseVersion = asset.find(".//baseVersion")
        if baseVersion is not None:
            baseVersion = baseVersion.text
        else:
            full = str(prodNum)

        productList[str(prodNum)] = {
            "assetName": os.path.basename(assetPath),
            "assetSize": asset.find("./asset_size").text,
            "assetPath": assetPath,
            "baseVersion": baseVersion,
        }

    # select product to download
    selectedCode = None
    if len(toDown) > 1:
        selectedCode = full

    while selectedCode is None:
        print("\nAvailable downloads\n")
        for n, p in productList.items():
            if p["baseVersion"] is None:
                full = n
                print(
                    "{}. {}{} Full Installer".format(
                        n, p["assetName"], (35 - len(p["assetName"])) * " "
                    )
                )
            else:
                print(
                    "{}. {}{} Update package for version {}".format(
                        n,
                        p["assetName"],
                        (35 - len(p["assetName"])) * " ",
                        p["baseVersion"],
                    )
                )

        val = input(
            "\nPlease enter the number from the list above or full installer: "
        ) or full

        if val in availNums:
            selectedCode = val
        elif val == "":
            print("No product selected! Please use a value from the list above.")
        else:
            print(f"{val} is not available! Please check your input.")

    aproDir = os.path.join(cfg["productDir"], "APRO")
    os.makedirs(aproDir, exist_ok=True)

    assetPath = productList[selectedCode]["assetPath"]

    print("\nDownloading Adobe Acrobat v. {} for {}...".format(
        prodInfo["productVersion"], prodInfo["appPlatform"]))

    download_file(assetPath, aproDir)


def run_ccdl(allProducts: dict) -> None:
    """Run Main execution."""
    toDown = download_list(allProducts)

    for sapCode in toDown:
        product = allProducts.get(sapCode)

        batch = False
        if len(toDown) > 1:
            # select app by version
            batch = True

        prodInfo = select_app_version(product, batch)

        # language select
        appLangs = prodInfo["supportedLanguages"]
        installLanguage = install_language(appLangs)

        if "productIcons" in prodInfo:
            download_icons(prodInfo)

        # download by manifest url
        if sapCode == "APRO":
            download_acrobat(prodInfo, toDown)
            continue

        product_download(prodInfo, allProducts, installLanguage)


if __name__ == "__main__":
    show_info(SCRIPT_NAME, VERSION_STR, 6, "=")

    # get and set configuration
    cfg = set_config()

    # get available products
    allProducts = get_products(cfg)

    while True:
        try:
            # run main program
            run_ccdl(allProducts)

            # reset download list
            cfg["toDown"] = None

            if cfg["noRepeat"] or not questiony(
                "\nDo you want to download another package"
            ):
                print("Bye!")
                break

        except KeyboardInterrupt:
            print("\nTerminated by user")
            sys.exit()
