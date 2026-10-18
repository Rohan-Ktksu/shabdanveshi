import unittest
import numpy as np
from .bridge import GlossBridge


class BridgeTests(unittest.TestCase):
    def test_only_exact_gloss_and_matching_part_of_speech_link(self):
        entries=[
            dict(word='poet',aliases=[],language='en',part_of_speech='noun',definition='writer of poems'),
            dict(word='कवि',aliases=[],language='hi',part_of_speech='noun',definition='a poet'),
            dict(word='कविता',aliases=[],language='hi',part_of_speech='noun',definition='poetry'),
            dict(word='कवि',aliases=[],language='hi',part_of_speech='adjective',definition='poet'),
        ]
        score=np.array([.9,.5,.4,.3],dtype=np.float32)
        np.testing.assert_allclose(GlossBridge(entries).apply(score),[.9,.9,.4,.3])
        np.testing.assert_allclose(score,[.9,.5,.4,.3])


if __name__=='__main__': unittest.main()
