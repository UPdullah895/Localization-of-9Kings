"""Regression tests for tools/visual.py (run: python -m unittest discover tests).

Each case is a bug that reached the game or a review: expected strings are the
visual (left-to-right, presentation-form) text TMP must receive.
"""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

from fontTools.ttLib import TTFont  # noqa: E402

import font_merge  # noqa: E402
import visual  # noqa: E402
from arabic_reshaper import ArabicReshaper  # noqa: E402

RESHAPE = ArabicReshaper({"delete_harakat": False}).reshape


def v(logical: str) -> str:
    """Expected visual text, written by hand: shape, then reverse character order."""
    return RESHAPE(logical)[::-1]


class Visual(unittest.TestCase):
    def test_plain_line_is_shaped_and_reversed(self):
        self.assertEqual(visual.visual("ملك التعاويذ"), v("ملك التعاويذ"))

    def test_colour_tag_with_placeholder_inside_stays_whole(self):
        # I2's runtime fix split <color=#{KINGCOLOR}> at the inner brace.
        self.assertEqual(visual.visual("ملك <color=#{KINGCOLOR}>التعاويذ</color>"),
                         f"<color=#{{KINGCOLOR}}>{v('التعاويذ')}</color> {v('ملك')}")

    def test_two_placeholders_keep_their_places(self):
        # I2 swapped {VAR1} and {VAR2}.
        out = visual.visual("مقداره {VAR1}. {VAR2} سلسلة")
        self.assertEqual(out, f"{v('سلسلة')} {{VAR2}} .{{VAR1}} {v('مقداره')}")

    def test_sign_and_percent_stay_with_the_number(self):
        self.assertEqual(visual.visual("ضرر +{VAR1}%"), f"+{{VAR1}}% {v('ضرر')}")
        self.assertEqual(visual.visual("+{VAR1} نقطة"), f"{v('نقطة')} +{{VAR1}}")

    def test_space_outside_tag_is_not_coloured(self):
        out = visual.visual("لديك <color=red>{VAR1}</color> أرواح")
        self.assertIn("<color=red>{VAR1}</color> ", out)

    def test_latin_run_keeps_its_order(self):
        self.assertEqual(visual.visual("اضغط R2 الآن"), f"{v('الآن')} R2 {v('اضغط')}")

    def test_brackets_are_mirrored(self):
        self.assertEqual(visual.visual("(نص)"), f"({v('نص')})")


class Wrapping(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        noto = (ROOT / "fonts/NotoSansArabic-Medium.ttf").read_bytes()
        cls.metrics = visual.Metrics(TTFont(__import__("io").BytesIO(noto)))

    def test_lines_come_out_top_to_bottom(self):
        # TMP wrapping a reversed paragraph put the last line on top.
        out = visual.visual("كلمة أولى ثم كلمة ثانية ثم كلمة ثالثة", metrics=self.metrics, max_em=6)
        lines = out.split("\n")
        self.assertGreater(len(lines), 1)
        self.assertTrue(lines[0].endswith(v("كلمة")))           # first logical word, rightmost
        self.assertTrue(lines[-1].startswith(v("ثالثة")))

    def test_wrapped_space_keeps_its_own_tags(self):
        out = visual.visual("أ <color=red>ب</color> ج د هـ و ز ح ط ي", metrics=self.metrics, max_em=4)
        self.assertNotIn(" </color>", out)
        self.assertNotIn("\u00a0</color>", out)

    def test_wrapped_lines_cannot_be_rewrapped(self):
        # TMP breaking a line again moved its logical first word to the next line.
        out = visual.visual("كلمة أولى ثم كلمة ثانية ثم كلمة ثالثة", metrics=self.metrics, max_em=6)
        self.assertNotIn(" ", out)
        self.assertIn("\u00a0", out)
        self.assertIn(" ", visual.visual("كلمة أولى"))            # unwrapped text: TMP may wrap it


class Marks(unittest.TestCase):
    def test_harakat_become_one_anchored_glyph(self):
        noto = TTFont(ROOT / "fonts/NotoSansArabic-Medium.ttf")
        marks = visual.MarkGlyphs(noto, noto)
        out = visual.visual("الرُّحَّل", marks)
        self.assertFalse(any(0x064B <= ord(c) <= 0x0652 for c in out))   # no raw harakat left
        self.assertEqual(len(marks.glyphs), 2)                            # ر+ُّ and ح+َّ
        data = font_merge.add_marks((ROOT / "fonts/NotoSansArabic-Medium.ttf").read_bytes(),
                                    (ROOT / "fonts/NotoSansArabic-Medium.ttf").read_bytes(), marks.spec())
        cmap = TTFont(__import__("io").BytesIO(data)).getBestCmap()
        self.assertTrue(all(int(cp, 16) in cmap for cp in marks.spec()))


if __name__ == "__main__":
    unittest.main()
