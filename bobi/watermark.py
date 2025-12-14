import io
import os
from PIL import Image
import cairosvg



LOGO_FILE_PATH = os.path.join(os.path.dirname(__file__), "logo.svg")
def apply_watermark_to_image(
    img,
    opacity=0.65,
    angle=0,
    scale_fraction=0.25,
    spacing=(320, 380),
    svg_path=LOGO_FILE_PATH,
):
    print(f"[DEBUG] apply_watermark_to_image called with opacity={opacity}, angle={angle}, scale_fraction={scale_fraction}, spacing={spacing}")
    
    base_dir = os.path.dirname(__file__)
    print(f"[DEBUG] base_dir={base_dir}")

    if not svg_path:
        svg_path = os.path.join(base_dir, "logo.svg")
    print(f"[DEBUG] svg_path={svg_path}")

    try:
        print(f"[DEBUG] Attempting to render SVG from {svg_path}")
        png_bytes = cairosvg.svg2png(url=svg_path)
        print(f"[DEBUG] SVG rendered to PNG, bytes length: {len(png_bytes)}")
        
        wm = Image.open(io.BytesIO(png_bytes)).convert("RGBA")
        print(f"[DEBUG] Watermark image loaded: size=({wm.width}x{wm.height}), mode={wm.mode}")
    except Exception as e:
        print(f"[ERROR] Failed to render watermark SVG: {str(e)}")
        return img

    base = img.convert("RGBA")
    print(f"[DEBUG] Base image converted to RGBA: size=({base.width}x{base.height})")

    min_dim = min(base.width, base.height)
    print(f"[DEBUG] min_dim={min_dim}")
    
    target_w = max(32, int(min_dim * scale_fraction))
    print(f"[DEBUG] target_w={target_w}")
    
    scale = target_w / max(1, wm.width)
    print(f"[DEBUG] scale factor={scale}")

    wm_resized = wm.resize(
        (int(wm.width * scale), int(wm.height * scale)),
        Image.LANCZOS
    )
    print(f"[DEBUG] Watermark resized to ({wm_resized.width}x{wm_resized.height})")

    wm_rotated = wm_resized.rotate(angle, expand=True)
    print(f"[DEBUG] Watermark rotated by {angle}°, new size=({wm_rotated.width}x{wm_rotated.height})")

    if opacity < 1.0:
        print(f"[DEBUG] Applying opacity {opacity} to watermark")
        alpha = wm_rotated.split()[3].point(lambda p: int(p * opacity))
        wm_rotated.putalpha(alpha)
        print(f"[DEBUG] Opacity applied")
    else:
        print(f"[DEBUG] Opacity=1.0, no adjustment needed")

    overlay = Image.new("RGBA", base.size, (255, 255, 255, 0))
    print(f"[DEBUG] Created overlay: size=({overlay.width}x{overlay.height})")
    
    step_x, step_y = spacing
    print(f"[DEBUG] Spacing: step_x={step_x}, step_y={step_y}")

    tile_count = 0
    # Start from top-left edge (0, 0) and tile with proper spacing
    for y in range(0, base.height, step_y):
        for x in range(0, base.width, step_x):
            overlay.paste(wm_rotated, (x, y), wm_rotated)
            tile_count += 1
    print(f"[DEBUG] Tiled watermark {tile_count} times across overlay")

    final_img = Image.alpha_composite(base, overlay).convert("RGB")
    print(f"[DEBUG] Alpha composite completed, converted to RGB: size=({final_img.width}x{final_img.height})")

    print(f"[DEBUG] apply_watermark_to_image completed successfully")
    return final_img







