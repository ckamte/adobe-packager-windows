## Prerequisites

1. You need Python environment to run the commands.
2. Go to ```https://www.python.org/downloads/``` and install the latest version.

## Usage

```
python ccdl-win.py -h
python ccdl-win.py -u 6 -l All -x
python ccdl-win.py -u 6 -l en_US -p win64 -x
```

## Create manually

1. Extract the whole branch to a working folder and pick one Set-up.exe version and extract it to the same folder. (v4 setup not support win10)
2. Download desire product using ccdl-win.py (creates "products" folder inside the working folder)
3. Download ACC packages for the installer using build_installer.py (creates "packages" folder inside the working folder)
4. Rename \products\\*prefix*-Driver.xml to Driver.xml (For multiple products, rename ONE product prefix to Driver.xml to install it) ~~until I figure out how to merge driver.xml files~~
5. Along the "packages" folder, a new "acc_sources" folder will be created as well (this contains the zip files of the ACC packages which were extracted before)
6. Optional - Delete downloaded zip files in "acc_sources" directory to reduce installer size (Not necessary because omitting the folder if the whole installation is packed is valid and if kept, used for other products)
7. Run Set-up.exe to install the product.
8. Note - Make sure AdobePIM.dll file version in "resources" folder matches the Set-Up.exe file version.
