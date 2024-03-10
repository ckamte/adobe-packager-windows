# Usage

```
python ccdl-win.py -h
python ccdl-win.py -u 6 -l All -x
python ccdl-win.py -u 6 -l en_US -p win64 -x
```

## Installer for stanalone product

1. Get old working installer
2. Replace all files and folder in /products
3. Rename \products\*prefix*-Driver.xml to Driver.xml
4. Check dependency packages are in \products folder (dependencies can be found in Driver.xml)
5. Replace \resources\content\images icons
6. Run Set-up.exe
