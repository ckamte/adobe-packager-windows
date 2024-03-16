"""
This is the Adobe Offline Package downloader for Windows.

Download package only! (except acrobat pro) Installer not included

Based on https://github.com/Drovosek01/adobe-packager
"""

import os
import string
import random
import argparse
import json
import locale
import ctypes
import sys
import operator
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

VERSION = 1
VERSION_STR = "1.0.0"
CODE_QUALITY = "Really_AWFUL"

ADOBE_PRODUCTS_XML_URL = "https://prod-rel-ffc-ccm.oobesaas.adobe.com/adobe-ffc-external/core/v{urlVersion}/products/all?_type=xml&channel=ccm&channel=sti&platform={installPlatform}&productType=Desktop"
ADOBE_APPLICATION_JSON_URL = "https://cdn-ffc.oobesaas.adobe.com/core/v3/applications"

ADOBE_REQ_HEADERS = {
    "X-Adobe-App-Id": "accc-hdcore-desktop",
    "User-Agent": "Adobe Application Manager 2.0",
    "X-Api-Key": "CC_HD_ESD_1_0",
    "Cookie": "fg="
    + "".join(random.choice(string.ascii_uppercase + string.digits) for _ in range(26))
    + "======",
}

ADOBE_DL_HEADERS = {"User-Agent": "Creative Cloud"}

session = requests.sessions.Session()


def show_version():
    ye = int((32 - len(VERSION_STR)) / 2)
    print("=================================")
    print("=  Adobe CC Package Downloader  =")
    print(
        "{} {} {}\n".format("=" * ye, VERSION_STR, "=" * (31 - len(VERSION_STR) - ye))
    )


def get_install_dir():
    return os.path.join(os.environ["PROGRAMFILES"], "Adobe")


def questiony(question: str) -> bool:
    """Question prompt default Y."""
    reply = None
    while reply not in ("", "y", "n"):
        reply = input(f"{question} (Y/n): ").lower()
    return reply in ("", "y")


def url_version():
    urlVersion = None
    if args.urlVersion:
        if args.urlVersion.lower() == "v4" or args.urlVersion == "4":
            urlVersion = 4
        elif args.urlVersion.lower() == "v5" or args.urlVersion == "5":
            urlVersion = 5
        elif args.urlVersion.lower() == "v6" or args.urlVersion == "6":
            urlVersion = 6
        else:
            print(
                'Invalid argument "{}" for {}! Please select from version list below\n'.format(
                    args.urlVersion, "URL version"
                )
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

        val = (
            input(
                "\nPlease enter the URL version(v4/v5/v6) for downloading products.xml, or nothing for v6: "
            )
            or "v6"
        )
        if val == "v4" or val == "4":
            urlVersion = 4
        elif val == "v5" or val == "5":
            urlVersion = 5
        elif val == "v6" or val == "6":
            urlVersion = 6
        else:
            print("Invalid URL version: {}\n".format(val))

    return urlVersion


def app_platform():
    winPlatforms = {
        "win32": "32 Bit Windows",
        "win64": "64 Bit Windows",
        "winarm64": "Windows ARM",
    }
    appPlatform = None
    if args.appPlatform:
        if args.appPlatform in winPlatforms:
            appPlatform = args.appPlatform
            print("\nUsing provided version: " + appPlatform)
        else:
            print(
                'Invalid argument "{}" for {}! Please select form list below\n'.format(
                    args.appPlatform, "application platform"
                )
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
            print("Invalid platform: {}\n".format(val))

    return appPlatform


def product_code(sapCodes):
    selectedCode = args.sapCode
    if selectedCode:
        selectedCode = selectedCode.upper()

    if selectedCode and selectedCode not in sapCodes:
        print("\nProvided SAP code ({}) is not available\n".format(selectedCode))
        answer = None
        while answer is None:
            answer = input("Are you want to continue? (y/n): ")
            if answer.lower() in ["y", "yes"]:
                print("")
                selectedCode = None
            elif answer.lower() in ["n", "no"]:
                print("\nProgram terminated!\n")
                exit()
            else:
                print("\nPlease enter yes or no!")
                answer = None

    if not selectedCode or selectedCode is None:
        for s, d in sapCodes.items():
            print("[{}]{}{}".format(s, (10 - len(s)) * " ", d))

        while selectedCode is None:
            val = input(
                "\nPlease enter the SAP Code of the desired product from the list above: "
            ).upper()
            if products.get(val):
                selectedCode = val
            elif val == "":
                print("No product selected! Please use a value from the list above.")
            else:
                print(
                    "{} is not available! Please use a value from the list above.".format(
                        val
                    )
                )
    return selectedCode


def product_version(product, versions):
    version = None
    if args.version:
        if versions.get(args.version):
            print("\nUsing provided version: " + args.version)
            version = args.version
        else:
            print("\nProvided version not found: " + args.version)

    print("")

    if not version:
        lastVersion = None
        for v in reversed(versions.values()):
            if v["buildGuid"] is not None or v["manifestURL"] is not None:
                print(
                    "{} Platform: {} - {}".format(
                        product["displayName"], v["appPlatform"], v["productVersion"]
                    )
                )
                lastVersion = v["productVersion"]

        while version is None:
            val = (
                input(
                    "\nPlease enter the desired version. Nothing for "
                    + lastVersion
                    + ": "
                )
                or lastVersion
            )
            if versions.get(val):
                version = val
            else:
                print(
                    "{} is not a valid version. Please use a value from the list above.".format(
                        val
                    )
                )

    print(
        "\nPrepare to download Adobe {}, version {}".format(
            product["displayName"], version
        )
    )
    return version


def install_language(supportedLangs):
    if "mul" in supportedLangs:
        supportedLangs[supportedLangs.index("mul")] = "All"
    else:
        if "All" not in supportedLangs:
            supportedLangs.append("All")
    supportedLangs.sort()

    # Detecting current language.
    windll = ctypes.windll.kernel32
    osLang = locale.windows_locale[windll.GetUserDefaultUILanguage()]

    if args.osLanguage:
        osLang = args.osLanguage

    defLang = "All"
    if osLang in supportedLangs:
        defLang = osLang

    installLanguage = None
    if args.installLanguage:
        if args.installLanguage in supportedLangs:
            print("\nUsing provided language: " + args.installLanguage)
            installLanguage = args.installLanguage
        else:
            print("\nProvided language not available: " + args.installLanguage)

    if not installLanguage:
        print("\nAvailable languages: {}".format(", ".join(supportedLangs)))
        while installLanguage is None:
            val = (
                input(
                    f"\nPlease enter the desired install language, or nothing for [{defLang}]: "
                )
                or defLang
            )
            if len(val) == 5:
                val = val[0:2].lower() + val[2] + val[3:5].upper()
            elif len(val) == 3:
                val = val[0].upper() + val[1:].lower()
            if val in supportedLangs:
                installLanguage = val
            else:
                print(
                    "{} is not available. Please use a value from the list above.".format(
                        val
                    )
                )

    if osLang != installLanguage:
        if installLanguage != "All":
            while osLang not in supportedLangs:
                print("Could not detect your default Language.")
                osLang = (
                    input(
                        f"\nPlease enter the your OS Language, or nothing for [{installLanguage}]: "
                    )
                    or installLanguage
                )
                if osLang not in supportedLangs:
                    print(
                        "{} is not available. Please use a value from the list above.".format(
                            osLang
                        )
                    )

    return installLanguage


def product_icons(elem):
    productIcons = []
    if len(elem.find("productIcons")):
        for icon in elem.findall("productIcons/icon"):
            productIcons.append(icon.text)
    return productIcons


def product_languages(elem):
    supportedLang = []
    if len(elem.find("locales")):
        for locale in elem.findall("locales/locale"):
            supportedLang.append(locale.get("name"))
    return supportedLang


def parse_products_xml(products_url, url_version, allowed_platform, selected_platform):
    # get xml data
    print("Downloading product data\n")
    response = session.get(products_url, stream=True, headers=ADOBE_REQ_HEADERS)
    response.encoding = "utf-8"
    products_xml = ET.fromstring(response.content)

    # with open('products.xml', 'wb+') as f:
    #    f.write(response.content)
    # products_xml = ET.parse("products.xml")

    cdn = products_xml.find(".//*/cdn/secure").text
    allProducts = {}
    for channel in products_xml.findall(".//channel"):
        appType = "dep"
        if channel.attrib["name"] == "ccm":
            appType = "app"

        for product in channel.findall("./products/product"):
            sapCode = product.get("id")
            displayName = product.find("displayName").text
            for plat in [
                item
                for item in product.findall("./platforms/platform")
                if item.attrib["id"] in allowed_platform
            ]:
                appPlatform = plat.attrib["id"]
                # platform filter for main app
                if appType == "app" and appPlatform != selected_platform:
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
                                "productIcons": product_icons(product),
                                "buildGuid": languageSet.get("buildGuid"),
                                "manifestURL": manifestURL,
                            }
                        else:
                            if url_version >= 5:
                                allProducts.pop(sapCode, None)

    return allProducts, cdn


def get_products():
    selectedVersion = url_version()
    print("\nUsing URL version {}\n".format(selectedVersion))

    selectedPlatform = app_platform()
    print("\nGetting {} products\n".format(selectedPlatform))

    if args.Auth:
        ADOBE_REQ_HEADERS["Authorization"] = args.Auth

    allowedPlatforms = [selectedPlatform]
    productsPlatform = selectedPlatform
    if selectedPlatform == "win64":
        allowedPlatforms.append("win32")
        productsPlatform += ",win32"

    products_xml_url = ADOBE_PRODUCTS_XML_URL.format(
        urlVersion=selectedVersion, installPlatform=productsPlatform
    )
    # download and parse product xml
    products, cdn = parse_products_xml(
        products_xml_url, selectedVersion, allowedPlatforms, selectedPlatform
    )

    sapCodes = {}
    for p in products.values():
        if p["appType"] == "app":
            versions = p["versions"]
            lastVersion = None
            for v in reversed(versions.values()):
                if v["buildGuid"] is not None or v["manifestURL"] is not None:
                    lastVersion = v["productVersion"]
            if lastVersion:
                sapCodes[p["sapCode"]] = p["displayName"]
    print(str(len(sapCodes)) + " products found:")

    return products, cdn, sapCodes, selectedPlatform


def get_download_path():
    """Ask for desired download folder"""
    if args.destination:
        print("\nUsing provided destination: " + args.destination + "\n")
        dest = args.destination
    else:
        dest = os.path.dirname(os.path.realpath(__name__))
    return dest


def download_progress(url, dest_dir, prefix=""):
    # get file size
    response = session.head(url, stream=False, headers=ADOBE_DL_HEADERS)
    total_size_in_bytes = int(response.headers.get("content-length", 0))

    if (
        args.skipExisting
        and os.path.isfile(dest_dir)
        and os.path.getsize(dest_dir) == total_size_in_bytes
    ):
        print("Downloaded file is OK, skipping ... \n")
        return True

    # download file
    response = session.get(url, stream=True, headers=ADOBE_REQ_HEADERS)

    filename = os.path.basename(url)
    if prefix:
        filename = prefix + filename

    dest_dir = os.path.join(dest_dir, filename)
    block_size = 1024  # 1 Kibibyte
    progress_bar = tqdm(total=total_size_in_bytes, unit="iB", unit_scale=True)
    with open(dest_dir, "wb") as file:
        for data in response.iter_content(block_size):
            progress_bar.update(len(data))
            file.write(data)

    progress_bar.close()

    if total_size_in_bytes != 0 and progress_bar.n != total_size_in_bytes:
        print("Cannot determine download size!")
        return False
    else:
        return True


def icons_download(product, dest_dir):
    """Download product icons"""
    print("Downloading product icons\n")

    icon_dir = os.path.join(dest_dir, "icons")
    os.makedirs(icon_dir, exist_ok=True)

    icons = product["productIcons"]
    prefix = product["sapCode"].lower()
    for url in icons:
        download_progress(url, icon_dir, prefix)


def file_download(url, dest_dir, s, v, name=None):
    """Download a product package"""
    if not name:
        name = os.path.basename(url)
    print("[{}_{}] Downloading {}".format(s, v, name))
    return download_progress(url, dest_dir)


def download_acrobat(appInfo, cdn):
    # download manifest file
    response = session.get(
        cdn + appInfo["manifestURL"], stream=True, headers=ADOBE_REQ_HEADERS
    )
    response.encoding = "utf-8"
    manifest = ET.fromstring(response.text)

    # check available products
    assetList = manifest.findall("./asset_list/asset")
    productList = {}
    prodNum = 0
    for asset in assetList:
        prodNum += 1
        assetPath = asset.find("./asset_path").text
        baseVersion = asset.find(".//baseVersion")
        if baseVersion is not None:
            baseVersion = baseVersion.text

        productList[str(prodNum)] = {
            "assetName": os.path.basename(assetPath),
            "assetSize": asset.find("./asset_size").text,
            "downloadUrl": assetPath,
            "baseVersion": baseVersion,
        }

    selectedCode = None
    while selectedCode is None:
        print("\nAvailable downloads\n")
        for n, p in productList.items():
            if p["baseVersion"] is None:
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
            "\nPlease enter the number of the desired product from the list above: "
        )

        if val in productList:
            selectedCode = val
        elif val == "":
            print("No product selected! Please use a value from the list above.")
        else:
            print("{} is not available! Please check your input.".format(val))

    downloadURL = productList[val]["downloadUrl"]

    dest = get_download_path()
    sapCode = appInfo["sapCode"]
    version = appInfo["productVersion"]
    name = os.path.basename(downloadURL)
    filePath = os.path.join(dest, name)

    if file_download(downloadURL, dest, sapCode, version, name) is True:
        print("\n{} was successfully downloaded to: {}".format(name, filePath))
    return


def get_application_json(buildGuid):
    """Retrieve JSON."""
    headers = ADOBE_REQ_HEADERS.copy()
    headers["x-adobe-build-guid"] = buildGuid
    response = session.get(ADOBE_APPLICATION_JSON_URL, headers=headers)
    response.encoding = "utf-8"
    return json.loads(response.content)


def save_application_json(pkg_dir, json_data):
    app_json_path = os.path.join(pkg_dir, "Application.json")
    with open(app_json_path, "w+") as file:
        json.dump(json_data, file, separators=(",", ":"))


def write_driver_xml(json, pds_dir, prefix=""):
    driverInfo = ET.Element("DriverInfo")
    productInfo = ET.SubElement(driverInfo, "ProductInfo")
    for key, val in dict(
        {
            "Name": "Adobe {}".format(json["Name"]),
            "SAPCode": json["SAPCode"],
            "CodexVersion": json["CodexVersion"],
            "BaseVersion": json["BaseVersion"],
            "Platform": json["Platform"],
            "EsdDirectory": (os.path.join("./", json["SAPCode"])),
        }
    ).items():
        child = ET.Element(key)
        child.text = str(val)
        productInfo.append(child)

    if "Dependencies" in json:
        dep_root = ET.SubElement(productInfo, "Dependencies")
        for d in json["Dependencies"]["Dependency"]:
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
            dep_root.append(deps)

    # for url > v5
    if "IsNonCCProduct" in json and "IsNglEnabled" in json:
        for key, val in dict(
            {
                "IsNonCCProduct": json["IsNonCCProduct"],
                "IsNglEnabled": True if "NglLicensingInfo" in json else False,
            }
        ).items():
            child = ET.Element(key)
            child.text = str(val)
            productInfo.append(child)

    lang_root = ET.SubElement(productInfo, "SupportedLanguages")
    for lg in json["SupportedLanguages"]["Language"]:
        for key, val in dict({"Language": ""}).items():
            child = ET.Element(key)
            child.set("locale", lg["locale"])
            lang_root.append(child)

    # suppress error on dep package download
    if "MinimumSupportedClientVersion" in json and "HDBuilderVersion" in json:
        for key, val in dict(
            {
                "MinimumSupportedClientVersion": json["MinimumSupportedClientVersion"],
                "HDBuilderVersion": json["HDBuilderVersion"],
            }
        ).items():
            child = ET.Element(key)
            child.text = str(val)
            productInfo.append(child)

    if json["SAPCode"] == "LTRM":
        requestInfo = ET.SubElement(driverInfo, "RequestInfo")
        req_sub = ET.SubElement(requestInfo, "IsEnterpriseDeployment")
        req_sub.text = "true"

    tree = ET.ElementTree(driverInfo)
    ET.indent(tree, space="    ", level=0)
    xml_file = os.path.join(pds_dir, prefix + "Driver.xml")
    tree.write(xml_file, encoding="utf-8", xml_declaration=True)


def condition_test(package, language, ProcessorFamily, condition):
    packageType = ProcessorFamily
    if "ProcessorFamily" in package:
        packageType = package["ProcessorFamily"]

    if "==" in condition:
        testSubject, testValue = condition.split("==")
        testOption = operator.eq
    elif "!=" in condition:
        testSubject, testValue = condition.split("!=")
        testOption = operator.ne
    elif "<=" in condition:
        testSubject, testValue = condition.split("<=")
        testOption = operator.le
    elif ">=" in condition:
        testSubject, testValue = condition.split(">=")
        testOption = operator.ge
    elif ">" in condition:
        testSubject, testValue = condition.split(">")
        testOption = operator.gt
    elif "<" in condition:
        testSubject, testValue = condition.split("<")
        testOption = operator.lt

    # start testing
    if testSubject.strip() == "[OSProcessorFamily]":
        return testOption(testValue.strip(), ProcessorFamily)
    elif testSubject.strip() == "[OSVersion]":
        getWinVer = sys.getwindowsversion()
        winVer = "{}.{}".format(getWinVer.major, getWinVer.minor)
        return testOption(testValue.strip(), winVer)
    elif testSubject.strip() == "[installLanguage]" and packageType == ProcessorFamily:
        if language.lower() == "all" or language.lower() == "mul":
            return True
        else:
            return testOption(testValue.strip(), language)
    else:
        # alway true on unset
        return True


def condition_filter(package, language, ProcessorFamily):
    conditions = []
    conditionString = package["Condition"].strip()
    if "&&" in conditionString:
        conditions = conditionString.split("&&")
        for condition in conditions:
            testResult = condition_test(package, language, ProcessorFamily, condition)
            if testResult is False:
                break

    elif "||" in conditionString:
        conditions = conditionString.split("||")
        for condition in conditions:
            testResult = condition_test(package, language, ProcessorFamily, condition)
            if testResult is True:
                break
    else:
        testResult = condition_test(package, language, ProcessorFamily, conditionString)

    return testResult


def language_for_premiere(language):
    if "_" in language:
        main, locale = language.split("_")
        return "-esl_lp_" + main
    return language


def package_filter(package, language, platform):
    coreCount = 0
    noneCoreCount = 0
    urlPath = []
    newPackage = []

    ProcessorFamily = "64-bit"
    if platform == "win32":
        ProcessorFamily = "32-bit"

    for pkg in package:
        if pkg.get("Type") and pkg["Type"] == "core":
            if "Condition" in pkg:
                if condition_filter(pkg, language, ProcessorFamily) == True:
                    newPackage.append(pkg)
                    urlPath.append(pkg["Path"])
                    coreCount += 1
            elif "ProcessorFamily" in pkg:
                if platform == "win32":
                    if pkg["ProcessorFamily"] == ProcessorFamily:
                        newPackage.append(pkg)
                        urlPath.append(pkg["Path"])
                        coreCount += 1
                else:
                    newPackage.append(pkg)
                    urlPath.append(pkg["Path"])
                    coreCount += 1
            else:
                newPackage.append(pkg)
                urlPath.append(pkg["Path"])
                coreCount += 1
        else:
            if "Condition" in pkg:
                if condition_filter(pkg, language, ProcessorFamily) == True:
                    newPackage.append(pkg)
                    urlPath.append(pkg["Path"])
                    noneCoreCount += 1
            elif "ProcessorFamily" in pkg:
                if platform == "win32":
                    if pkg["ProcessorFamily"] == ProcessorFamily:
                        newPackage.append(pkg)
                        urlPath.append(pkg["Path"])
                        noneCoreCount += 1
                else:
                    newPackage.append(pkg)
                    urlPath.append(pkg["Path"])
                    noneCoreCount += 1
            else:
                # for premiere pro
                if "-esl_lp_" in pkg["PackageName"]:
                    if language_for_premiere(language) in pkg["PackageName"]:
                        newPackage.append(pkg)
                        urlPath.append(pkg["Path"])
                        noneCoreCount += 1
                else:
                    newPackage.append(pkg)
                    urlPath.append(pkg["Path"])
                    noneCoreCount += 1

    print(
        "Selected {} core packages and {} non-core packages".format(
            coreCount, noneCoreCount
        )
    )

    return urlPath, newPackage


# https://stackoverflow.com/questions/71543579/python-find-and-replace-all-values-under-a-certain-key-in-a-nested-dictionary
def language_filter(data, language):
    key = "Language"
    if isinstance(data, dict):
        # filter by locale
        filtered = {}
        for k, v in data.items():
            if k == key:
                for lc in v:
                    if lc["locale"] == language or lc["locale"] == "mul":
                        filtered = [lc]
        # replace with filtered result
        return {
            k: filtered if k == key and v else language_filter(v, language)
            for k, v in data.items()
        }
    elif isinstance(data, list):
        return [language_filter(v, language) for v in data]
    else:
        return data


def dependencies_download(json, products, pds_dir, installLanguage, selectedPlatform):
    for dependency in json["Dependencies"]["Dependency"]:
        depSap = dependency["SAPCode"]
        dep_dir = os.path.join(pds_dir, depSap)
        os.makedirs(dep_dir, exist_ok=True)

        depPackage = products.get(depSap)
        dep_data = list(depPackage["versions"].values())
        firstItem = dep_data[0]
        dep_json = get_application_json(firstItem["buildGuid"])
        if (
            package_download(dep_json, dep_dir, installLanguage, selectedPlatform)
            is False
        ):
            print("\nCannot download dependency package")
            break
    return


def package_download(json, pkg_dir, language, selectedPlatform):
    allPackages = json["Packages"]["Package"]
    cdn = json["Cdn"]["Secure"]
    sapCode = json["SAPCode"]
    version = json["ProductVersion"]
    urls, package = package_filter(allPackages, language, selectedPlatform)

    # module filter
    if "Modules" in json:
        packageNames = []
        for names in package:
            packageNames.append(names["PackageName"])

        allModules = json["Modules"]["Module"]
        newModules = []
        for module in allModules:
            refPackage = module["ReferencePackages"]["ReferencePackage"]
            for names in refPackage:
                if names in packageNames:
                    newModules.append(module)

        json["Modules"]["Module"] = newModules

    # filtered json data
    json["Packages"]["Package"] = package

    print("\nCreating Application.json")
    save_application_json(pkg_dir, json)
    for url in urls:
        if file_download(cdn + url, pkg_dir, sapCode, version) is False:
            return False
    return True


def run_ccdl(products, cdn, sapCodes, selectedPlatform):
    """Run Main execution."""
    # get product list
    sapCode = product_code(sapCodes)
    product = products.get(sapCode)

    # version select
    versions = product["versions"]
    selectedVersion = product_version(product, versions)

    # product to download
    prodInfo = versions[selectedVersion]

    # language select
    supportedLangs = prodInfo["supportedLanguages"]
    installLanguage = install_language(supportedLangs)

    # download by manifest url
    if sapCode == "APRO":
        download_acrobat(prodInfo, cdn)
        return

    # main product
    print(
        "\nPrepare to download Adobe {}-{}-{}-{}".format(
            prodInfo["displayName"],
            prodInfo["productVersion"],
            installLanguage,
            prodInfo["appPlatform"],
        )
    )

    dest = get_download_path()

    # download icons
    icons_download(prodInfo, dest)

    # create products directory
    products_dir = os.path.join(dest, "products")
    os.makedirs(products_dir, exist_ok=True)

    # create product packages dir
    package_dir = os.path.join(products_dir, sapCode)
    os.makedirs(package_dir, exist_ok=True)

    app_json = get_application_json(prodInfo["buildGuid"])

    # filter out unused languages from Application.json file
    if installLanguage.lower() != "all":
        app_json = language_filter(app_json, installLanguage)

    if (
        package_download(app_json, package_dir, installLanguage, selectedPlatform)
        is False
    ):
        print("\nCannot download all packages")

    if "Dependencies" in app_json:
        print("\nDownloading dependencies")
        dependencies_download(
            app_json, products, products_dir, installLanguage, selectedPlatform
        )

    print("Generating Driver.xml")
    prefix = app_json["SAPCode"] + "-"
    write_driver_xml(app_json, products_dir, prefix)

    print(
        "\nSuccessfully downloaded Adobe {} v-{}".format(
            prodInfo["displayName"],
            prodInfo["productVersion"],
        )
    )

    return


if __name__ == "__main__":
    show_version()

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-l", "--installLanguage", help="Language code (eg. en_US)", action="store"
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
        help="SAP code for desired product (eg. PHSP)",
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
        "--noRepeatPrompt",
        help="Don't prompt for additional downloads",
        action="store_true",
    )
    parser.add_argument(
        "-x",
        "--skipExisting",
        help="Skip existing files, e.g. resuming failed downloads",
        action="store_true",
    )
    args = parser.parse_args()

    products, cdn, sapCodes, selectedPlatform = get_products()

    while True:
        try:
            run_ccdl(products, cdn, sapCodes, selectedPlatform)
            if args.noRepeatPrompt or not questiony(
                "\n\nDo you want to download another package"
            ):
                break
        except KeyboardInterrupt:
            print("\nProgram was terminated by user")
            sys.exit()
