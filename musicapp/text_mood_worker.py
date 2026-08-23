"""Standalone worker: classifies one line of text into an emotion label.

Run in a separate process from the Django server because this project also
loads DeepFace/TensorFlow (see musicapp/views.py), and on this environment
having both TensorFlow and PyTorch loaded in the same process causes a native
DLL initialization failure on Windows. Reads one line of text from stdin,
prints a JSON object {"label": "..."} to stdout.
"""
import json
import sys


def main():
    text = sys.stdin.readline().strip()
    if not text:
        print(json.dumps({'error': 'empty text'}))
        return

    from transformers import pipeline
    classifier = pipeline(
        'text-classification',
        model='j-hartmann/emotion-english-distilroberta-base',
    )
    result = classifier(text)[0]
    print(json.dumps({'label': result['label']}))


if __name__ == '__main__':
    main()
