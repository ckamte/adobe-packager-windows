"""
This is the Adobe Offline Package downloader for Windows.

Download package only! Installer not included

FYI - If cannot down APRO, please re-run the script :)
      Check line number 593

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
from collections import OrderedDict
from xml.etree import ElementTree as ET

try:
    import requests
except ImportError:
        sys.exit("""You need requests module!
            install it from https://pypi.org/project/requests/
            or run: pip3 install requests.""")

try:
    from tqdm.auto import tqdm
except ImportError:
    sys.exit("""You need tqdm module!
            install it from https://pypi.org/project/tqdm/
            or run: pip3 install tqdm.""")

VERSION = 1
VERSION_STR = '0.0.1'
CODE_QUALITY = 'Really_AWFUL'

ADOBE_PRODUCTS_XML_URL = 'https://prod-rel-ffc-ccm.oobesaas.adobe.com/adobe-ffc-external/core/v{urlVersion}/products/all?_type=xml&channel=ccm&channel=sti&platform={installPlatform}&productType=Desktop'
ADOBE_APPLICATION_JSON_URL = 'https://cdn-ffc.oobesaas.adobe.com/core/v3/applications'

ADOBE_REQ_HEADERS = {
    'X-Adobe-App-Id': 'accc-apps-panel-desktop',
    'User-Agent': 'Adobe Application Manager 2.0',
    'X-Api-Key': 'CC_HD_ESD_1_0',
    'Cookie': 'fg=' + ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(26)) + '======'
}

ADOBE_DL_HEADERS = {
    'User-Agent': 'Creative Cloud'
}

session = requests.sessions.Session()

try:
    os.environ["PROGRAMFILES(X86)"]
    osArch = "win64"
except:
    osArch = "win32"


def show_version():
    ye = int((32 - len(VERSION_STR)) / 2)
    print('=================================')
    print('=  Adobe CC Package Downloader  =')
    print('{} {} {}\n'.format('=' * ye, VERSION_STR,
          '=' * (31 - len(VERSION_STR) - ye)))


def get_install_dir():
    return os.path.join(os.environ["PROGRAMFILES"], "Adobe")


def questiony(question: str) -> bool:
    """Question prompt default Y."""
    reply = None
    while reply not in ("", "y", "n"):
        reply = input(f"{question} (Y/n): ").lower()
    return (reply in ("", "y"))


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
            print('Invalid argument "{}" for {}'.format(args.urlVersion, 'URL version'))
            exit(1)

    while not urlVersion:
        val = input('\nPlease enter the URL version(v4/v5/v6) for downloading products.xml, or nothing for v6: ') or 'v6'
        if val == 'v4' or val == '4':
            urlVersion = 4
        elif val == 'v5' or val == '5':
            urlVersion = 5
        elif val == 'v6' or val == '6':
            urlVersion = 6
        else:
            print('Invalid URL version: {}'.format(val))

    print('\nUsing URL version {}\n'.format(urlVersion))
    return urlVersion


def app_platform():
    appPlatform = None
    if args.appPlatform:
        if "64" in args.appPlatform:
            appPlatform = "win64"
            print('\nUsing provided version: ' + appPlatform)
        elif "32" in args.appPlatform:
            appPlatform = "win32"
            print('\nUsing provided version: ' + appPlatform)
        else:
            print('Invalid argument "{}" for {}'.format(args.appPlatform, 'application platform'))
            exit(1)
    
    while not appPlatform:
        val = input('Please enter application platform (eg win32), or nothing for win64: ') or 'win64'
        if val == 'win32':
            appPlatform = 'win32'
        elif val == 'win64':
            appPlatform = 'win64'
        else:
            print('Invalid platform: {}'.format(val))
    
    print('\nGetting {} products\n'.format(appPlatform))
    return appPlatform


def product_code(sapCodes):
    selectedCode = args.sapCode
    if not selectedCode:
        for s, d in sapCodes.items():
            print('[{}]{}{}'.format(s, (10 - len(s)) * ' ', d))

        while selectedCode is None:
            val = input('\nPlease enter the SAP Code of the desired product from the list above: ').upper()
            if products.get(val):
                selectedCode = val
            elif val == '':
                print('No product selected! Please use a value from the list above.')
            else:
                print('{} is not available! Please use a value from the list above.'.format(val))
    return selectedCode


def product_version(product, versions):
    version = None
    if (args.version):
        if versions.get(args.version):
            print('\nUsing provided version: ' + args.version)
            version = args.version
        else:
            print('\nProvided version not found: ' + args.version)

    print('')

    if not version:
        lastVersion = None
        for v in reversed(versions.values()):
            if v['buildGuid'] and v['apPlatform'] in allowedPlatforms:
                print('{} Platform: {} - {}'.format(product['displayName'], v['apPlatform'], v['productVersion']))
                lastVersion = v['productVersion']

        while version is None:
            val = input('\nPlease enter the desired version. Nothing for ' + lastVersion + ': ') or lastVersion
            if versions.get(val):
                version = val
            else:
                print('{} is not a valid version. Please use a value from the list above.'.format(val))

    print('\nPrepare to download Adobe {}, version {}'.format(product['displayName'], version))
    return version


def install_language(supportedLangs):
    if 'mul' in supportedLangs:
        supportedLangs[supportedLangs.index('mul')] = 'All'
    else:
        if 'All' not in supportedLangs:
            supportedLangs.append('All')

    supportedLangs.sort()

    # Detecting Current set default Os language. Fixed.
    windll = ctypes.windll.kernel32
    osLang = locale.windows_locale[ windll.GetUserDefaultUILanguage() ]

    if args.osLanguage:
        osLang = args.osLanguage

    defLang = 'All'
    if osLang in supportedLangs:
        defLang = osLang

    installLanguage = None
    if args.installLanguage:
        if args.installLanguage in supportedLangs:
            print('\nUsing provided language: ' + args.installLanguage)
            installLanguage = args.installLanguage
        else:
            print('\nProvided language not available: ' + args.installLanguage)

    if not installLanguage:
        print('\nAvailable languages: {}'.format(', '.join(supportedLangs)))
        while installLanguage is None:
            val = input(
                f'\nPlease enter the desired install language, or nothing for [{defLang}]: ') or defLang
            if len(val) == 5:
                val = val[0:2].lower() + val[2] + val[3:5].upper()
            elif len(val) == 3:
                val = val[0].upper() + val[1:].lower()
            if val in supportedLangs:
                installLanguage = val
            else:
                print(
                    '{} is not available. Please use a value from the list above.'.format(val))

    if osLang != installLanguage:
        if installLanguage != 'All':
            while osLang not in supportedLangs:
                print('Could not detect your default Language.')
                osLang = input(
                    f'\nPlease enter the your OS Language, or nothing for [{installLanguage}]: ') or installLanguage
                if osLang not in supportedLangs:
                    print(
                        '{} is not available. Please use a value from the list above.'.format(osLang))

    print('\nDownloading packages with {} language'.format(installLanguage))
    return installLanguage


def parse_products_xml(products_url, url_version, allowed_platform, selected_platform):
    # get xml data
    #print('Using existing products.xml\n')
    #products_xml = ET.parse('products.xml')
    print('Downloading product data\n')
    response = session.get(products_url, stream=True, headers=ADOBE_REQ_HEADERS)
    response.encoding = 'utf-8'
    products_xml = ET.fromstring(response.content)
    # to study
    #with open('products.xml', 'wb+') as f:
    #    f.write(response.content)
    
    """2nd stage of parsing the XML."""
    if url_version == 6:
        prefix = 'channels/'
    else:
        prefix = ''
    cdn = products_xml.find(prefix + 'channel/cdn/secure').text
    products = {}
    parent_map = {c: p for p in products_xml.iter() for c in p}
    for p in products_xml.findall(prefix + 'channel/products/product'):
        sap = p.get('id')
        hidden = parent_map[parent_map[p]].get('name') != 'ccm'
        displayName = p.find('displayName').text
        productVersion = p.get('version')
        
        if not products.get(sap):
            products[sap] = {
                'hidden': hidden,
                'displayName': displayName,
                'sapCode': sap,
                'versions': OrderedDict()
            }
        
        #icon for main application
        icons = []
        if len(p.find('productIcons')):
            for icon in p.findall('productIcons/icon'):
                icons.append(icon.text)

        for pf in p.findall('platforms/platform'):
            baseVersion = pf.find('languageSet').get('baseVersion')
            buildGuid = pf.find('languageSet').get('buildGuid')
            appPlatform = pf.get('id')
            dependencies = list(pf.findall('languageSet/dependencies/dependency'))

            # filter by platform
            if sap == 'APRO' and appPlatform != selected_platform:
                break
            
            if sap == 'APRO':
                baseVersion = productVersion
                if url_version == 4 or url_version == 5:
                    productVersion = pf.find('languageSet/nglLicensingInfo/appVersion').text
                if url_version == 6:
                    for b in products_xml.findall('builds/build'):
                        if b.get("id") == sap and b.get("version") == baseVersion:
                            productVersion = b.find('nglLicensingInfo/appVersion').text
                            break
                buildGuid = pf.find('languageSet/urls/manifestURL').text
                # This is actually manifest URL
                
            languageSet = pf.findall('languageSet/locales/locale')
            supportedLang = []
            for locale in languageSet:
                supportedLang.append(locale.get('name'))

            # filter products for allowed platform
            if appPlatform in allowed_platform:
                products[sap]['versions'][productVersion] = {
                    'sapCode': sap,
                    'displayName': displayName,
                    'baseVersion': baseVersion,
                    'productVersion': productVersion,
                    'productIcons': icons,
                    'supportedLanguages': supportedLang,
                    'apPlatform': appPlatform,
                    'dependencies': [{
                        'sapCode': d.find('sapCode').text, 'version': d.find('baseVersion').text
                    } for d in dependencies],
                    'buildGuid': buildGuid
                }
    return products, cdn


def get_products():
    selectedVersion = url_version()
    selectedPlatform = app_platform()
    
    if args.Auth:
        ADOBE_REQ_HEADERS['Authorization'] = args.Auth

    allowedPlatforms = [selectedPlatform]
    productsPlatform = selectedPlatform
    if selectedPlatform == 'win64':
        allowedPlatforms.append('win32')
        productsPlatform += ',win32'
    
    products_xml_url = ADOBE_PRODUCTS_XML_URL.format(urlVersion=selectedVersion, installPlatform=productsPlatform)
    # download and parse product xml
    products, cdn = parse_products_xml(products_xml_url, selectedVersion, allowedPlatforms, selectedPlatform)
    
    sapCodes = {}
    for p in products.values():
        if not p['hidden']:
            versions = p['versions']
            lastVersion = None
            for v in reversed(versions.values()):
                if v['buildGuid'] and v['apPlatform'] in allowedPlatforms:
                    lastVersion = v['productVersion']
            if lastVersion:
                sapCodes[p['sapCode']] = p['displayName']
    print(str(len(sapCodes)) + ' products found:')

    if args.sapCode and products.get(args.sapCode.upper()) is None:
        print('\nProvided SAP Code not found in products: ' + args.sapCode)
        exit(1)

    return products, cdn, sapCodes, allowedPlatforms


def get_download_path():
    """Ask for desired download folder"""
    if (args.destination):
        print('\nUsing provided destination: ' + args.destination + '\n')
        dest = args.destination
    else:
        print('\nDownloaded file will be put on current location.\n')
        dest = os.path.dirname(os.path.realpath(__name__))
    return dest


def download_progress(url, dest_dir, prefix=''):
    response = session.get(
            url, stream=True, headers=ADOBE_REQ_HEADERS)
    total_size_in_bytes = int(
            response.headers.get('content-length', 0))
    if (total_size_in_bytes > 0):
        block_size = 1024  # 1 Kibibyte
        progress_bar = tqdm(total=total_size_in_bytes,
                            unit='iB', unit_scale=True)
        if prefix:
            name = prefix + os.path.basename(url)
            dest_dir = dest_dir + '\\' + name
        with open(dest_dir, 'wb') as file:
            for data in response.iter_content(block_size):
                progress_bar.update(len(data))
                file.write(data)
        progress_bar.close()
        if total_size_in_bytes != 0 and progress_bar.n != total_size_in_bytes:
            print("ERROR, something went wrong")


def icons_download(product, dest_dir):
    """Download product icons"""
    print('Downloading product icons\n')
    
    icon_dir = os.path.join(dest_dir, 'icons')
    os.makedirs(icon_dir, exist_ok=True)
    
    icons = product['productIcons']
    prefix = product['sapCode'].lower()
    for url in icons:
        download_progress(url, icon_dir, prefix)


def file_download(url, dest_dir, s, v, name=None):
    """Download a product package"""
    if not name:
        name = os.path.basename(url)
    print('[{}_{}] Downloading {}'.format(s, v, name))
    file_path = os.path.join(dest_dir, name)
    response = session.head(url, stream=True, headers=ADOBE_DL_HEADERS)
    total_size_in_bytes = int(
        response.headers.get('content-length', 0))
    if (args.skipExisting and os.path.isfile(file_path) and os.path.getsize(file_path) == total_size_in_bytes):
        print('[{}_{}] {} already exists, skipping\n'.format(s, v, name))
    else:
        download_progress(url, file_path)


def download_APRO(appInfo, cdn):
    """Download APRO"""
    # download manifest.xml
    response = session.get(cdn + appInfo['buildGuid'], stream=True, headers=ADOBE_REQ_HEADERS)
    response.encoding = 'utf-8'
    # to study
    #with open('manifest.xml', 'wb+') as f:
    #    f.write(response.content)
    manifest = ET.fromstring(response.text)

    # for full app
    assetList = manifest.find('app_modes/app_mode/asset_list')
    for asset in assetList:
        if asset.find('asset_type').text == 'EXE':
            downloadURL = asset.find('asset_path').text
        
    # for update
    #downloadURL = manifest.find('asset_list/asset/asset_path').text
    
    dest = get_download_path()
    sapCode = appInfo['sapCode']
    version = appInfo['productVersion']
    name = os.path.basename(downloadURL)

    print('')
    print('dest: ' + os.path.join(dest, name))

    print('\nDownloading...\n')

    print('[{}_{}] Selected 1 package'.format(sapCode, version))
    file_download(downloadURL, dest, sapCode, version, name)

    print('\nInstaller successfully downloaded.')
    return    


def get_application_json(buildGuid):
    """Retrieve JSON."""
    headers = ADOBE_REQ_HEADERS.copy()
    headers['x-adobe-build-guid'] = buildGuid
    response = session.get(ADOBE_APPLICATION_JSON_URL, headers=headers)
    response.encoding = 'utf-8'
    return json.loads(response.content)


def save_application_json(package_dir, json_data):
    app_json_path = os.path.join(package_dir, 'application.json')
    with open(app_json_path, 'w+') as file:
        json.dump(json_data, file, separators=(',', ':'))


def write_driver_xml(jsonData, products_dir, prefix=""):
	driver = ET.Element('DriverInfo')
	product = ET.SubElement(driver, 'ProductInfo')

	prd_name = ET.SubElement(product, 'Name')
	prd_name.text = 'Adobe ' + jsonData['Name']

	sap_code = ET.SubElement(product, 'SAPCode')
	sap_code.text = jsonData['SAPCode']

	cod_ver = ET.SubElement(product, 'CodexVersion')
	cod_ver.text = jsonData['CodexVersion']

	base_ver = ET.SubElement(product, 'BaseVersion')
	base_ver.text = jsonData['BaseVersion']

	platform = ET.SubElement(product, 'Platform')
	platform.text = jsonData['Platform']

	esd_dir = ET.SubElement(product, 'EsdDirectory')
	esd_dir.text = './' + jsonData['SAPCode']

	if 'Dependencies' in jsonData:
		dep_top = ET.SubElement(product, 'Dependencies')
		for dependency in jsonData['Dependencies']['Dependency']:
			dep_sub = ET.SubElement(dep_top, 'Dependency')
			dep_code = ET.SubElement(dep_sub, 'SAPCode')
			dep_code.text = dependency['SAPCode']
			dep_base = ET.SubElement(dep_sub, 'BaseVersion')
			dep_base.text = dependency['BaseVersion']
			dep_dir = ET.SubElement(dep_sub, 'EsdDirectory')
			dep_dir.text = './' + dependency['SAPCode']

	tree = ET.ElementTree(driver)
	ET.indent(tree, space="    ", level=0)
	xml_file = os.path.join(products_dir, prefix + 'driver.xml')
	tree.write(xml_file, encoding='utf-8', xml_declaration=True)


def condition_check(condition, language):
    if 'installLanguage' in condition:
        if language == 'All':
            return True
        else:
            if language in condition:
                return True
	
    if 'OSProcessorFamily' in condition:
        # lock on 64 bit os
        processor = '64-bit'
        if processor in condition:
            return True

    return False

    
def language_for_premiere(language):
    if '_' in language:
        main, locale = language.split('_')
        return '-esl_lp_' + main
    return language

        
def package_filter(package, language):
    coreCount = 0
    noneCoreCount = 0
    newPackage = []
    urlPath = []
    for pkg in package:
        if pkg.get('Type') and pkg['Type'] == 'core':
            if 'Condition' in pkg:
                condition = pkg['Condition']
                if condition_check(condition, language):
                    newPackage.append(pkg)
                    urlPath.append(pkg['Path'])
                    coreCount += 1
            else:
                newPackage.append(pkg)
                urlPath.append(pkg['Path'])
                coreCount += 1

        else:
            if 'Condition' in pkg:
                condition = pkg['Condition']
                if condition_check(condition, language):
                    newPackage.append(pkg)
                    urlPath.append(pkg['Path'])
                    noneCoreCount += 1
            else:
				# for premiere pro
                if '-esl_lp_' in pkg['PackageName']:
                    if language_for_premiere(language) in pkg['PackageName']:
                        newPackage.append(pkg)
                        urlPath.append(pkg['Path'])
                        noneCoreCount += 1
                else:
                    newPackage.append(pkg)
                    urlPath.append(pkg['Path'])
                    noneCoreCount += 1
    print('Selected {} core packages and {} non-core packages'.format(coreCount, noneCoreCount))
    return urlPath, newPackage


def dependencies_download(dep_data, products_dir):
    dep_dir = os.path.join(products_dir, dep_data['sapCode'])
    os.makedirs(dep_dir, exist_ok=True)
    dep_data = list(dep_data['versions'].values())
    firstItem = dep_data[0]    
    dep_json = get_application_json(firstItem['buildGuid'])
    package_download(dep_json, dep_dir)


def package_download(app_json, package_dir, language='All'):
    allPackages = app_json['Packages']['Package']
    cdn = app_json['Cdn']['Secure']
    sapCode = app_json['SAPCode']
    version = app_json['ProductVersion']
    urls, package = package_filter(allPackages, language)

    # filtered json data
    app_json['Packages']['Package'] = package
    
    print('\nCreate application.json\n')
    save_application_json(package_dir, app_json)
    for url in urls:
        file_download(cdn + url, package_dir, sapCode, version)
    


def run_ccdl(products, cdn, sapCodes, allowedPlatforms):
    """Run Main execution."""
    # get product list
    sapCode = product_code(sapCodes)
    product = products.get(sapCode)
    
    # version select
    versions = product['versions']
    selectedVersion = product_version(product, versions)
    
    # product to download
    prodInfo = versions[selectedVersion]
    
    # language select
    supportedLangs = prodInfo['supportedLanguages']
    installLanguage = install_language(supportedLangs)
    
    # acrobat download
    if sapCode == 'APRO':
        download_APRO(prodInfo, cdn)
        return
    
    # main product
    print('\nPrepare to download Adobe {}-{}-{}-{}'.format(prodInfo['displayName'], prodInfo['productVersion'], installLanguage, prodInfo['apPlatform']))
    
    dest = get_download_path()
    
    #download icons
    icons_download(prodInfo, dest)
    
    # create products directory
    products_dir = os.path.join(dest, 'products')
    os.makedirs(products_dir, exist_ok=True)
    package_dir = os.path.join(products_dir, sapCode)
    os.makedirs(package_dir, exist_ok=True)
    
    app_json = get_application_json(prodInfo['buildGuid'])
    
    package_download(app_json, package_dir, installLanguage)
    
    if 'Dependencies' in app_json:
        for dependency in app_json['Dependencies']['Dependency']:
            depSap = dependency['SAPCode']
            depPackage = products.get(depSap)
            dependencies_download(depPackage, products_dir)
    
    print('\nGenerating driver.xml')
    prefix = app_json['SAPCode'] + '-'
    write_driver_xml(app_json, products_dir, prefix)
    
    return


if __name__ == '__main__':
    show_version()

    parser = argparse.ArgumentParser()
    parser.add_argument('-l', '--installLanguage',
                        help='Language code (eg. en_US)', action='store')
    parser.add_argument('-o', '--osLanguage',
                        help='OS Language code (eg. en_US)', action='store')
    parser.add_argument('-p', '--appPlatform',
                        help='Application platform (eg. win64)', action='store')
    parser.add_argument('-s', '--sapCode',
                        help='SAP code for desired product (eg. PHSP)', action='store')
    parser.add_argument('-v', '--version',
                        help='Version of desired product (eg. 21.0.3)', action='store')
    parser.add_argument('-d', '--destination',
                        help='Directory to download installation files to', action='store')
    parser.add_argument('-u', '--urlVersion',
                        help="Get app info from v4/v5/v6 url (eg. v6)", action='store')
    parser.add_argument('-A', '--Auth',
                        help='Add a bearer_token to to authenticate your account, e.g. downloading Xd', action='store')
    parser.add_argument('--noRepeatPrompt',
                        help="Don't prompt for additional downloads", action='store_true')
    parser.add_argument('-x', '--skipExisting',
                        help="Skip existing files, e.g. resuming failed downloads", action='store_true')
    args = parser.parse_args()
    
    products, cdn, sapCodes, allowedPlatforms = get_products()
    
    while True:
        run_ccdl(products, cdn, sapCodes, allowedPlatforms)
        if args.noRepeatPrompt or not questiony('\n\nDo you want to download another package'):
            break
