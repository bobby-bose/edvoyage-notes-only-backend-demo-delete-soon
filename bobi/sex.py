def apply_watermark_to_image(
    img,
    svg_path=None,
    opacity=0.75,
    angle=30,
    scale_fraction=0.45,
    spacing=(420, 900),
    output_filename="output.png"
):
    import io
    import os
    from PIL import Image
    import cairosvg

    base_dir = os.path.dirname(__file__)

    if not svg_path:
        svg_path = os.path.join(base_dir, "logo.svg")

    try:
        png_bytes = cairosvg.svg2png(url=svg_path)
        wm = Image.open(io.BytesIO(png_bytes)).convert("RGBA")
    except Exception:
        return img

    base = img.convert("RGBA")

    min_dim = min(base.width, base.height)
    target_w = max(32, int(min_dim * scale_fraction))
    scale = target_w / max(1, wm.width)

    wm_resized = wm.resize(
        (int(wm.width * scale), int(wm.height * scale)),
        Image.LANCZOS
    )

    wm_rotated = wm_resized.rotate(angle, expand=True)

    if opacity < 1.0:
        alpha = wm_rotated.split()[3].point(lambda p: int(p * opacity))
        wm_rotated.putalpha(alpha)

    overlay = Image.new("RGBA", base.size, (255, 255, 255, 0))
    step_x, step_y = spacing

    margin_x = step_x // 2
    margin_y = step_y // 2

    for y in range(-margin_y, base.height + margin_y, step_y):
        for x in range(-margin_x, base.width + margin_x, step_x):
            overlay.paste(wm_rotated, (x, y), wm_rotated)

    final_img = Image.alpha_composite(base, overlay).convert("RGB")

    output_path = os.path.join(base_dir, output_filename)
    final_img.save(output_path, format="PNG")

    return final_img


import os
from PIL import Image
LOGO_FILE_PATH = os.path.join(os.path.dirname(__file__), "logo.svg")
IMG_PATH = os.path.join(os.path.dirname(__file__), "input.jpg")

def apply_watermark():
    
    return apply_watermark_to_image(
        img=Image.open(IMG_PATH),
        svg_path=LOGO_FILE_PATH,
        opacity=0.6,
        angle=30,
        scale_fraction=0.45,
        spacing=(190, 250),
        output_filename="output.png"
    )
    
apply_watermark()