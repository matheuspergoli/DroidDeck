import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / 'app/src/main/cpp/waylandcomp/src/compositor.c'


def extract_function(source, name):
    match = re.search(r'^static (?:uint32_t|int64_t) ' + re.escape(name) +
                      r'\([^;]*?\) \{', source, re.MULTILINE)
    if match is None:
        raise AssertionError(f'Missing compositor function: {name}')
    cursor, depth = match.end(), 1
    while depth:
        depth += (source[cursor] == '{') - (source[cursor] == '}')
        cursor += 1
    return source[match.start():cursor]


PREAMBLE = r'''
#include <inttypes.h>
#include <stdatomic.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
static atomic_int g_output_refresh_mhz;
static int64_t g_tick_vsync_ns;
static int64_t g_last_vsync_ns;
'''

MAIN = r'''
int main(int argc, char **argv) {
    if (argc != 5) return 2;
    atomic_store(&g_output_refresh_mhz, (int)strtol(argv[1], NULL, 10));
    g_tick_vsync_ns = strtoll(argv[2], NULL, 10);
    g_last_vsync_ns = strtoll(argv[3], NULL, 10);
    printf("%" PRId64 "\n", presented_ns(strtoll(argv[4], NULL, 10)));
    return 0;
}
'''


class PresentationTimestampsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        compiler = shutil.which(os.environ.get('CC', 'cc'))
        if compiler is None:
            raise unittest.SkipTest('A host C compiler is required')
        cls.folder = tempfile.TemporaryDirectory(prefix='droiddeck-presentation-')
        cls.addClassCleanup(cls.folder.cleanup)
        path = Path(cls.folder.name)
        source = SOURCE.read_text()
        harness = PREAMBLE + '\n'.join(
            extract_function(source, name)
            for name in ('nominal_refresh_ns', 'presented_ns')
        ) + MAIN
        (path / 'presentation.c').write_text(harness)
        cls.binary = path / 'presentation-test'
        build = subprocess.run(
            [compiler, '-std=c11', '-Wall', '-Wextra', '-Werror', '-O2',
             str(path / 'presentation.c'), '-o', str(cls.binary)],
            capture_output=True, text=True, timeout=30,
        )
        if build.returncode:
            raise AssertionError(build.stderr)

    def expect_stamp(self, hz, tick, received, scene, expected):
        result = subprocess.run(
            [str(self.binary), str(hz * 1000), str(tick), str(received), str(scene)],
            capture_output=True, text=True, timeout=5,
        )
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual(expected, int(result.stdout))

    def test_recent_tick_keeps_display_cadence(self):
        for hz in (60, 90, 120, 144):
            with self.subTest(hz=hz):
                self.expect_stamp(hz, 1_000_000_000, 1_000_500_000,
                                  1_001_000_000, 1_000_000_000)

    def test_tick_after_scene_start_keeps_display_cadence(self):
        for hz in (60, 90, 120, 144):
            with self.subTest(hz=hz):
                self.expect_stamp(hz, 1_001_000_000, 1_002_000_000,
                                  1_000_000_000, 1_001_000_000)

    def test_old_tick_with_recent_callback_falls_back(self):
        for hz in (60, 90, 120, 144):
            with self.subTest(hz=hz):
                self.expect_stamp(hz, 900_000_000, 999_500_000,
                                  1_000_000_000, 1_000_000_000)

    def test_missing_or_late_callback_falls_back(self):
        for hz in (60, 90, 120, 144):
            for tick, received, scene in (
                (0, 999_500_000, 1_000_000_000),
                (500_000, 0, 1_000_000),
                (999_500_000, 900_000_000, 1_000_000_000),
            ):
                with self.subTest(hz=hz, tick=tick, received=received):
                    self.expect_stamp(hz, tick, received, scene, scene)

    def test_far_future_tick_falls_back(self):
        for hz in (60, 90, 120, 144):
            with self.subTest(hz=hz):
                self.expect_stamp(hz, 1_100_000_000, 999_500_000,
                                  1_000_000_000, 1_000_000_000)

    def test_interval_boundary_at_different_refresh_rates(self):
        for hz in (60, 90, 120, 144):
            interval = 1_000_000_000 // hz
            scene = 1_000_000_000
            for offset, expected in (
                (-interval - 1, scene),
                (-interval, scene - interval),
                (interval, scene + interval),
                (interval + 1, scene),
            ):
                with self.subTest(hz=hz, offset=offset):
                    self.expect_stamp(hz, scene + offset, scene, scene, expected)

    def test_unknown_refresh_uses_sixty_hz(self):
        self.expect_stamp(0, 1_001_000_000, 1_002_000_000,
                          1_000_000_000, 1_001_000_000)


if __name__ == '__main__':
    unittest.main()
