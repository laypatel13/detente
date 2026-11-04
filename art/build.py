"""Draws Roger and the pilot planes, then writes the sprite JSON and PNG exports.

The cast is built from big flat blocks. Roger's glass and beacon take the sign colour of
the moment, and his arm poses come from real marshalling signals.
"""

import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

OUT = Path(__file__).parent

ROGER_WIDTH, ROGER_HEIGHT = 26, 24
PLANE_WIDTH, PLANE_HEIGHT = 20, 11

YELLOW, YELLOW_SHADE = "#ffc417", "#d69a00"
RED, RED_SHADE, ALARM = "#c8102e", "#8f0a20", "#ff2b3f"
GLASS, GLASS_SHADE = "#3d4752", "#2a3138"
BLACK, WHITE, WHITE_SHADE = "#000000", "#ffffff", "#c9ced6"

ROGER_PALETTE = {
    "Y": YELLOW,
    "y": YELLOW_SHADE,
    "W": WHITE,
    "w": WHITE_SHADE,
    "K": BLACK,
    "E": WHITE,
    "P": BLACK,
    "Z": "#b0b6bd",
}

# beacon, glass, glass shade, mouth, paddle
ROGER_ACCENT = {
    "watching": (YELLOW, GLASS, GLASS_SHADE, WHITE, YELLOW),
    "traffic": (YELLOW, YELLOW, YELLOW_SHADE, BLACK, YELLOW),
    "collision": (ALARM, RED, RED_SHADE, BLACK, RED),
    "resolved": (WHITE, GLASS, GLASS_SHADE, YELLOW, YELLOW),
    "stop": (ALARM, RED, RED_SHADE, BLACK, RED),
    "resting": ("#5a5128", GLASS_SHADE, "#20262c", WHITE, YELLOW),
}

PLANE_SHARED = {"K": BLACK, "W": WHITE, "w": WHITE_SHADE, "P": BLACK}

# Red and yellow are left out: on the radar they mean hold and traffic.
PLANE_OWNERS = {
    "lay": {"B": "#378add", "D": "#185fa5"},
    "a": {"B": "#ec6a3c", "D": "#a83f1b"},
    "b": {"B": "#8d7cf0", "D": "#5a48c0"},
    "c": {"B": "#2bb3a3", "D": "#17796e"},
    "d": {"B": "#e86aa6", "D": "#a93a70"},
    "e": {"B": "#8bbf3a", "D": "#5b8220"},
    "f": {"B": "#d8dce0", "D": "#8d939b"},
    "g": {"B": "#c28a56", "D": "#855a32"},
}

# Named the way Roger is: after things pilots say on the radio.
PLANE_NAMES = {
    "lay": "Wilco",
    "a": "Mayday",
    "b": "Squawk",
    "c": "Niner",
    "d": "Pan-Pan",
    "e": "Chocks",
    "f": "Echo",
    "g": "Bravo",
}


class Grid:
    def __init__(self, width, height):
        self.width, self.height = width, height
        self.cells = [["."] * width for _ in range(height)]

    def block(self, x, y, width, height, letter):
        for row in range(y, y + height):
            for column in range(x, x + width):
                if 0 <= column < self.width and 0 <= row < self.height:
                    self.cells[row][column] = letter

    def outlined(self):
        """A one-block black edge, like the border on a real airfield sign."""
        out = Grid(self.width + 2, self.height + 2)
        for y, row in enumerate(self.cells):
            for x, letter in enumerate(row):
                out.cells[y + 1][x + 1] = letter
        edged = [row[:] for row in out.cells]
        for y in range(out.height):
            for x in range(out.width):
                if out.cells[y][x] != ".":
                    continue
                for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    near_x, near_y = x + dx, y + dy
                    if (
                        0 <= near_x < out.width
                        and 0 <= near_y < out.height
                        and out.cells[near_y][near_x] != "."
                    ):
                        edged[y][x] = "K"
                        break
        out.cells = edged
        return out

    def rows(self):
        return ["".join(row) for row in self.cells]


def tower(grid):
    # Beacon and mast.
    grid.block(11, 0, 4, 2, "a")
    grid.block(12, 2, 2, 1, "K")
    # Flat roof, narrower than the cab.
    grid.block(6, 3, 14, 2, "Y")
    grid.block(16, 3, 4, 2, "y")
    # Glass cab, wide at the top like a real control tower.
    grid.block(4, 5, 18, 2, "G")
    grid.block(5, 7, 16, 2, "G")
    grid.block(6, 9, 14, 2, "G")
    grid.block(20, 5, 2, 2, "g")
    grid.block(19, 7, 2, 2, "g")
    grid.block(18, 9, 2, 2, "g")
    # Balcony.
    grid.block(5, 11, 16, 1, "W")
    grid.block(17, 11, 4, 1, "w")
    # Shaft, belt and door.
    grid.block(8, 12, 10, 8, "W")
    grid.block(15, 12, 3, 8, "w")
    grid.block(8, 14, 10, 1, "Y")
    grid.block(15, 14, 3, 1, "y")
    grid.block(11, 16, 4, 4, "K")
    # Boots.
    grid.block(6, 20, 6, 2, "Y")
    grid.block(14, 20, 6, 2, "Y")
    grid.block(10, 20, 2, 2, "y")
    grid.block(18, 20, 2, 2, "y")


def paddle(grid, x, y):
    grid.block(x, y, 4, 4, "p")
    grid.block(x + 1, y + 1, 2, 2, "W")


def arm_down(grid, x, lift=0):
    grid.block(5 if x < 12 else 18, 13, 3, 2, "W")
    grid.block(5 if x < 12 else 19, 15, 2, 2, "W")
    paddle(grid, x, 17 - lift)


def arms_down(grid, frame):
    arm_down(grid, 4, frame)
    arm_down(grid, 18, frame)


def arms_pointing(grid, frame):
    arm_down(grid, 4)
    grid.block(18, 13, 4, 2, "W")
    paddle(grid, 22, 11 + frame)


def arms_up(grid, frame):
    grid.block(5, 12, 3, 2, "W")
    grid.block(3, 6, 2, 8, "W")
    grid.block(18, 12, 3, 2, "W")
    grid.block(21, 6, 2, 8, "W")
    paddle(grid, 1 + frame, 2)
    paddle(grid, 21 - frame, 2)


def arms_out(grid, frame):
    grid.block(2, 13, 6, 2, "W")
    grid.block(18, 13, 6, 2, "W")
    paddle(grid, 0, 11 + frame)
    paddle(grid, 22, 11 + frame)


def arm_waving(grid, frame):
    arm_down(grid, 4)
    grid.block(18, 12, 3, 2, "W")
    grid.block(21, 6, 2, 8, "W")
    paddle(grid, 22 if frame else 20, 2)


LEFT_EYE, RIGHT_EYE = 8, 14


def face_looking(grid, frame):
    for x in (LEFT_EYE, RIGHT_EYE):
        if frame:
            grid.block(x, 8, 4, 1, "E")
        else:
            grid.block(x, 6, 4, 4, "E")
            grid.block(x + 1, 7, 2, 2, "P")


def face_suspicious(grid, frame):
    for x in (LEFT_EYE, RIGHT_EYE):
        grid.block(x, 6, 4, 4, "E")
        grid.block(x + 2 - frame, 7, 2, 2, "P")
    grid.block(LEFT_EYE, 5, 4, 1, "K")


def face_alarmed(grid, _frame):
    grid.block(LEFT_EYE - 1, 5, 5, 5, "E")
    grid.block(RIGHT_EYE, 5, 5, 5, "E")
    grid.block(LEFT_EYE + 1, 7, 1, 1, "P")
    grid.block(RIGHT_EYE + 2, 7, 1, 1, "P")
    grid.block(12, 9, 2, 2, "m")


def face_happy(grid, _frame):
    for x in (LEFT_EYE, RIGHT_EYE):
        grid.block(x, 8, 1, 1, "E")
        grid.block(x + 1, 7, 2, 1, "E")
        grid.block(x + 3, 8, 1, 1, "E")
    grid.block(11, 9, 1, 1, "m")
    grid.block(14, 9, 1, 1, "m")
    grid.block(12, 10, 2, 1, "m")


def face_stern(grid, _frame):
    for x in (LEFT_EYE, RIGHT_EYE):
        grid.block(x, 6, 4, 4, "E")
        grid.block(x + 1, 8, 2, 2, "P")
        grid.block(x, 6, 4, 1, "G")
    grid.block(LEFT_EYE + 2, 7, 2, 1, "G")
    grid.block(RIGHT_EYE, 7, 2, 1, "G")
    grid.block(10, 10, 6, 1, "m")


def face_asleep(grid, _frame):
    for x in (LEFT_EYE, RIGHT_EYE):
        grid.block(x, 8, 4, 1, "Z")
    grid.block(21, 0, 3, 1, "Z")
    grid.block(22, 1, 1, 1, "Z")
    grid.block(21, 2, 3, 1, "Z")


def roger_frame(pose, face, frame):
    grid = Grid(ROGER_WIDTH, ROGER_HEIGHT)
    tower(grid)
    pose(grid, frame)
    face(grid, frame)
    return grid.outlined().rows()


def roger_mood(says, sign_face, pose, face, frames):
    return {
        "face": sign_face,
        "says": says,
        "frames": [roger_frame(pose, face, frame) for frame in frames],
    }


ROGER_MOODS = {
    # Four beats, so he blinks now and then instead of every other tick.
    "watching": roger_mood("watching", "[o_o]", lambda g, _: arms_down(g, 0), face_looking, [0, 0, 0, 1]),
    "traffic": roger_mood("suspicious", "[¬_¬]", arms_pointing, face_suspicious, [0, 1]),
    "collision": roger_mood("alarmed", "[O_O]!", arms_up, face_alarmed, [0, 1]),
    "resolved": roger_mood("happy", "[^_^]", arm_waving, face_happy, [0, 1]),
    "stop": roger_mood("stern", "[ò_ó]", arms_out, face_stern, [0, 1]),
    "resting": roger_mood("asleep", "[-_-]z", lambda g, _: arms_down(g, 0), face_asleep, [0]),
}


def plane_frame(eyes, spinning):
    grid = Grid(PLANE_WIDTH, PLANE_HEIGHT)
    # Tail.
    grid.block(0, 0, 3, 1, "D")
    grid.block(0, 1, 4, 1, "D")
    grid.block(0, 2, 5, 1, "D")
    # Body, stripe and wing.
    grid.block(5, 2, 10, 1, "B")
    grid.block(2, 3, 15, 1, "B")
    grid.block(1, 4, 17, 3, "B")
    grid.block(2, 7, 15, 1, "B")
    grid.block(4, 8, 11, 1, "D")
    grid.block(1, 6, 8, 1, "W")
    grid.block(4, 7, 7, 1, "D")
    eyes(grid)
    grid.block(13, 7, 3, 1, "K")
    # Propeller. A long blade and a short one swap to spin it.
    grid.block(18, 4, 1, 3, "W")
    grid.block(19, 0 if spinning else 3, 1, 10 if spinning else 4, "w")
    # Wheels, so they read on the ground.
    grid.block(5, 9, 3, 2, "w")
    grid.block(12, 9, 3, 2, "w")
    grid.block(6, 9, 1, 1, "K")
    grid.block(13, 9, 1, 1, "K")
    return grid.outlined().rows()


def plane_eyes(pupil):
    def draw_eyes(grid):
        for x in (10, 14):
            grid.block(x, 3, 3, 3, "W")
            pupil(grid, x)

    return draw_eyes


def eyes_open(grid, x):
    grid.block(x + 1, 4, 2, 2, "P")


def eyes_lidded(grid, x):
    grid.block(x, 3, 3, 1, "D")
    grid.block(x + 1, 4, 2, 2, "P")


def eyes_wide(grid, x):
    grid.block(x + 1, 4, 1, 1, "P")


def eyes_happy(grid, x):
    grid.block(x, 3, 3, 3, "B")
    grid.block(x, 5, 1, 1, "W")
    grid.block(x + 1, 4, 1, 1, "W")
    grid.block(x + 2, 5, 1, 1, "W")


PLANE_MOODS = {
    "cleared": {
        "says": "cleared",
        "frames": [plane_frame(plane_eyes(eyes_open), spin) for spin in (False, True)],
    },
    "hold": {"says": "holding", "frames": [plane_frame(plane_eyes(eyes_lidded), False)]},
    "worried": {
        "says": "collision course",
        "frames": [plane_frame(plane_eyes(eyes_wide), spin) for spin in (False, True)],
    },
    "happy": {"says": "landed", "frames": [plane_frame(plane_eyes(eyes_happy), False)]},
}


def roger_palette(mood):
    beacon, glass, shade, mouth, paddle_color = ROGER_ACCENT[mood]
    return {**ROGER_PALETTE, "a": beacon, "G": glass, "g": shade, "m": mouth, "p": paddle_color}


def draw(rows, palette, scale):
    image = Image.new("RGBA", (len(rows[0]) * scale, len(rows) * scale), (0, 0, 0, 0))
    for y, row in enumerate(rows):
        for x, letter in enumerate(row):
            if letter != ".":
                box = (x * scale, y * scale, (x + 1) * scale, (y + 1) * scale)
                image.paste(palette[letter], box)
    return image


def check(name, frames, width, height):
    for frame in frames:
        assert len(frame) == height, f"{name} has {len(frame)} rows"
        assert all(len(row) == width for row in frame), f"{name} has an uneven row"


def sheet(path):
    scale = 6
    fields = {
        "watching": BLACK,
        "traffic": YELLOW,
        "collision": RED,
        "resolved": BLACK,
        "stop": RED,
        "resting": "#2a2e33",
    }
    tile = (ROGER_WIDTH + 6) * scale
    tall = (ROGER_HEIGHT + 6) * scale
    plane_scale = 5
    plane_tile = tile * 6 // len(PLANE_OWNERS)
    canvas = Image.new("RGBA", (tile * 6, tall + (PLANE_HEIGHT + 15) * plane_scale), "#141619")
    for index, (mood, field) in enumerate(fields.items()):
        canvas.paste(field, (index * tile, 0, (index + 1) * tile - 6, tall))
        image = draw(ROGER_MOODS[mood]["frames"][0], roger_palette(mood), scale)
        canvas.alpha_composite(image, (index * tile + 2 * scale, 2 * scale))
    label = ImageDraw.Draw(canvas)
    font = ImageFont.load_default(22)
    moods = ("cleared", "worried", "hold", "happy") * 2
    for index, (owner, mood) in enumerate(zip(PLANE_OWNERS, moods)):
        palette = {**PLANE_SHARED, **PLANE_OWNERS[owner]}
        image = draw(PLANE_MOODS[mood]["frames"][-1], palette, plane_scale)
        left = index * plane_tile + (plane_tile - image.width) // 2
        canvas.alpha_composite(image, (left, tall + 3 * plane_scale))
        middle = (index * plane_tile + plane_tile // 2, tall + (PLANE_HEIGHT + 8) * plane_scale)
        label.text(middle, PLANE_NAMES[owner], fill=WHITE, font=font, anchor="ma")
    canvas.save(path)


def main():
    for mood, data in ROGER_MOODS.items():
        check(f"roger/{mood}", data["frames"], ROGER_WIDTH + 2, ROGER_HEIGHT + 2)
    for mood, data in PLANE_MOODS.items():
        check(f"plane/{mood}", data["frames"], PLANE_WIDTH + 2, PLANE_HEIGHT + 2)

    roger = {
        "_comment": "Roger, the tower. One letter per block, '.' is transparent. Merge 'palette' with the mood's 'accent'.",
        "width": ROGER_WIDTH + 2,
        "height": ROGER_HEIGHT + 2,
        "palette": ROGER_PALETTE,
        "accent": {mood: {k: v for k, v in roger_palette(mood).items() if k in "aGgmp"} for mood in ROGER_ACCENT},
        "moods": ROGER_MOODS,
    }
    plane = {
        "_comment": "Pilot planes, facing right. Merge 'shared' with one owner's colors. Frames alternate the propeller.",
        "width": PLANE_WIDTH + 2,
        "height": PLANE_HEIGHT + 2,
        "shared": PLANE_SHARED,
        "owners": PLANE_OWNERS,
        "names": PLANE_NAMES,
        "moods": PLANE_MOODS,
    }
    (OUT / "roger.json").write_text(json.dumps(roger, ensure_ascii=False, indent=2) + "\n")
    (OUT / "plane.json").write_text(json.dumps(plane, ensure_ascii=False, indent=2) + "\n")

    sheet(OUT / "cast-sheet.png")

    avatar = Image.new("RGBA", (256, 256), YELLOW)
    image = draw(ROGER_MOODS["watching"]["frames"][0][:14], roger_palette("watching"), 8)
    avatar.alpha_composite(image, ((256 - image.width) // 2, (256 - image.height) // 2))
    avatar.save(OUT / "roger-avatar-256.png")


if __name__ == "__main__":
    main()
