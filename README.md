## Prerequisites

1. You need Python environment to run the commands.
2. Go to ```https://www.python.org/downloads/``` and install the latest version.

## Usage

```
Examples with arguments (optional):
python ccdl-win.py -h
python ccdl-win.py -u 6 -l All -x
python ccdl-win.py -u 6 -l en_US -p win64 -x

Arguments:
"-l", "--installLanguage", "Language code (eg. en_US)"
"-o", "--osLanguage", "OS Language code (eg. en_US)"
"-p", "--appPlatform", "Application platform (eg. win64)"
"-s", "--sapCode", "SAP code for desired product (eg. PHSP). For batch download use comma to separate products"
"-v", "--version", "Version of desired product (eg. 21.0.3)"
"-d", "--destination", "Directory to download installation files to"
"-u", "--urlVersion", "Get app info from v4/v5/v6 url (eg. v6)"
"-A", "--Auth", "Add a bearer_token to to authenticate your account, e.g. downloading Xd"
"-n", "--noRepeatPrompt", "Don't prompt for additional downloads"
"-i", "--productIcons", "Get app icons"
"-x", "--skipExisting", "Skip existing files, e.g. resuming failed downloads"

```

## Creation

1. Extract the whole branch to a working folder and pick one Set-up.exe version and extract it to the same folder. (v4 setup not support win10)
2. Download desire product using ccdl-win.py (creates "products" folder inside the working folder)
3. Download ACC packages for the installer using build_installer.py (creates "packages" folder inside the working folder)
4. Rename \products\\*prefix*-Driver.xml to Driver.xml (For multiple products, rename ONE product prefix to Driver.xml to install it)
5. Along the "packages" folder, a new "acc_sources" folder will be created as well (this contains the zip files of the ACC packages which were extracted before)
6. Optional - Delete downloaded zip files in "acc_sources" directory to reduce installer size (Not necessary because omitting the folder if the whole installation is packed is valid and if kept, used for other products)
7. Run Set-up.exe to install the product.
8. Note - Make sure AdobePIM.dll file version in "resources" folder matches the Set-Up.exe file version.
* It's possible to skip building the installer all together with this provided Minimal Prerequisites archive,
which contains everything needed to install any package without all the optional modules.
https://drive.google.com/file/d/1Quc2YgR85VO9_aTMo3HfvcsOXnlwSFid/view?usp=sharing

## Note

1. You can manually download CC Library package using *libs* sapcode and *kfnt* for Adobe fonts.
2. Batch download is available now. (Batch download will _now_ try to download latest version of products)
```
python ccdl-win.py -u 6 -l en_US -p win64 -s phsp,idsn,ilst -x
```
3. You can create suite like installer by using gen-suite.py (from suite_installer directory)
4. You can now add two or more languages to download.
```
python ccdl-win.py -u 6 -l en_US,fr_FR -p win64 -s phsp,idsn,ilst -x
```
