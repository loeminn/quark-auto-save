import re
import unittest

from quark_auto_save import MagicRename


class MagicRenameTests(unittest.TestCase):
    def setUp(self):
        self.rename = MagicRename()

    def test_episode_and_season_widths(self):
        cases = [
            ("E1234.mp4", "{EEEE}", "1234"),
            ("S123E4.mp4", "{SSS}|{SXX}", "123|S123"),
            ("S2E3.mp4", "{S}|{SS}|{SSS}|{E}|{EE}|{EEE}", "2|02|002|3|03|003"),
            ("S02E003.mp4", "{S}|{SS}|{E}|{EE}", "02|02|003|003"),
            ("s2e3.mp4", "{SXX}E{EE}", "S02E03"),
            ("preview.mp4", "{SS}|{EE}|{SXX}", "||S01"),
            ("EP1234.mp4", "{EE}", "1234"),
            ("第1234集.mp4", "{EE}", "1234"),
            ("1234.mp4", "{EE}", "1234"),
        ]
        for filename, template, expected in cases:
            with self.subTest(filename=filename, template=template):
                self.assertEqual(self.rename.sub("", template, filename), expected)

    def test_tv_pattern_keeps_long_numbers(self):
        for template in ("", "{SXX}E{EE}.{EXT}"):
            pattern, replacement = self.rename.magic_regex_conv("$TV", template)
            self.assertEqual(
                self.rename.sub(pattern, replacement, "S123E1234.mp4"),
                "S123E1234.mp4",
            )

    def test_tv_prefers_episode_markers_over_metadata(self):
        cases = [
            ("Show.2024.S01E03.mp4", "S01E03.mp4", "0003"),
            ("Show.1080p.E03.mp4", "E03.mp4", "0003"),
            ("2024.Show.S01E03.mp4", "S01E03.mp4", "0003"),
            ("Show.1234.S123E5678.mp4", "S123E5678.mp4", "5678"),
            ("Show.2024.EP1234.mp4", "E1234.mp4", "1234"),
            ("Show.2024.第1234集.mp4", "E1234.mp4", "1234"),
            ("Show.2024.S1X1234.mp4", "S1E1234.mp4", "1234"),
            ("Show.1234.mp4", "E1234.mp4", "1234"),
            ("Show-1234.mp4", "E1234.mp4", "1234"),
            ("Show.2024.1234.mp4", "E1234.mp4", "1234"),
            ("Show.E2024.mp4", "E2024.mp4", "2024"),
        ]
        pattern, replacement = self.rename.magic_regex_conv("$TV", "")
        for filename, expected, episode in cases:
            with self.subTest(filename=filename):
                self.assertEqual(self.rename.sub(pattern, replacement, filename), expected)
                self.assertEqual(self.rename.sub("", "{EEEE}", filename), episode)
                self.assertEqual(
                    self.rename.sub(pattern, "E{EEEE}.{EXT}", filename),
                    "E" + episode + ".mp4",
                )

    def test_codec_tags_do_not_override_episodes(self):
        cases = [
            ("Show.03.1080p.x264.mp4", "E03.mp4", "03"),
            ("Show.03.x265.mkv", "E03.mkv", "03"),
            ("Show.第3集.x264.mp4", "E3.mp4", "03"),
            ("Show.x264.第3集.mp4", "E3.mp4", "03"),
            ("Show.X265.03.mp4", "E03.mp4", "03"),
            ("Show.x264.S01E03.mp4", "S01E03.mp4", "03"),
            ("Show.S01X03.x264.mp4", "S01E03.mp4", "03"),
            ("Show.S1X264.x265.mp4", "S1E264.mp4", "264"),
            ("Show.s123x265.x264.mp4", "s123E265.mp4", "265"),
            ("Show.X03.mp4", "E03.mp4", "03"),
            ("Show.X2640.mp4", "E2640.mp4", "2640"),
        ]
        pattern, replacement = self.rename.magic_regex_conv("$TV", "")
        for filename, expected, episode in cases:
            with self.subTest(filename=filename):
                self.assertEqual(self.rename.sub(pattern, replacement, filename), expected)
                self.assertEqual(self.rename.sub("", "{EE}", filename), episode)
                self.assertEqual(
                    self.rename.sub(pattern, "E{EE}.{EXT}", filename),
                    "E" + episode + "." + filename.rsplit(".", 1)[1],
                )

    def test_resolution_and_frame_rate_are_not_episode_markers(self):
        pattern, replacement = self.rename.magic_regex_conv("$TV", "")
        for metadata in ("1920x1080", "3840x2160", "1080p60", "720P50"):
            for filename in (
                f"Show.03.{metadata}.mp4",
                f"Show.{metadata}.03.mp4",
                f"Show.第03集.{metadata}.mp4",
                f"Show.{metadata}.S01X03.mp4",
            ):
                with self.subTest(filename=filename):
                    expected = "S01E03.mp4" if "S01X03" in filename else "E03.mp4"
                    self.assertEqual(self.rename.sub(pattern, replacement, filename), expected)
                    self.assertEqual(self.rename.sub("", "{EE}", filename), "03")
                    self.assertEqual(self.rename.sub(pattern, "E{EE}.{EXT}", filename), "E03.mp4")
        for filename, expected in (
            ("Show.1234.S123X265.mp4", "S123E265.mp4"),
            ("Show.P03.mp4", "E03.mp4"),
            ("Show.S01P03.mp4", "S01E03.mp4"),
        ):
            with self.subTest(filename=filename):
                self.assertEqual(self.rename.sub(pattern, replacement, filename), expected)
                self.assertEqual(self.rename.sub("", "{EE}", filename), "265" if "X265" in filename else "03")

    def test_episode_version_and_end_suffixes(self):
        pattern, replacement = self.rename.magic_regex_conv("$TV", "")
        for suffix in ("v2", "V12", "END", "end", "End", "v2END"):
            for number in ("03", "1234"):
                for metadata in ("1080p", "1920x1080", "1080p60", "x265"):
                    filename = f"Anime.{number}{suffix}.{metadata}.mkv"
                    with self.subTest(filename=filename):
                        self.assertEqual(
                            self.rename.sub(pattern, replacement, filename),
                            f"E{number}.mkv",
                        )
                        self.assertEqual(self.rename.sub("", "{E}", filename), number)
                        self.assertEqual(
                            self.rename.sub(pattern, "E{EEEE}.{EXT}", filename),
                            f"E{number.zfill(4)}.mkv",
                        )
        for filename in ("03v2.mp4", "Anime.03END.mp4"):
            with self.subTest(filename=filename):
                self.assertEqual(self.rename.sub(pattern, replacement, filename), "E03.mp4")
                self.assertEqual(self.rename.sub("", "{EE}", filename), "03")

    def test_metadata_alone_is_not_an_episode(self):
        pattern, _ = self.rename.magic_regex_conv("$TV", "")
        for filename in (
            "Show.2024.mp4", "Show.1080p.mp4", "Show.2024.1080p.mp4",
            "Show.x264.mp4", "Show.X265.mkv", "Show.1080p.x265.mp4",
            "Show.1920x1080.mp4", "Show.3840x2160.mp4", "Show.1080p60.mp4",
            "Show.1080p60v2.mp4", "Show.10bit.mp4", "Show.03version.mp4",
        ):
            with self.subTest(filename=filename):
                self.assertIsNone(re.search(pattern, filename))
                self.assertEqual(self.rename.sub("", "{EEEE}", filename), "")

    def test_capture_padding(self):
        cases = [
            (r"(\d+)", r"\1-{\1:02}-{\1:03}", "3", "3-03-003"),
            (r"(\d+)", r"{\1:02}", "1234", "1234"),
            (r"(\d+)", r"{\1:02}", "003", "003"),
            (r"(\w+)", r"{\1:02}", "text", "text"),
            (r"(\d+)?x", r"A{\1:02}B", "x", "AB"),
            (r"(\d+)", r"{\1:02}", "1 2", "01 02"),
            (r"(\d+)", r"{\1:02}", "text", "text"),
            (r"(\d+)\.(\w+)", r"{\1:02}.\2", "3.mp4", "03.mp4"),
            (r"(.+)", r"{\1:02}", r"a\1", r"a\1"),
        ]
        for pattern, template, filename, expected in cases:
            with self.subTest(template=template, filename=filename):
                self.assertEqual(self.rename.sub(pattern, template, filename), expected)

    def test_backslashes_before_padding(self):
        for count in range(7):
            template = "\\" * count + r"{\1:02}"
            expected = "\\" * ((count + 1) // 2) + ("{3:02}" if count % 2 else "03")
            with self.subTest(backslashes=count):
                self.assertEqual(self.rename.sub(r"(\d+)", template, "3"), expected)
                # A later padding expression must not break an earlier escaped brace.
                self.assertEqual(
                    self.rename.sub(r"(\d+)", template + r"-{\1:03}", "3"),
                    expected + "-003",
                )

    def test_directory_numbering_with_padded_captures(self):
        self.rename.set_dir_file_list(
            [{"file_name": "01.S02E03.mp4", "dir": False}],
            r"{II}.S{\1:02}E{\2:02}.mp4",
        )
        self.assertEqual(self.rename.dir_filename_dict, {1: "{II}.S02E03.mp4"})


if __name__ == "__main__":
    unittest.main()
