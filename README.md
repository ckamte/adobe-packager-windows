## Prerequisites

1. You need Python environment to run the commands.
2. Go to ```https://www.python.org/downloads/``` and install the latest version.

## Usage

```
python ccdl-win.py -h
python ccdl-win.py -u 6 -l All -x
python ccdl-win.py -u 6 -l en_US -p win64 -x
```

## Installer for standalone product

1. Get old working installer
2. Replace all files and folder in \products
3. Rename \products\\*prefix*-Driver.xml to Driver.xml
4. Check dependency packages are in \products folder (dependencies can be found in Driver.xml)
5. Rename and replace icons in \resources\content\images (96x96.png to appicon.png 122x192.png to appicon2x.png)
6. Run Set-up.exe

## Create manually
1. Extract Set-up.exe file to current folder (v4 setup not support win10)
3. Download desire package with ccdl-win
4. Rename \products\\*prefix*-Driver.xml to Driver.xml
5. Download packages for installer using installer.py
   ```
   python build_installer.py
   ```
6. New folder "packages" will appear.
7. Delete downloaded zip files in "packages" directory to reduce installer size
8. Rename and replace icons in \resources\content\images (from icons folder \*prefix*96x96.png to appicon.png \*prefix*122x192.png to appicon2x.png)
9. Run Set-up.exe

~~## Install with CCMaker~~
~~You can also install with ccmaker.exe (tested with v-1.3.16.0). *Crack won't work*.~~
~~1. Rename desired \products\\*prefix*-Driver.xml to Driver.xml~~
~~2. Run CCMaker and select Driver.xml.~~
