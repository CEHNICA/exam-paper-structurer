import sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

def make_sheet(img_dir, out_path, thumb=260, cols=5, label_h=26):
    img_dir = Path(img_dir)
    files = sorted(img_dir.glob("*.jpg")) + sorted(img_dir.glob("*.png"))
    if not files:
        print(f"no images in {img_dir}")
        return
    rows = (len(files) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * thumb, rows * (thumb + label_h)), "white")
    draw = ImageDraw.Draw(sheet)
    try:
        font = ImageFont.truetype("arial.ttf", 20)
    except Exception:
        font = ImageFont.load_default()
    for i, f in enumerate(files):
        im = Image.open(f).convert("RGB")
        im.thumbnail((thumb - 8, thumb - 8))
        x = (i % cols) * thumb
        y = (i // cols) * (thumb + label_h)
        sheet.paste(im, (x + 4, y + label_h + 2))
        draw.rectangle([x, y, x + thumb, y + label_h], fill=(30, 30, 30))
        draw.text((x + 4, y + 4), f"#{i} {f.stem[:8]}", fill="white", font=font)
    sheet.save(out_path)
    print(f"saved {out_path} ({len(files)} images, {cols}x{rows})")

if __name__ == "__main__":
    make_sheet(sys.argv[1], sys.argv[2])
