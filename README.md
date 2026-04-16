This script is a refactored version of https://github.com/Timiimiimii/TomoKoreFacepaintTool (https://gamebanana.com/tools/22280) with ZSTD compression and decompression added and some experimental icc profile stuff changed for ease of use

You need to use python 3.14 in order to get the ZSTD library from the python standard library. Otherwise the script will crash!

If you are using vs code, you can set it to use python 3.14 like this

<img width="1394" height="1088" alt="image" src="https://github.com/user-attachments/assets/bfae2bea-2bed-4ddb-a33d-d146efb36a8d" />

There's two different scripts in the script folder `canvas_converter.py` and `ugctex_converter.py`. 

## canvas_converter.py
It's for converting canvases.

Such as UgcFacePaint001.canvas.zs or UgcCloth000.canvas.zs

Simply drag and drop a png onto this script to convert a png into a .canvas.zs or a .canvas.zs to convert it into a png

## ugctex_converter.py
It's for converting textures.

Such as UgcCloth000.ugctex.zs or UgcFacePaint000.ugctex.zs

Simply drag and drop a png onto this script to convert a png into a .ugctex.zs or a .ugctex.zs to convert it into a png
