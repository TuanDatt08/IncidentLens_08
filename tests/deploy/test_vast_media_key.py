import os
import subprocess
import tempfile
import unittest
from pathlib import Path


@unittest.skipIf(os.name == 'nt', 'Vast startup helper runs on Linux')
class VastMediaKeyTest(unittest.TestCase):
    def test_existing_media_public_key_restore_is_restricted_and_idempotent(self):
        with tempfile.TemporaryDirectory() as directory:
            key = Path(directory) / 'media'
            subprocess.run(['ssh-keygen', '-q', '-t', 'ed25519', '-N', '', '-f', str(key)], check=True)
            authorized = Path(directory) / 'authorized_keys'
            authorized.write_text('# existing entries preserved')
            helper = Path('deploy/vast/restore_media_key.sh')
            for _ in range(2):
                subprocess.run(['bash', str(helper), str(key.with_suffix('.pub')), str(authorized)], check=True)
            lines = authorized.read_text().splitlines()
            self.assertEqual(lines[0], '# existing entries preserved')
            self.assertEqual(len(lines), 2)
            self.assertTrue(lines[1].startswith('restrict,port-forwarding,permitopen="127.0.0.1:18000",command="/bin/false" ssh-ed25519 '))
            self.assertEqual(authorized.stat().st_mode & 0o777, 0o600)


if __name__ == '__main__':
    unittest.main()
