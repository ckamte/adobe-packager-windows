## Folder structure:
```
.\packages
.\products
.\resources
.\Set-up.exe
```

## How to
1. Download desired products.
2. Move all packages folders to products (No need to move __prefix__Driver.xml files)
3. Copy Set-up.exe and packages files to current folder
4. Copy AdobePIM.dll to resources folder
5. Run gen-suite.py
    ```
    python gen-suite.py
    python gen-suite.py -d "./../products"
    ````
6. SuiteInfo.xml can be found in products directory. (You can manually edit too)

### Note
1. Acrobat Pro DC is not HD installer type. You can manually edit SuiteInfo.xml (use APRO.xml file) and add acrobat installer files to products folder.