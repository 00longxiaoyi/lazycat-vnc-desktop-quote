import importlib.util
import json
import pathlib
import struct
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('prepare', ROOT / 'scripts/prepare.py')
prepare = importlib.util.module_from_spec(spec)
spec.loader.exec_module(prepare)


class PrepareTests(unittest.TestCase):
    def test_patch_sets_paths_before_store_initialization(self):
        source = "var userDataDir = app.getPath('userData')\ndefaultPath: defaultName || 'quotation-backup.json'\ndefaultPath: defaultName,"
        patched = prepare.patch_main(source)
        self.assertLess(patched.index("app.setPath('userData'"), patched.index('var userDataDir'))
        self.assertIn('path.join(persistentExports, path.basename(defaultName)),', patched)
        self.assertIn("path.basename(defaultName || 'quotation-backup.json')", patched)

    def test_patch_rejects_unexpected_upstream(self):
        with self.assertRaises(AssertionError):
            prepare.patch_main('unknown source')

    @unittest.skipUnless((ROOT / 'images/vendor/app.asar').is_file(), 'Run scripts/prepare.py first')
    def test_prepared_business_files_unchanged_except_main(self):
        with tempfile.TemporaryDirectory() as tmp:
            original = pathlib.Path(tmp)
            asar = (ROOT / 'images/vendor/app.asar').read_bytes()
            prepare.unpack_asar(asar, original)
            output = ROOT / 'images/vendor/quote-desktop/resources/app'
            original_paths = {p.relative_to(original) for p in original.rglob('*') if p.is_file()}
            output_paths = {p.relative_to(output) for p in output.rglob('*') if p.is_file()}
            self.assertEqual(original_paths, output_paths)
            for path in original_paths:
                expected = (original / path).read_bytes()
                if str(path) == 'main.js':
                    expected = prepare.patch_main(expected.decode()).encode()
                self.assertEqual(expected, (output / path).read_bytes(), str(path))

    def test_asar_rejects_path_traversal(self):
        header = json.dumps({'files': {'..': {'files': {}}}}).encode()
        data = struct.pack('<IIII', 4, len(header) + 8, len(header) + 4, len(header)) + header
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError):
                prepare.unpack_asar(data, pathlib.Path(tmp))

    @unittest.skipUnless((ROOT / 'images/vendor/quote-desktop').is_dir(), 'Run scripts/prepare.py first')
    def test_complete_runtime(self):
        runtime = ROOT / 'images/vendor/quote-desktop'
        for filename in ('icudtl.dat', 'libffmpeg.so', 'libEGL.so', 'libGLESv2.so', 'chrome_crashpad_handler', 'quote-desktop'):
            self.assertTrue((runtime / filename).is_file(), filename)
        self.assertEqual(prepare.digest((ROOT / f'images/vendor/electron-v{prepare.VERSION}-linux-x64.zip').read_bytes()), prepare.RUNTIME_SHA256)


if __name__ == '__main__':
    unittest.main()
