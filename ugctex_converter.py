from PIL import Image, ImageCms
from constants import *
from helper_functions import *
import compression.zstd as zstd
import io
from pyswizzle import nsw_deswizzle, nsw_swizzle
import sys
import os

"""
For converting textures.
Such as UgcCloth000.ugctex.zs or UgcFacePaint000.ugctex.zs
Simply drag and drop a png onto this script to convert a png into a .ugctex.zs or a .ugctex.zs to convert it into a png
"""


def save_ugctex(img: Image, imagepath: Path):
    dds_bytes = io.BytesIO()
    img.save(dds_bytes, format='DDS', pixel_format='DXT1')

    save_ugctex_path = imagepath.with_name(f"{imagepath.stem}.ugctex.zs")
    ugctex_swizzled_data = nsw_swizzle(dds_bytes.getvalue()[128:], (HEIGHT_OF_IMAGE_TEXTURE, WIDTH_OF_IMAGE_TEXTURE),
                                       UNCOMPRESSED_BLOCK_SIZE_TEXTURE, BYTES_PER_BLOCK_SWITCH_TEXTURE, SWITCH_SWIZZLE_MODE)
    check_if_path_exists(save_ugctex_path)
    ugctex_swizzled_data = zstd.compress(ugctex_swizzled_data)
    with open(save_ugctex_path, 'wb') as f:
        f.write(bytes(ugctex_swizzled_data))


def convert_ugctex_to_png(ugctext_path):
    with open(ugctext_path, 'rb') as file:
        rawdata = file.read()
        if ugctext_path.name.endswith(".zs"):
            rawdata = zstd.decompress(rawdata)

        swizzled = nsw_deswizzle(rawdata, (HEIGHT_OF_IMAGE_TEXTURE, WIDTH_OF_IMAGE_TEXTURE),
                                 UNCOMPRESSED_BLOCK_SIZE_TEXTURE, BYTES_PER_BLOCK_SWITCH_TEXTURE, SWITCH_SWIZZLE_MODE)

        img = Image.open(io.BytesIO(DDS_HEADER + swizzled))

        save_file(img, ugctext_path)


def convert_png_to_ugctex(ugctex_path):
    ugctex = Image.open(Path.cwd() / ugctex_path)
    if not is_srgb_image(ugctex):
        ugctex = set_image_gamma(ugctex, ENCODING_GAMMA)

    """
    Todo: readd asserts from the valid ugctex sizes
    """

    save_ugctex(ugctex, ugctex_path)


if __name__ == "__main__":
    if len(sys.argv) > 1:
        files = sys.argv[1:]
        for path in files:
            if os.path.exists(os.path.abspath(path)):
                if path.endswith("ugctex.zs"):
                    convert_ugctex_to_png(Path.cwd() / path)
                elif path.endswith(".png"):
                    convert_png_to_ugctex(Path.cwd() / path)
                else:
                    print("File extension unrecognized.")
            else:
                print(f"File {path} doesn't exist.")
