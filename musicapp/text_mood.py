import json
import os
import subprocess
import sys

TEXT_EMOTION_TO_MOOD = {
    'joy': 'Happy',
    'sadness': 'Sad',
    'anger': 'Angry',
    'fear': 'Fear',
    'neutral': 'Neutral',
    'disgust': 'Angry',
    'surprise': 'Happy',
}

_WORKER_PATH = os.path.join(os.path.dirname(__file__), 'text_mood_worker.py')


def classify_text_mood(text):
    """Runs the emotion classifier in a separate process.

    This process already imports DeepFace/TensorFlow (musicapp/views.py), and
    on Windows that leaves the process unable to also load PyTorch (a native
    DLL init failure) — the classifier has to live in its own process.
    """
    env = dict(os.environ, HF_HUB_OFFLINE='1', KMP_DUPLICATE_LIB_OK='TRUE')
    result = subprocess.run(
        [sys.executable, _WORKER_PATH],
        input=text + '\n',
        capture_output=True,
        text=True,
        timeout=90,
        env=env,
    )
    if result.returncode != 0:
        raise RuntimeError(f'text mood worker failed: {result.stderr[-2000:]}')
    payload = json.loads(result.stdout.strip().splitlines()[-1])
    if 'error' in payload:
        raise ValueError(payload['error'])
    return TEXT_EMOTION_TO_MOOD.get(payload['label'].lower(), 'Neutral')
