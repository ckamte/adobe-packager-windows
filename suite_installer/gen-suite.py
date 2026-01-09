import os
import io
import sys
import json
import argparse
from pathlib import Path
import xml.etree.ElementTree as ET

prodsDir = "./products"

SCRIPT_NAME = "Suite Info xml generator"
VERSION_STR = "1.0.00"


def show_info(name: str, version: str, pad: int, bdr: str) -> None:
    """Show script information"""
    tl = len(name) + (pad * 2)
    print(bdr * tl)
    print(bdr + name.center(tl - 2) + bdr)
    print(version.center(tl, bdr))


def icon_list(elem, sap):
    sap = sap.lower()
    icons = ET.SubElement(elem, "Icons")
    list = ["20x19", "32x32", "44x42", "64x64", "88x84", "176x168"]
    for ic in list:
        ico = ET.SubElement(icons, f"Size{ic}")
        path = ET.SubElement(ico, "path")
        path.text = f"./resources/icons/{sap}{ic}.png"

def calc_sizes(data):
    pkgs = data["Packages"]["Package"]
    size = 0
    for tmp in pkgs:
        size += int(tmp.get("ExtractSize"))
    
    return str(size)


def add_product(elem):
    pDir = Path(prodsDir)
    paths = [str(item) for item in pDir.rglob('*/') if item.is_dir()]
    if len(paths) < 1:
        print("\nNo products found in products directory")
        sys.exit("\nBye")
    
    print("\nGenerating ...")
    langs = []
    for p in paths:
        file = os.path.join(".", p, "Application.json")
        if Path(file).is_file() == False:
            continue
        
        with open(file, "r") as f:
            data = json.load(f)
            if data.get("AddRemoveInfo") and data.get("IsSTI") is False:
                sapCode = data.get("SAPCode")
                prod = ET.SubElement(elem, "ProductInfo")
                name = ET.SubElement(prod, "Name")
                name.text = data["AddRemoveInfo"]["DisplayName"]["Language"][0]["value"]

                type = ET.SubElement(prod, "InstallerType")
                type.text = "HD"

                hide = ET.SubElement(prod, "HideProductLaunch")
                hide.text = "true"

                icon_list(prod, sapCode)
            
                insData = ET.SubElement(prod, "InstallData")
                hdData = ET.SubElement(insData, "HDData")
                for k, v in dict({
                    "SAPCode": sapCode,
                    "CodexVersion" : data.get("CodexVersion"),
                    "BaseVersion": data.get("BaseVersion"),
                    "Platform": data.get("Platform"),
                    "EsdDirectory": f"{prodsDir}/{sapCode}",
                    "InstallSize": calc_sizes(data),
                }).items():
                    x = ET.SubElement(hdData, k)
                    x.text =  v

                supLangs = data["SupportedLanguages"]["Language"]
                for k in supLangs:
                    if k["locale"] not in langs:
                        langs.append(k["locale"])

                if data.get("Dependencies"):
                    deps = ET.SubElement(hdData, "Dependencies")

                    depList = data["Dependencies"]["Dependency"]
                    for d in depList:
                        esdDir = f"{prodsDir}/{d.get("SAPCode")}"
                        depJson = os.path.join(Path(esdDir), "Application.json")
                        with open(depJson, "r") as f:
                            depData = json.load(f)
                            size = calc_sizes(depData)
                            dPkg = ET.SubElement(deps, "Dependency")
                            for k, v in dict({
                                "SAPCode": d.get("SAPCode"),
                                "BaseVersion": d.get("BaseVersion"),
                                "EsdDirectory": esdDir,
                                "InstallSize": size or "0",
                            }).items():
                                x = ET.SubElement(dPkg, k)
                                x.text =  v

                if sapCode == "LTRM":
                    requestInfo = ET.SubElement(insData, "RequestInfo")
                    reqSub = ET.SubElement(requestInfo, "IsEnterpriseDeployment")
                    reqSub.text = "true"
    return langs


def gen_suiteinfo():
    '''
    Generate SuiteInfo.xml for suite like installer
    '''
    suiteInfo = ET.Element("SuiteInfo")

    tmp = ET.SubElement(suiteInfo, "SuiteName")
    tmp.text = suiteName

    tmp = ET.SubElement(suiteInfo, "CodexVersion")
    tmp.text = suiteVer

    supLangs = ET.SubElement(suiteInfo, "SupportedLanguages")
    
    infoList = ["IsNonCCSuite", "IsAAMRequired", "IsCCDRequired"]
    for inf in infoList:
        tmp = ET.SubElement(suiteInfo, inf)
        tmp.text = "false"

    icon_list(suiteInfo, "cloud")

    products = ET.SubElement(suiteInfo, "ProductInfos")
    langs = add_product(products)

    for sl in langs:
        # remove mul from locale list
        if sl == "mul":
            continue

        tmp = ET.SubElement(supLangs, "Locale")
        tmp.text = sl
    
    
    tree = ET.ElementTree(suiteInfo)
    ET.indent(tree, space="    ", level=0)
    xml_file = os.path.join(prodsDir, "SuiteInfo.xml")
    xml_declaration = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'

    with io.open(xml_file, "wb") as f:
        f.write(xml_declaration.encode("utf-8"))
        tree.write(f, encoding="utf-8", xml_declaration=False)
        print(f"\nSuccessfully generated: {os.path.realpath(xml_file)}\n")


if __name__ == "__main__":
    """Get command-line parameters"""
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-d", "--prodsDir", help="Products directory", action="store"
    )
    parser.add_argument(
        "-n", "--suiteName", help="Name for suite", action="store"
    )
    parser.add_argument(
        "-v", "--suiteVer", help="Suite version number", action="store"
    )
    args = parser.parse_args()

    show_info(SCRIPT_NAME, VERSION_STR, 10, "=")

    suiteName = args.suiteName

    while suiteName is None:
        suiteName = (input("\nPlease enter a name for suite: ").strip() or "Adobe Creative Cloud")
    
    suiteVer = args.suiteVer
    while suiteVer is None:
        suiteVer = (input("\nPlease enter suite version: ").strip() or "1.0")
    
    prodsDir = args.prodsDir or prodsDir
    print(f"\nSuiteInfo.xml file will be save in {os.path.realpath(prodsDir)}")
    
    gen_suiteinfo()