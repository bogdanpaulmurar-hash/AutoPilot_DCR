# -*- coding: utf-8 -*-
# Genereaza iconita aplicatiei (assets/autopilot.ico + autopilot.png) cu Pillow.
# Rulare (doar daca vrei sa o schimbi):  py assets/make_icon.py
#
# Motiv: patrat rotunjit turcoaz (culoarea aplicatiei), litera "A" alba ca un varf de sageata
# + un traseu de pasi (puncte) care se termina cu un triunghi "play" = automatizare / rulare.
import os

from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
S = 512  # desenam mare, apoi micsoram (margini netede)


def draw() -> Image.Image:
    img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    # 1. fundal: gradient vertical turcoaz in patrat rotunjit
    top, bottom = (0, 170, 170), (0, 102, 110)
    grad = Image.new("RGBA", (S, S))
    gd = ImageDraw.Draw(grad)
    for y in range(S):
        t = y / (S - 1)
        gd.line([(0, y), (S, y)], fill=tuple(int(top[i] + (bottom[i] - top[i]) * t) for i in range(3)) + (255,))
    mask = Image.new("L", (S, S), 0)
    ImageDraw.Draw(mask).rounded_rectangle([16, 16, S - 16, S - 16], radius=110, fill=255)
    img.paste(grad, (0, 0), mask)

    # 2. litera "A" (doua picioare + bara), alba
    w = 54
    apex, left, right = (S * 0.43, S * 0.17), (S * 0.17, S * 0.80), (S * 0.69, S * 0.80)
    d.line([left, apex, right], fill="white", width=w, joint="curve")
    d.line([(S * 0.28, S * 0.58), (S * 0.58, S * 0.58)], fill="white", width=int(w * 0.8))

    # 3. traseul de pasi: puncte care urca spre dreapta-sus + triunghi "play"
    for i, (x, y) in enumerate([(0.62, 0.48), (0.70, 0.40), (0.78, 0.32)]):
        r = 20 - i * 2
        d.ellipse([S * x - r, S * y - r, S * x + r, S * y + r], fill=(255, 214, 0, 255))
    px, py = S * 0.80, S * 0.62
    d.polygon([(px - 46, py - 56), (px - 46, py + 56), (px + 50, py)], fill=(255, 214, 0, 255))
    return img


def main():
    big = draw()
    big.resize((256, 256), Image.LANCZOS).save(os.path.join(HERE, "autopilot.png"))
    big.save(os.path.join(HERE, "autopilot.ico"),
             sizes=[(16, 16), (20, 20), (24, 24), (32, 32), (40, 40), (48, 48), (64, 64), (128, 128), (256, 256)])
    print("assets/autopilot.ico + autopilot.png generate")


if __name__ == "__main__":
    main()
