from pathlib import Path

from PIL import Image, ImageDraw


files = sorted(Path("tmp/pdfs").glob("page-*.png"))
thumbs = []
for index, path in enumerate(files, 1):
    image = Image.open(path).convert("RGB")
    image.thumbnail((306, 396))
    canvas = Image.new("RGB", (326, 426), "white")
    canvas.paste(image, ((326 - image.width) // 2, 20))
    ImageDraw.Draw(canvas).text((8, 4), f"Page {index}", fill="black")
    thumbs.append(canvas)

columns = 3
rows = (len(thumbs) + columns - 1) // columns
sheet = Image.new("RGB", (columns * 326, rows * 426), (220, 220, 220))
for index, image in enumerate(thumbs):
    sheet.paste(image, ((index % columns) * 326, (index // columns) * 426))

sheet.save("tmp/pdfs/contact-sheet.png")
