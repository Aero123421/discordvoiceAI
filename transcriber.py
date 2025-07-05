import sys
from faster_whisper import WhisperModel

model = WhisperModel('small', device='cpu', compute_type='int8')
segments, _ = model.transcribe(sys.argv[1])
print(''.join(seg.text for seg in segments))

