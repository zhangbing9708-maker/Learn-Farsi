"""Fast Persian speech synthesis: the Piper "gyro" voice through sherpa-onnx's C API (ctypes).

make_audio.py uses this when the shared-library build of sherpa-onnx is in ~/.cache/wnw-tts (it downloads it
otherwise): each worker process loads the voice once and then synthesises many sentences, which is several
times faster than starting the command-line program for every sentence.

The config struct is passed as a zeroed buffer with only the VITS paths filled in; every other field takes
its default inside sherpa-onnx (SHERPA_ONNX_OR in c-api.cc), so the code doesn't depend on the exact size of
the newer model configs that follow the VITS one in the struct.
"""
import ctypes
import os
import subprocess
import tempfile

_TTS = None
_LIB = None


class _Audio(ctypes.Structure):
    _fields_ = [("samples", ctypes.POINTER(ctypes.c_float)), ("n", ctypes.c_int32), ("sample_rate", ctypes.c_int32)]


def init(libdir, voice_dir, model_file):
    global _TTS, _LIB
    ctypes.CDLL(os.path.join(libdir, "libonnxruntime.so"), mode=ctypes.RTLD_GLOBAL)
    lib = ctypes.CDLL(os.path.join(libdir, "libsherpa-onnx-c-api.so"))
    lib.SherpaOnnxCreateOfflineTts.restype = ctypes.c_void_p
    lib.SherpaOnnxCreateOfflineTts.argtypes = [ctypes.c_void_p]
    lib.SherpaOnnxOfflineTtsGenerate.restype = ctypes.POINTER(_Audio)
    lib.SherpaOnnxOfflineTtsGenerate.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_int32, ctypes.c_float]
    lib.SherpaOnnxDestroyOfflineTtsGeneratedAudio.argtypes = [ctypes.POINTER(_Audio)]
    lib.SherpaOnnxWriteWave.argtypes = [ctypes.POINTER(ctypes.c_float), ctypes.c_int32, ctypes.c_int32, ctypes.c_char_p]
    buf = ctypes.create_string_buffer(16384)
    strings = [os.path.join(voice_dir, model_file), os.path.join(voice_dir, "tokens.txt"), os.path.join(voice_dir, "espeak-ng-data")]
    keep = [ctypes.create_string_buffer(s.encode()) for s in strings]
    base = ctypes.addressof(buf)
    for off, s in zip((0, 16, 24), keep):          # vits.model, vits.tokens, vits.data_dir
        ctypes.c_void_p.from_address(base + off).value = ctypes.addressof(s)
    ctypes.c_int32.from_address(base + 56).value = 1  # model.num_threads
    tts = lib.SherpaOnnxCreateOfflineTts(base)
    if not tts:
        raise RuntimeError("sherpa-onnx could not load the voice")
    _TTS, _LIB = tts, lib
    init.keep = (buf, keep)


def synth(item):
    """item = (audio_id, text, out_dir) -> audio_id. Writes out_dir/<id>.mp3."""
    i, text, out_dir = item
    a = _LIB.SherpaOnnxOfflineTtsGenerate(_TTS, text.encode("utf-8"), 0, ctypes.c_float(1.0))
    with tempfile.TemporaryDirectory() as td:
        wav = os.path.join(td, "a.wav")
        _LIB.SherpaOnnxWriteWave(a.contents.samples, a.contents.n, a.contents.sample_rate, wav.encode())
        _LIB.SherpaOnnxDestroyOfflineTtsGeneratedAudio(a)
        out = os.path.join(out_dir, i + ".mp3")
        subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", wav, "-af", "adelay=60:all=1", "-ac", "1", "-ar", "22050",
                        "-c:a", "libmp3lame", "-b:a", "32k", out + ".tmp.mp3"], check=True)
        os.replace(out + ".tmp.mp3", out)
    return i
