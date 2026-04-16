from PIL import Image, ImageCms
from pyswizzle import nsw_deswizzle, nsw_swizzle
from pathlib import Path
from constants import *
from helper_functions import *
import os
import sys
import compression.zstd as zstd

"""
For converting canvases.
Such as UgcFacePaint001.canvas.zs or UgcCloth000.canvas.zs
Simply drag and drop a png onto this script to convert a png into a .canvas.zs or a .canvas.zs to convert it into a png
"""


# This script is a refactored version of https://github.com/Timiimiimii/TomoKoreFacepaintTool
# with ZSTD compression and decompression added and some experimental icc profile stuff changed


def save_canvas(img: Image, imagepath: Path):
    save_canvas_path = imagepath.with_name(f"{imagepath.stem}.canvas.zs")
    canvas_swizzled_data = nsw_swizzle(img, (HEIGHT_OF_IMAGE_CANVAS, WIDTH_OF_IMAGE_CANVAS),
                                       UNCOMPRESSED_BLOCK_SIZE_CANVAS, BYTES_PER_BLOCK_SWITCH_CANVAS, SWITCH_SWIZZLE_MODE)
    check_if_path_exists(save_canvas_path)
    canvas_swizzled_data = zstd.compress(canvas_swizzled_data)
    with open(save_canvas_path, 'wb') as f:
        f.write(bytes(canvas_swizzled_data))


def convert_canvas_to_png(canvas_path):
    with open(canvas_path, 'rb') as file:
        rawdata = file.read()
        if canvas_path.name.endswith(".zs"):
            rawdata = zstd.decompress(rawdata)

        swizzled = nsw_deswizzle(rawdata, (HEIGHT_OF_IMAGE_CANVAS, WIDTH_OF_IMAGE_CANVAS),
                                 UNCOMPRESSED_BLOCK_SIZE_CANVAS, BYTES_PER_BLOCK_SWITCH_CANVAS, SWITCH_SWIZZLE_MODE)

        img = Image.frombytes(
            IMAGE_MODE, (HEIGHT_OF_IMAGE_CANVAS, WIDTH_OF_IMAGE_CANVAS), swizzled, 'raw', IMAGE_MODE)

        save_file(img, canvas_path)


def convert_png_to_canvas(canvas_path):
    canvas = Image.open(Path.cwd() / canvas_path)
    if not is_srgb_image(canvas):
        canvas = set_image_gamma(canvas, ENCODING_GAMMA)

    """
    Todo: readd asserts from the valid canvas sizes
    Clothing = 256 x 256
    Facepaint = 256 x 256
    Food = 256 x 256
    """

    canvas = canvas.convert(IMAGE_MODE).tobytes('raw')
    save_canvas(canvas, canvas_path)


if __name__ == "__main__":
    if len(sys.argv) > 1:
        files = sys.argv[1:]
        for path in files:
            if os.path.exists(os.path.abspath(path)):
                print(f"Found file: {path}")
                if path.endswith("canvas.zs"):
                    convert_canvas_to_png(Path.cwd() / path)
                elif path.endswith(".png"):
                    convert_png_to_canvas(Path.cwd() / path)
                else:
                    print("File extension unrecognized.")
            else:
                print(f"File {path} doesn't exist.")
    else:
        print("No command line arguments received")
        # lazy vscode f5 pressing
        # facepaint = "UgcCloth000"
        # convert_canvas_to_png(Path.cwd() / f"{facepaint}.canvas.zs")
        # convert_png_to_canvas(Path.cwd() / f"{facepaint}OUTPUT.png")
