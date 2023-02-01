#
#    Copyright 2023 Picovoice Inc.
#
#    You may not use this file except in compliance with the license. A copy of the license is located in the "LICENSE"
#    file accompanying this source.
#
#    Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
#    an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
#    specific language governing permissions and limitations under the License.
#
import argparse
import os
import struct
import sys
import unittest
import wave
from typing import Optional, Sequence

import numpy as np
from numpy.typing import NDArray

from _koala import Koala
from _util import default_library_path, default_model_path


class KoalaTestCase(unittest.TestCase):
    ACCESS_KEY: str
    AUDIO_PATH = os.path.join(os.path.dirname(__file__), '../../resources/audio_samples/test.wav')

    pcm: Sequence[int]
    koala: Koala
    window: NDArray[float]

    @classmethod
    def setUpClass(cls):
        with wave.open(os.path.join(os.path.dirname(__file__), '../../resources/audio_samples/test.wav'), 'rb') as f:
            buffer = f.readframes(f.getnframes())
            cls.pcm = struct.unpack('%dh' % (len(buffer) / struct.calcsize('h')), buffer)

        cls.koala = Koala(
            access_key=cls.ACCESS_KEY,
            model_path=default_model_path('../..'),
            library_path=default_library_path('../..'))

        cls.window = np.hanning(cls.koala.frame_length)

    def test_frame_length(self) -> None:
        self.assertGreater(self.koala.frame_length, 0)

    def test_delay_sample(self) -> None:
        self.assertGreaterEqual(self.koala.delay_sample, 0)

    def _run_test(
            self,
            input_pcm: Sequence[int],
            reference_pcm: Optional[Sequence[int]] = None,
            tolerance: float = 1e-4) -> None:
        num_samples = len(input_pcm)
        frame_length = self.koala.frame_length
        delay_sample = self.koala.delay_sample
        if reference_pcm is not None:
            reference_pcm = np.pad(reference_pcm, pad_width=(delay_sample, 0))

        for frame_start in range(0, num_samples - frame_length, frame_length):
            enhanced_pcm = self.koala.process(input_pcm[frame_start:frame_start + frame_length])
            spectrogram = np.fft.rfft(enhanced_pcm)
            if reference_pcm is not None:
                spectrogram -= np.fft.rfft(reference_pcm[frame_start:frame_start + frame_length])
            spectrogram /= 2 ** 15
            self.assertLess(np.linalg.norm(spectrogram), tolerance)

    @staticmethod
    def _create_noise(num_samples: int, amplitude: float = 0.5) -> NDArray[int]:
        # spectrogram = np.fft.rfft(np.random.randn(num_samples))
        # freq_curve = 1 / np.where(spectrogram == 0, np.inf, np.sqrt(np.fft.rfftfreq(num_samples)))
        # freq_curve /= np.sqrt(np.mean(freq_curve ** 2))
        # spectrogram = np.fft.irfft(spectrogram * freq_curve) * amplitude * (2 ** 15)
        spectrogram = np.random.randn(num_samples) * amplitude * (2 ** 15)
        return spectrogram.astype(np.int16)

    def test_pure_speech(self) -> None:
        self._run_test(self.pcm, self.pcm)

    def test_pure_noise(self) -> None:
        noise_pcm = self._create_noise(5 * self.koala.sample_rate)
        self._run_test(noise_pcm)

    def test_mixed(self) -> None:
        noisy_pcm = self.pcm + self._create_noise(len(self.pcm), amplitude=0.2)
        self._run_test(noisy_pcm, self.pcm)

    def test_version(self):
        version = self.koala.version
        self.assertIsInstance(version, str)
        self.assertGreater(len(version), 0)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--access-key', required=True)
    args = parser.parse_args()

    KoalaTestCase.ACCESS_KEY = args.access_key
    unittest.main(argv=sys.argv[:1])
