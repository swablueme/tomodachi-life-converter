from PIL import Image, ImageCms
from pyswizzle import nsw_deswizzle, nsw_swizzle
from pathlib import Path
import io
import os
import sys
import compression.zstd as zstd

# This script is a refactored version of https://github.com/Timiimiimii/TomoKoreFacepaintTool
# with ZSTD compression and decompression added and some experimental icc profile stuff changed

DECODING_GAMMA = 0.4545
ENCODING_GAMMA = 2.2
HEIGHT_OF_IMAGE, WIDTH_OF_IMAGE = 256, 256

SWITCH_SWIZZLE_MODE = 4
BYTES_PER_BLOCK_SWITCH = 4
UNCOMPRESSED_BLOCK_SIZE = (1, 1)

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


def save_canvas(img: Image, imagepath: Path):
    save_canvas_path = imagepath.with_name(f"{imagepath.stem}.canvas.zs")
    canvas_swizzled_data = nsw_swizzle(img, (HEIGHT_OF_IMAGE, WIDTH_OF_IMAGE),
                                       UNCOMPRESSED_BLOCK_SIZE, BYTES_PER_BLOCK_SWITCH, SWITCH_SWIZZLE_MODE)
    check_if_path_exists(save_canvas_path)
    canvas_swizzled_data = zstd.compress(canvas_swizzled_data)
    with open(save_canvas_path, 'wb') as f:
        f.write(bytes(canvas_swizzled_data))


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
