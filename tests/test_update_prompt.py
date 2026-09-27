from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from update_prompt import should_offer, remind_later


class UpdatePromptTests(TestCase):
    def test_later_persists_for_one_day_only_for_same_version(self):
        with TemporaryDirectory() as folder:
            self.assertTrue(should_offer(folder,'0.13.5',100))
            remind_later(folder,'0.13.5',100)
            self.assertFalse(should_offer(str(Path(folder)),'0.13.5',86499))
            self.assertTrue(should_offer(folder,'0.13.5',86500))
            self.assertTrue(should_offer(folder,'0.13.6',101))

    def test_bad_preferences_do_not_block_updates(self):
        with TemporaryDirectory() as folder:
            for content in ('broken','null','[]','{}','{"version":"0.13.5","until":"bad"}'):
                (Path(folder)/'update-later.json').write_text(content,encoding='utf-8')
                self.assertTrue(should_offer(folder,'0.13.5',100))
