#!/usr/bin/env python3
"""
This is the Adobe Offline Package downloader for Windows.

original file
https://github.com/Drovosek01/adobe-packager

"""

import argparse
import json
import locale
import os
import random
import string
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

session = requests.sessions.Session()

VERSION = 4
VERSION_STR = '0.2.0'
CODE_QUALITY = 'Mildly_AWFUL'

ADOBE_PRODUCTS_XML_URL = 'https://prod-rel-ffc-ccm.oobesaas.adobe.com/adobe-ffc-external/core/v{urlVersion}/products/all?_type=xml&channel=ccm&channel=sti&platform={installPlatform}&productType=Desktop'
ADOBE_APPLICATION_JSON_URL = 'https://cdn-ffc.oobesaas.adobe.com/core/v3/applications'

DRIVER_XML = '''<DriverInfo>
    <ProductInfo>
        <Name>Adobe {name}</Name>
        <SAPCode>{sapCode}</SAPCode>
        <CodexVersion>{version}</CodexVersion>
		<BaseVersion>{baseVersion}</BaseVersion>
        <Platform>{installPlatform}</Platform>
        <EsdDirectory>./{sapCode}</EsdDirectory>
        <Dependencies>
{dependencies}
        </Dependencies>
    </ProductInfo>
    <RequestInfo>
        <InstallDir>{installDir}\Adobe</InstallDir>
        <InstallLanguage>{language}</InstallLanguage>
    </RequestInfo>
</DriverInfo>
'''

DRIVER_XML_DEPENDENCY = '''         <Dependency>
                <SAPCode>{sapCode}</SAPCode>
                <BaseVersion>{version}</BaseVersion>
                <EsdDirectory>./{sapCode}</EsdDirectory>
            </Dependency>'''

ADOBE_REQ_HEADERS = {
    'X-Adobe-App-Id': 'accc-apps-panel-desktop',
    'User-Agent': 'Adobe Application Manager 2.0',
    'X-Api-Key': 'CC_HD_ESD_1_0',
    'Cookie': 'fg=' + ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(26)) + '======'
}

ADOBE_DL_HEADERS = {
    'User-Agent': 'Creative Cloud'
}

def get_install_dir():
	return os.environ["ProgramFiles"]

def r(url, headers=ADOBE_REQ_HEADERS):
    """Retrieve a from a url as a string."""
    req = session.get(url, headers=headers)
    req.encoding = 'utf-8'
    #with open('1.xml', 'wb+') as f:
    #    f.write(req.content)
    return req.text


def get_products_xml(adobeurl):
    """First stage of parsing the XML."""
    print('Source URL is: ' + adobeurl)
    return ET.fromstring(r(adobeurl))


def parse_products_xml(products_xml, urlVersion):
    """2nd stage of parsing the XML."""
    if urlVersion == 6:
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

        icons = []
        if p.find('productIcons'):
            for icon in p.findall('productIcons/icon'):
                icons.append(icon.text)

        for pf in p.findall('platforms/platform'):
            baseVersion = pf.find('languageSet').get('baseVersion')
            buildGuid = pf.find('languageSet').get('buildGuid')
            appplatform = pf.get('id')
            dependencies = list(pf.findall('languageSet/dependencies/dependency'))

            if sap == 'APRO':
                baseVersion = productVersion
                if urlVersion == 4 or urlVersion == 5:
                    productVersion = pf.find('languageSet/nglLicensingInfo/appVersion').text
                if urlVersion == 6:
                    for b in products_xml.findall('builds/build'):
                        if b.get("id") == sap and b.get("version") == baseVersion:
                            productVersion = b.find('nglLicensingInfo/appVersion').text
                            break
                buildGuid = pf.find('languageSet/urls/manifestURL').text
                # This is actually manifest URL

            products[sap]['versions'][productVersion] = {
                'sapCode': sap,
                'baseVersion': baseVersion,
                'productVersion': productVersion,
                'productIcons': icons,
                'apPlatform': appplatform,
                'dependencies': [{
                    'sapCode': d.find('sapCode').text, 'version': d.find('baseVersion').text
                } for d in dependencies],
                'buildGuid': buildGuid
            }
    return products, cdn


def questiony(question: str) -> bool:
    """Question prompt default Y."""
    reply = None
    while reply not in ("", "y", "n"):
        reply = input(f"{question} (Y/n): ").lower()
    return (reply in ("", "y"))


def questionn(question: str) -> bool:
    """Question prompt default N."""
    reply = None
    while reply not in ("", "y", "n"):
        reply = input(f"{question} (y/N): ").lower()
    return (reply in ("y", "Y"))


def get_application_json(buildGuid):
    """Retrieve JSON."""
    headers = ADOBE_REQ_HEADERS.copy()
    headers['x-adobe-build-guid'] = buildGuid
    return json.loads(r(ADOBE_APPLICATION_JSON_URL, headers))


def get_download_path():
    """Ask for desired download folder"""
    if (args.destination):
        print('\nUsing provided destination: ' + args.destination)
        dest = args.destination
    else:
        print('\nDownloaded file will be put on current location.')
        dest = os.path.dirname(os.path.realpath(__name__))
    return dest


def download_icons(icons, icon_dir):
    print('Downloading application icons')
    if not os.path.exists(icon_dir):
        os.makedirs(icon_dir)
    for url in icons:
        response = session.get(
            url, stream=True, headers=ADOBE_REQ_HEADERS)
        total_size_in_bytes = int(
            response.headers.get('content-length', 0))
        if (total_size_in_bytes > 0):
            block_size = 1024  # 1 Kibibyte
            progress_bar = tqdm(total=total_size_in_bytes,
                                unit='iB', unit_scale=True)
            name = url.split('/')[-1].split('?')[0]
            file_path = os.path.join(icon_dir, name)
            with open(file_path, 'wb') as file:
                for data in response.iter_content(block_size):
                    progress_bar.update(len(data))
                    file.write(data)
            progress_bar.close()


def download_file(url, product_dir, s, v, name=None):
    """Download a file"""
    if not name:
        name = url.split('/')[-1].split('?')[0]
    print('Url is: ' + url)
    print('[{}_{}] Downloading {}'.format(s, v, name))
    file_path = os.path.join(product_dir, name)
    response = session.head(url, stream=True, headers=ADOBE_DL_HEADERS)
    total_size_in_bytes = int(
        response.headers.get('content-length', 0))
    if (args.skipExisting and os.path.isfile(file_path) and os.path.getsize(file_path) == total_size_in_bytes):
        print('[{}_{}] {} already exists, skipping'.format(s, v, name))
    else:
        response = session.get(
            url, stream=True, headers=ADOBE_REQ_HEADERS)
        total_size_in_bytes = int(
            response.headers.get('content-length', 0))
        block_size = 1024  # 1 Kibibyte
        progress_bar = tqdm(total=total_size_in_bytes,
                            unit='iB', unit_scale=True)
        with open(file_path, 'wb') as file:
            for data in response.iter_content(block_size):
                progress_bar.update(len(data))
                file.write(data)
        progress_bar.close()
        if total_size_in_bytes != 0 and progress_bar.n != total_size_in_bytes:
            print("ERROR, something went wrong")


def download_APRO(appInfo, cdn):
    """Download APRO"""
    manifest = get_products_xml(cdn + appInfo['buildGuid'])
    downloadURL = manifest.find('asset_list/asset/asset_path').text
    dest = get_download_path()
    sapCode = appInfo['sapCode']
    version = appInfo['productVersion']
    name = '{}_{}_{}.exe'.format(sapCode, version, appInfo['apPlatform'])
    print('')
    print('sapCode: ' + sapCode)
    print('version: ' + version)
    print('installLanguage: ' + 'ALL')
    print('dest: ' + os.path.join(dest, name))

    print('\nDownloading...\n')

    print('[{}_{}] Selected 1 package'.format(sapCode, version))
    download_file(downloadURL, dest, sapCode, version, name)

    print('\nInstaller successfully downloaded.')
    return


def show_version():
    ye = int((32 - len(VERSION_STR)) / 2)
    print('=================================')
    print('=  Adobe CC Package Downloader  =')
    print('{} {} {}\n'.format('=' * ye, VERSION_STR,
          '=' * (31 - len(VERSION_STR) - ye)))


def get_products():
    selectedVersion = None
    if args.urlVersion:
        if args.urlVersion.lower() == "v4" or args.urlVersion == "4":
            selectedVersion = 4
        elif args.urlVersion.lower() == "v5" or args.urlVersion == "5":
            selectedVersion = 5
        elif args.urlVersion.lower() == "v6" or args.urlVersion == "6":
            selectedVersion = 6
        else:
            print('Invalid argument "{}" for {}'.format(args.urlVersion, 'URL version'))
            exit(1)

    while not selectedVersion:
        val = input('\nPlease enter the URL version(v4/v5/v6) for downloading products.xml, or nothing for v6: ') or 'v6'
        if val == 'v4' or val == '4':
            selectedVersion = 4
        elif val == 'v5' or val == '5':
            selectedVersion = 5
        elif val == 'v6' or val == '6':
            selectedVersion = 6
        else:
            print('Invalid URL version: {}'.format(val))
    print('')

    if args.Auth:
        ADOBE_REQ_HEADERS['Authorization'] = args.Auth

    allowedPlatforms = ['win64', 'win32']

    productsPlatform = 'win32,win64'
    adobeurl = ADOBE_PRODUCTS_XML_URL.format(urlVersion=selectedVersion, installPlatform=productsPlatform)

    print('\nDownloading products.xml\n')
    products_xml = get_products_xml(adobeurl)

    print('\nParsing products.xml\n')
    products, cdn = parse_products_xml(products_xml, selectedVersion)

    print('CDN: ' + cdn)
    sapCodes = {}
    for p in products.values():
        if not p['hidden']:
            versions = p['versions']
            lastv = None
            for v in reversed(versions.values()):
                if v['buildGuid'] and v['apPlatform'] in allowedPlatforms:
                    lastv = v['productVersion']
            if lastv:
                sapCodes[p['sapCode']] = p['displayName']
    print(str(len(sapCodes)) + ' products found:')

    if args.sapCode and products.get(args.sapCode.upper()) is None:
        print('\nProvided SAP Code not found in products: ' + args.sapCode)
        exit(1)

    return products, cdn, sapCodes, allowedPlatforms

'''
def condition_check(condition, language):
    if 'installLanguage' in condition:
        if language == 'ALL':
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

def package_filter(package, language):
	newPackage = []

	for pkg in package:
		if pkg.get('Type') and pkg['Type'] == 'core':
			if 'Condition' in pkg:
				condition = pkg['Condition']
				if condition_check(condition, language):
					newPackage.append(pkg)
			else:
				newPackage.append(pkg)

		else:
			if 'Condition' in pkg:
				condition = pkg['Condition']
				if condition_check(condition, language):
					newPackage.append(pkg)
			else:
				# for premiere pro
				if '-esl_lp_' in pkg['PackageName']:
					if language_for_premiere(language) in pkg['PackageName']:
						newPackage.append(pkg)
				
				else:
					newPackage.append(pkg)
	return newPackage
'''

def run_ccdl(products, cdn, sapCodes, allowedPlatforms):
    """Run Main execution."""
    sapCode = args.sapCode
    if not sapCode:
        for s, d in sapCodes.items():
            print('[{}]{}{}'.format(s, (10 - len(s)) * ' ', d))

        while sapCode is None:
            val = input(
                '\nPlease enter the SAP Code of the desired product (eg. PHSP for Photoshop): ').upper() or 'PHSP'
            if products.get(val):
                sapCode = val
            else:
                print(
                    '{} is not a valid SAP Code. Please use a value from the list above.'.format(val))

    product = products.get(sapCode)
    versions = product['versions']
    version = None
    if (args.version):
        if versions.get(args.version):
            print('\nUsing provided version: ' + args.version)
            version = args.version
        else:
            print('\nProvided version not found: ' + args.version)

    print('')

    if not version:
        lastv = None
        for v in reversed(versions.values()):

            if v['buildGuid'] and v['apPlatform'] in allowedPlatforms:
                print('{} Platform: {} - {}'.format(product['displayName'], v['apPlatform'], v['productVersion']))
                lastv = v['productVersion']

        while version is None:
            val = input('\nPlease enter the desired version. Nothing for ' + lastv + ': ') or lastv
            if versions.get(val):
                version = val
            else:
                print('{} is not a valid version. Please use a value from the list above.'.format(val))
    print('')

    if sapCode == 'APRO':
        download_APRO(versions[version], cdn)
        return

    # TODO: Parase languages in the xml
    langs = ['en_US', 'en_GB', 'en_IL', 'en_AE', 'es_ES', 'es_MX', 'pt_BR', 'fr_FR', 'fr_CA', 'fr_MA', 'it_IT', 'de_DE', 'nl_NL',
             'ru_RU', 'uk_UA', 'zh_TW', 'zh_CN', 'ja_JP', 'ko_KR', 'pl_PL', 'hu_HU', 'cs_CZ', 'tr_TR', 'sv_SE', 'nb_NO', 'fi_FI', 'da_DK', 'ALL']
    # Detecting Current set default Os language. Fixed.
    defLang = locale.getlocale()[0]
    if not defLang:
        defLang = 'en_US'

    oslang = None
    if args.osLanguage:
        oslang = args.osLanguage
    elif defLang:
        oslang = defLang

    if oslang in langs:
        deflang = oslang
    else:
        deflang = 'en_US'

    installLanguage = None
    if args.installLanguage:
        if args.installLanguage in langs:
            print('\nUsing provided language: ' + args.installLanguage)
            installLanguage = args.installLanguage
        else:
            print('\nProvided language not available: ' + args.installLanguage)

    if not installLanguage:
        print('Available languages: {}'.format(', '.join(langs)))
        while installLanguage is None:
            val = input(
                f'\nPlease enter the desired install language, or nothing for [{deflang}]: ') or deflang
            if len(val) == 5:
                val = val[0:2].lower() + val[2] + val[3:5].upper()
            elif len(val) == 3:
                val = val.upper()
            if val in langs:
                installLanguage = val
            else:
                print(
                    '{} is not available. Please use a value from the list above.'.format(val))
    if oslang != installLanguage:
        if installLanguage != 'ALL':
            while oslang not in langs:
                print('Could not detect your default Language.')
                oslang = input(
                    f'\nPlease enter the your OS Language, or nothing for [{installLanguage}]: ') or installLanguage
                if oslang not in langs:
                    print(
                        '{} is not available. Please use a value from the list above.'.format(oslang))

    dest = get_download_path()

    print('')

    prodInfo = versions[version]
    prods_to_download = []
    dependencies = prodInfo['dependencies']
    for d in dependencies:
        firstGuid = buildGuid = None
        for p in products[d['sapCode']]['versions']:
            if products[d['sapCode']]['versions'][p]['baseVersion'] == d['version']:
                if not firstGuid:
                    firstGuid = products[d['sapCode']]['versions'][p]['buildGuid']
                if products[d['sapCode']]['versions'][p]['apPlatform'] in allowedPlatforms:
                    buildGuid = products[d['sapCode']]['versions'][p]['buildGuid']
                    break
        if not buildGuid:
            buildGuid = firstGuid
        prods_to_download.append({'sapCode': d['sapCode'], 'version': d['version'],
                                  'buildGuid': buildGuid})

    prods_to_download.insert(
        0, {'sapCode': prodInfo['sapCode'], 'version': prodInfo['productVersion'], 'buildGuid': prodInfo['buildGuid'], 'productIcons': prodInfo['productIcons']})
    apPlatform = prodInfo['apPlatform']
    install_app_name = '{}_{}-{}-{}'.format(
        sapCode, version, installLanguage, apPlatform)
    install_app_path = os.path.join(dest, install_app_name)
    print('sapCode: ' + sapCode)
    print('version: ' + version)
    print('installLanguage: ' + installLanguage)
    print('dest: ' + install_app_path)

    print('\nCreating {}'.format(install_app_name))

    products_dir = os.path.join(dest, 'products')

    print('\nPreparing...\n')

    for p in prods_to_download:
        s, v = p['sapCode'], p['version']
        product_dir = os.path.join(products_dir, s)
        app_json_path = os.path.join(product_dir, 'application.json')

        print('[{}_{}] Downloading application.json'.format(s, v))
        app_json = get_application_json(p['buildGuid'])

        '''
        #replace filtered result for testing
        to_filter = app_json['Packages']['Package']
        app_json['Packages']['Package'] = package_filter(to_filter, installLanguage)
        '''
        
        p['application_json'] = app_json

        print('[{}_{}] Creating folder for product'.format(s, v))
        os.makedirs(product_dir, exist_ok=True)

        print('[{}_{}] Saving application.json'.format(s, v))
        with open(app_json_path, 'w') as file:
            json.dump(app_json, file, separators=(',', ':'))

        print('')

    print('Downloading...\n')

    for p in prods_to_download:
        s, v = p['sapCode'], p['version']
        app_json = p['application_json']
        #icons directory
        icon_dir = os.path.join(products_dir, 'icons')
        product_dir = os.path.join(products_dir, s)

        print('[{}_{}] Parsing available packages'.format(s, v))
        core_pkg_count = 0
        noncore_pkg_count = 0
        packages = app_json['Packages']['Package']
        download_urls = []
        for pkg in packages:
            if pkg.get('Type') and pkg['Type'] == 'core':
                core_pkg_count += 1
                download_urls.append(cdn + pkg['Path'])
            else:
                # TODO: actually parse `Condition` and check it properly (and maybe look for & add support for conditions other than installLanguage)
                if installLanguage == "ALL":
                    noncore_pkg_count += 1
                    download_urls.append(cdn + pkg['Path'])
                else:
                    if (not pkg.get('Condition')) or installLanguage in pkg['Condition'] or oslang in pkg['Condition']:
                        noncore_pkg_count += 1
                        download_urls.append(cdn + pkg['Path'])
        print('[{}_{}] Selected {} core packages and {} non-core packages'.format(s,
              v, core_pkg_count, noncore_pkg_count))
		
        # get app icons if exist
        if 'productIcons' in p:
            productIcons = p['productIcons']
            download_icons(productIcons, icon_dir)
		
        for url in download_urls:
            download_file(url, product_dir, s, v)

    print('\nGenerating driver.xml')
	
    driver = DRIVER_XML.format(
        name=product['displayName'],
        sapCode=prodInfo['sapCode'],
        version=prodInfo['productVersion'],
		baseVersion=prodInfo['baseVersion'],
        installPlatform=apPlatform,
        dependencies='\n'.join([DRIVER_XML_DEPENDENCY.format(
            sapCode=d['sapCode'],
            version=d['version']
        ) for d in prodInfo['dependencies']]),
		installDir=get_install_dir(),
        language=installLanguage
    )

    with open(os.path.join(products_dir, f'{sapCode}-driver.xml'), 'w') as f:
        f.write(driver)
        f.close()

    print('\nPackage successfully downloaded.')
    return


if __name__ == '__main__':
    show_version()

    parser = argparse.ArgumentParser()
    parser.add_argument('-l', '--installLanguage',
                        help='Language code (eg. en_US)', action='store')
    parser.add_argument('-o', '--osLanguage',
                        help='OS Language code (eg. en_US)', action='store')
    parser.add_argument('-s', '--sapCode',
                        help='SAP code for desired product (eg. PHSP)', action='store')
    parser.add_argument('-v', '--version',
                        help='Version of desired product (eg. 21.0.3)', action='store')
    parser.add_argument('-d', '--destination',
                        help='Directory to download installation files to', action='store')
    parser.add_argument('-a', '--arch',
                        help='Set the architecture to download', action='store')
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
        if args.noRepeatPrompt or not questiony('\n\nDo you want to create another package'):
            break
