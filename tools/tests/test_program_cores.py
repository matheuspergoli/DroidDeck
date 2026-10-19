import os
from pathlib import Path
import subprocess
import tempfile
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / 'linuxfs/overlay/usr/local/bin/droiddeck-session'
SOURCE = SCRIPT.read_text()
FUNCTION = SOURCE[SOURCE.index('program_cores() {'):].split('\n}\n', 1)[0] + '\n}\n'


class ProgramCoresTest(unittest.TestCase):
    def selected(self, frequencies, model='', requested='', pin=True, taskset=True):
        with tempfile.TemporaryDirectory(prefix='droiddeck-program-cores-') as folder:
            root = Path(folder)
            for core, frequency in enumerate(frequencies):
                node = root / f'cpu{core}' / 'cpufreq'
                node.mkdir(parents=True)
                (node / 'cpuinfo_max_freq').write_text(f'{frequency}\n')
            function = FUNCTION.replace('/sys/devices/system/cpu', str(root))
            environment = dict(os.environ, BL_SOC_MODEL=model, BL_GAME_CPUS=requested,
                               BL_PIN_CORES='1' if pin else '0')
            code = f'command() {{ return {0 if taskset else 1}; }}\n' + function + '\nprogram_cores\n'
            result = subprocess.run(['bash', '-c', code], env=environment,
                                    capture_output=True, text=True, timeout=10)
            self.assertEqual(0, result.returncode, result.stderr)
            return result.stdout.strip()

    def test_known_oryon_six_plus_two_keeps_inherited_affinity(self):
        frequencies = [3_532_800] * 6 + [4_470_000] * 2
        for model in ('SM8750', 'SM8750-AC', 'SM8850', 'SM8850-AC', 'sm8750-ac'):
            with self.subTest(model=model):
                self.assertEqual('', self.selected(frequencies, model))

    def test_explicit_user_mask_wins_on_oryon(self):
        self.assertEqual('6,7', self.selected([3_532_800] * 6 + [4_470_000] * 2,
                                             'SM8750-AC', requested='6,7'))

    def test_disabled_pinning_keeps_inherited_affinity_even_with_override(self):
        self.assertEqual('', self.selected([3_532_800] * 6 + [4_470_000] * 2,
                                          'SM8750-AC', requested='6,7', pin=False))

    def test_unknown_six_plus_two_is_not_assumed_to_be_oryon(self):
        for model in ('', 'UNKNOWN', 'SM87500', 'SM8750X'):
            with self.subTest(model=model):
                self.assertEqual('6,7', self.selected([1_800_000] * 6 + [2_400_000] * 2, model))

    def test_traditional_little_clusters_keep_existing_selection(self):
        for frequencies, model, expected in (
            ([1_804_800] * 4 + [2_419_200] * 3 + [2_841_600], 'SM8250-AC', '4,5,6,7'),
            ([1_800_000] * 3 + [2_800_000] * 4 + [3_200_000], 'SM8550', '3,4,5,6,7'),
            ([2_265_600] * 2 + [3_148_800] * 5 + [3_398_400], 'SM8650-AC', '2,3,4,5,6,7'),
        ):
            with self.subTest(model=model):
                self.assertEqual(expected, self.selected(frequencies, model))

    def test_homogeneous_or_missing_frequency_data_keeps_inherited_affinity(self):
        for frequencies in ([2_000_000] * 8, []):
            with self.subTest(frequencies=frequencies):
                self.assertEqual('', self.selected(frequencies))

    def test_missing_taskset_keeps_inherited_affinity(self):
        self.assertEqual('', self.selected([1_800_000] * 4 + [2_800_000] * 4,
                                          'SM8650', requested='4,5', taskset=False))


if __name__ == '__main__':
    unittest.main()
