from PIL import Image, ImageCms
from pyswizzle import nsw_deswizzle, nsw_swizzle
from pathlib import Path
import io
import os
import sys
import compression.zstd as zstd

# This script is a refactored version of https://github.com/Timiimiimii/TomoKoreFacepaintTool
# with ZSTD compression and decompression added and some experimental icc profile stuff changed

DDS_HEADER = b"\x44\x44\x53\x20\x7C\x00\x00\x00\x07\x10\x0A\x00\x00\x02\x00\x00\x00\x02\x00\x00\x00\x00\x02\x00\x01\x00\x00\x00\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x20\x00\x00\x00\x04\x00\x00\x00\x44\x58\x54\x31\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x10\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"

DECODING_GAMMA = 0.4545
ENCODING_GAMMA = 2.2
HEIGHT_OF_IMAGE, WIDTH_OF_IMAGE = 256, 256

SWITCH_SWIZZLE_MODE = 4
BYTES_PER_BLOCK_SWITCH = 4
UNCOMPRESSED_BLOCK_SIZE = (1, 1)

UGC_HEIGHT, UGC_WIDTH = 512, 512
UGC_BPBS = 8
UGC_BLOCK_SIZE = (4, 4)

FILE_FORMAT = "png"
SRGB_PROFILE = "sRGB"
IMAGE_MODE = "RGBA"


def set_image_gamma(img: Image, gamma):
    # this is the Callable[[int], float] being passed to img.point
    lookup_table = lambda x: ((x / 255) ** gamma) * 255
    return img.point(lookup_table)


def get_icc_profile(image):
    icc = image.info.get('icc_profile')
    if icc is None:
        print("No ICC profile found in image.")
        return
    f = io.BytesIO(icc)
    prf = ImageCms.ImageCmsProfile(f)
    print(f"Custom ICC profile detected {prf.profile.profile_description}")
    return prf


def is_srgb_image(image):
    if "srgb" in image.info:
        return True
    prf = get_icc_profile(image)
    if prf is None:
        return False
    elif "srgb" in prf.profile.profile_description.lower():
        return True
    return False


def check_if_path_exists(savepath: Path):
    if savepath.exists():
        savepath.unlink()


def save_file(img: Image, canvas_path: Path):
    img = set_image_gamma(img, DECODING_GAMMA)
    save_image_path = canvas_path.with_name(
        canvas_path.name.split(".")[0] + f"OUTPUT.{FILE_FORMAT}")
    check_if_path_exists(save_image_path)
    img.save(save_image_path, FILE_FORMAT)


def save_ugctex(img: Image, imagepath: Path):
    dds_bytes = io.BytesIO()
    img.save(dds_bytes, format='DDS', pixel_format='DXT1')

    save_ugctex_path = imagepath.with_name(f"{imagepath.stem}.ugctex.zs")
    ugctex_swizzled_data = nsw_swizzle(dds_bytes.getvalue()[128:], (UGC_HEIGHT, UGC_WIDTH),
                                       UGC_BLOCK_SIZE, UGC_BPBS, SWITCH_SWIZZLE_MODE)
    check_if_path_exists(save_ugctex_path)
    ugctex_swizzled_data = zstd.compress(ugctex_swizzled_data)
    with open(save_ugctex_path, 'wb') as f:
        f.write(bytes(ugctex_swizzled_data))


def save_canvas(img: Image, imagepath: Path):
    save_canvas_path = imagepath.with_name(f"{imagepath.stem}.canvas.zs")
    canvas_swizzled_data = nsw_swizzle(img, (HEIGHT_OF_IMAGE, WIDTH_OF_IMAGE),
                                       UNCOMPRESSED_BLOCK_SIZE, BYTES_PER_BLOCK_SWITCH, SWITCH_SWIZZLE_MODE)
    check_if_path_exists(save_canvas_path)
    canvas_swizzled_data = zstd.compress(canvas_swizzled_data)
    with open(save_canvas_path, 'wb') as f:
        f.write(bytes(canvas_swizzled_data))


def convert_ugctex_to_png(ugctext_path):
    with open(ugctext_path, 'rb') as file:
        rawdata = file.read()
        if ugctext_path.name.endswith(".zs"):
            rawdata = zstd.decompress(rawdata)

        swizzled = nsw_deswizzle(rawdata, (UGC_HEIGHT, UGC_WIDTH),
                                 UGC_BLOCK_SIZE, UGC_BPBS, SWITCH_SWIZZLE_MODE)

        img = Image.open(io.BytesIO(DDS_HEADER + swizzled))

        save_file(img, ugctext_path)


def convert_canvas_to_png(canvas_path):
    with open(canvas_path, 'rb') as file:
        rawdata = file.read()
        if canvas_path.name.endswith(".zs"):
            rawdata = zstd.decompress(rawdata)

        swizzled = nsw_deswizzle(rawdata, (HEIGHT_OF_IMAGE, WIDTH_OF_IMAGE),
                                 UNCOMPRESSED_BLOCK_SIZE, BYTES_PER_BLOCK_SWITCH, SWITCH_SWIZZLE_MODE)

        img = Image.frombytes(
            IMAGE_MODE, (HEIGHT_OF_IMAGE, WIDTH_OF_IMAGE), swizzled, 'raw', IMAGE_MODE)

        save_file(img, canvas_path)


def convert_png(png_path):
    canvas = Image.open(Path.cwd() / png_path)
    if canvas.size == (UGC_WIDTH, UGC_HEIGHT):
        convert_png_to_ugctex(png_path)
    else:
        convert_png_to_canvas(png_path)
    canvas.close()


def convert_png_to_ugctex(ugctex_path):
    ugctex = Image.open(Path.cwd() / ugctex_path)
    if not is_srgb_image(ugctex):
        ugctex = set_image_gamma(ugctex, ENCODING_GAMMA)

    assert ugctex.size == (UGC_WIDTH, UGC_HEIGHT), "Ugctex must be 512 x 512 in dimensions"
    save_ugctex(ugctex, ugctex_path)


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
                elif path.endswith("ugctex.zs"):
                    convert_ugctex_to_png(Path.cwd() / path)
                elif path.endswith(".png"):
                    convert_png(Path.cwd() / path)
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
