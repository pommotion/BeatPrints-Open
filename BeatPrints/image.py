"""
Module: image.py

Provides essential image functions to generate posters.
"""

import io
import os
import random
import requests
import qrcode

from pathlib import Path
from typing import List, Literal, Tuple, Optional

from PIL import Image, ImageDraw, ImageEnhance
from BeatPrints.consts import Size, Position, Color, ThemesSelector, FilePath

# Initialize the components
s = Size()
c = Color()
p = Position()
f = FilePath()
t = ThemesSelector()


def get_palette(image: Image.Image) -> List[Tuple]:
    """
    Extracts the dominant color palette from an image.

    Args:
        image (Image.Image): The image from which to extract the color palette.

    Returns:
        List[Tuple[int, int, int]]: A list of RGB tuples representing the dominant colors.
    """
    quantized = image.convert("RGB").resize((96, 96)).quantize(colors=6)
    palette = quantized.getpalette() or []
    color_counts = quantized.getcolors(maxcolors=96 * 96) or []
    color_counts.sort(reverse=True)

    colors = []
    for _count, palette_index in color_counts[:6]:
        offset = palette_index * 3
        colors.append(tuple(palette[offset : offset + 3]))

    while len(colors) < 6:
        colors.append(c.BLACK)

    return colors


def draw_palette(
    draw: ImageDraw.ImageDraw, image: Image.Image, accent: bool = False
) -> None:
    """
    Draws a color palette on the given image.

    Args:
        draw (ImageDraw.ImageDraw): The drawing context used to render on the image.
        image (Image.Image): The image to which the color palette will be drawn.
        accent (bool, optional): If True, an accent color is added at the bottom. Defaults to False.
    """
    palette = get_palette(image)

    # Render each color from the palette as a rectangle
    for index in range(6):
        x, y = p.PALETTE
        start, end = s.PL_WIDTH * index, s.PL_WIDTH * (index + 1)

        # Render the rectangle for the current color
        draw.rectangle(((x + start, y), (x + end, s.PL_HEIGHT)), fill=palette[index])

    # Add the accent at the bottom of the poster, if True
    if accent:
        draw.rectangle(p.ACCENT, fill=palette[random.randint(0, 2)])


def crop(path: Path) -> Image.Image:
    """
    Crops an image to a square aspect ratio.

    Args:
        path (Path): The file system path to the image file.

    Returns:
        Image.Image: The cropped square image.

    Raises:
        FileNotFoundError: If the provided file path does not exist.
    """

    def chop(image: Image.Image) -> Image.Image:
        width, height = image.size

        # Retrieve the minimum length of the image
        min_size = min(width, height)

        # Calculate the center of the image and crop it to a square
        left = (width - min_size) / 2
        top = (height - min_size) / 2
        right = (width + min_size) / 2
        bottom = (height + min_size) / 2

        return image.crop((left, top, right, bottom))

    with Image.open(path) as img:
        return chop(img)


def magicify(image: Image.Image) -> Image.Image:
    """
    Adjusts the brightness and contrast of an image.

    Args:
        image (Image.Image): The image to be adjusted.

    Returns:
        Image.Image: The image with modified brightness and contrast.
    """

    # Reduce brightness by 10%
    brightness = ImageEnhance.Brightness(image)
    magic = brightness.enhance(0.9)

    # Reduce contrast by 20%
    contrast = ImageEnhance.Contrast(magic)
    return contrast.enhance(0.8)


def scannable(
    id: str,
    theme: ThemesSelector.Options = "Light",
    item: Literal["track", "album"] = "track",
) -> Image.Image:
    """
    Generates a Spotify scannable code for a track or album.

    Args:
        id (str): The Spotify track or album ID.
        theme (ThemesSelector.Options, optional): The theme for the scannable code. Defaults to "Light".
        item (Literal["track", "album"], optional): Specifies the type of the scannable code. Defaults to "track".

    Returns:
        Image.Image: The resized scannable code image.
    """

    variant = t.THEMES[theme]

    if id.startswith(("http://", "https://")):
        return link_code(id, theme)

    # URL to fetch the scannable code
    scan_url = f"https://scannables.scdn.co/uri/plain/png/101010/white/1280/spotify:{item}:{id}"

    try:
        response = requests.get(scan_url, timeout=20)
        response.raise_for_status()
        img_bytes = io.BytesIO(response.content)

        with Image.open(img_bytes) as scan_code:
            # Convert to RGBA to support transparency
            scan_code = scan_code.convert("RGBA")

            pixels = scan_code.load()
            width, height = scan_code.size

            # Iterate over all pixels and replace white pixels with transparency code
            for x in range(width):
                for y in range(height):
                    if pixels is not None:
                        pixels[x, y] = (
                            c.TRANSPARENT if pixels[x, y] != c.WHITE else variant
                        )

            # Resize the image
            return scan_code.resize(s.SCANCODE, Image.Resampling.BICUBIC)
    except (requests.RequestException, OSError):
        return link_code(id, theme)


def link_code(url: str, theme: ThemesSelector.Options = "Light") -> Image.Image:
    """
    Generates a compact QR code for non-Spotify track or album links.
    """
    variant = t.THEMES[theme]
    qr = qrcode.QRCode(border=0, box_size=10)
    qr.add_data(url)
    qr.make(fit=True)

    code = qr.make_image(fill_color=variant, back_color=(255, 255, 255)).convert(
        "RGBA"
    )
    pixels = code.load()
    width, height = code.size
    for x in range(width):
        for y in range(height):
            if pixels is not None and pixels[x, y][:3] == (255, 255, 255):
                pixels[x, y] = c.TRANSPARENT

    code = code.resize((s.SCANCODE[1], s.SCANCODE[1]), Image.Resampling.NEAREST)

    canvas = Image.new("RGBA", s.SCANCODE, c.TRANSPARENT)
    canvas.paste(code, (0, 0), code)

    draw = ImageDraw.Draw(canvas)
    bar_x = s.SCANCODE[1] + 35
    bar_top = 34
    for index, height in enumerate([92, 58, 114, 74, 104, 46, 96, 66, 116, 80]):
        x = bar_x + index * 34
        y0 = bar_top + (116 - height) // 2
        draw.rounded_rectangle((x, y0, x + 12, y0 + height), radius=6, fill=variant)

    return canvas


def cover(url: str, path: Optional[str]) -> Image.Image:
    """
    Fetches and processes an image from a URL or local path.

    Args:
        url (str): The URL of the image.
        path (Optional[str]): The local path of the image. If provided, the image will be loaded
                              from this path; otherwise, it will be fetched from the URL.

    Returns:
        Image.Image: The processed image.

    Raises:
        FileNotFoundError: If the provided local image path does not exist.
    """

    if path:
        path_ = Path(path).expanduser().resolve()

        if not path_.exists():
            raise FileNotFoundError(f"The specified path '{path_}' does not exist.")

        img = crop(path_)

    else:
        img = Image.open(io.BytesIO(requests.get(url).content))

    # Apply the magic filter and resize the image
    return magicify(img.resize(s.COVER))


def get_theme(theme: ThemesSelector.Options = "Light") -> Tuple[tuple, str]:
    """
    Returns theme-related properties based on the selected theme.

    Args:
        theme (ThemesSelector.Options, optional): The selected theme. Defaults to "Light".

    Returns:
        Tuple[tuple, str]: A tuple containing the theme color and the template path.
    """

    variant = t.THEMES[theme]
    template = os.path.join(f.TEMPLATES, f"{theme.lower()}.png")

    return variant, template
