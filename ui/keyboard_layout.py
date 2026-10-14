from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple


@dataclass
class VirtualKey:
    char: str
    display_label: str
    x1: int
    y1: int
    x2: int
    y2: int
    is_special: bool = False

    def contains(self, x: int, y: int) -> bool:
        return self.x1 <= x <= self.x2 and self.y1 <= y <= self.y2


class KeyboardLayout:
    """Calculates and manages interactive on-screen QWERTY keyboard coordinates."""

    ROWS = [
        ["Q", "W", "E", "R", "T", "Y", "U", "I", "O", "P"],
        ["A", "S", "D", "F", "G", "H", "J", "K", "L"],
        ["Z", "X", "C", "V", "B", "N", "M"],
    ]

    def __init__(self, frame_w: int, frame_h: int):
        self.frame_w = frame_w
        self.frame_h = frame_h
        self.keys: List[VirtualKey] = []
        self._build_layout()

    def _build_layout(self):
        """Constructs keys positioned ergonomically in the bottom-center of the screen."""
        self.keys.clear()

        # Keyboard spans across central 85% width, bottom 45% height
        kb_w = int(self.frame_w * 0.86)
        kb_h = int(self.frame_h * 0.44)
        start_x = (self.frame_w - kb_w) // 2
        start_y = int(self.frame_h * 0.52)

        row_count = 4  # 3 rows of letters + 1 bottom utility row
        row_h = kb_h // row_count
        gap = 6

        # Row 0: Q to P (10 keys)
        col_w_row0 = (kb_w - (10 - 1) * gap) // 10
        for i, char in enumerate(self.ROWS[0]):
            x1 = start_x + i * (col_w_row0 + gap)
            y1 = start_y
            x2 = x1 + col_w_row0
            y2 = y1 + row_h - gap
            self.keys.append(VirtualKey(char=char, display_label=char, x1=x1, y1=y1, x2=x2, y2=y2))

        # Row 1: A to L (9 keys, offset)
        offset_row1 = col_w_row0 // 2
        col_w_row1 = (kb_w - offset_row1 * 2 - (9 - 1) * gap) // 9
        for i, char in enumerate(self.ROWS[1]):
            x1 = start_x + offset_row1 + i * (col_w_row1 + gap)
            y1 = start_y + row_h
            x2 = x1 + col_w_row1
            y2 = y1 + row_h - gap
            self.keys.append(VirtualKey(char=char, display_label=char, x1=x1, y1=y1, x2=x2, y2=y2))

        # Row 2: Z to M (7 keys, centered)
        offset_row2 = col_w_row0 * 1
        col_w_row2 = (kb_w - offset_row2 * 2 - (7 - 1) * gap) // 7
        for i, char in enumerate(self.ROWS[2]):
            x1 = start_x + offset_row2 + i * (col_w_row2 + gap)
            y1 = start_y + row_h * 2
            x2 = x1 + col_w_row2
            y2 = y1 + row_h - gap
            self.keys.append(VirtualKey(char=char, display_label=char, x1=x1, y1=y1, x2=x2, y2=y2))

        # Row 3: Special Keys [SPACE], [BACKSPACE], [ENTER], [CLOSE]
        y1_row3 = start_y + row_h * 3
        y2_row3 = y1_row3 + row_h - gap

        specials = [
            ("SPACE", "␣ Space", 0.40, False),
            ("BACKSPACE", "⌫ Back", 0.20, True),
            ("ENTER", "⏎ Enter", 0.20, True),
            ("CLOSE", "✕ Close", 0.16, True),
        ]

        curr_x = start_x
        for code, label, width_ratio, is_spec in specials:
            btn_w = int(kb_w * width_ratio) - gap
            self.keys.append(
                VirtualKey(
                    char=code,
                    display_label=label,
                    x1=curr_x,
                    y1=y1_row3,
                    x2=curr_x + btn_w,
                    y2=y2_row3,
                    is_special=is_spec,
                )
            )
            curr_x += btn_w + gap

    def find_key(self, x: int, y: int) -> Optional[VirtualKey]:
        for key in self.keys:
            if key.contains(x, y):
                return key
        return None
