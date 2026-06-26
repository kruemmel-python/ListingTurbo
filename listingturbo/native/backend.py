from __future__ import annotations

import ctypes
import platform
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Final

ABI_VERSION: Final[int] = 1
BACKEND_CPU: Final[int] = 1
BACKEND_OPENCL: Final[int] = 2


@dataclass(frozen=True, slots=True)
class NativeAnalysis:
    available: bool
    backend_flags: int
    brightness: float | None
    contrast: float | None
    sharpness: float | None
    pixels: int
    message: str

    @property
    def used_opencl(self) -> bool:
        return bool(self.backend_flags & BACKEND_OPENCL)

    @property
    def backend_name(self) -> str:
        if not self.available:
            return "Python/Pillow"
        return "C++/OpenCL" if self.used_opencl else "C++/CPU"


@dataclass(frozen=True, slots=True)
class NativeEnhancement:
    available: bool
    backend_flags: int
    data: bytes | None
    message: str

    @property
    def used_opencl(self) -> bool:
        return bool(self.backend_flags & BACKEND_OPENCL)

    @property
    def backend_name(self) -> str:
        if not self.available:
            return "Python/Pillow"
        return "C++/OpenCL" if self.used_opencl else "C++/CPU"


class _NativeMetrics(ctypes.Structure):
    _fields_ = [
        ("abi_version", ctypes.c_uint32),
        ("backend_flags", ctypes.c_uint32),
        ("brightness", ctypes.c_double),
        ("contrast", ctypes.c_double),
        ("sharpness", ctypes.c_double),
        ("pixels", ctypes.c_uint64),
        ("status", ctypes.c_uint32),
        ("message", ctypes.c_char * 256),
    ]


class _NativeLibrary:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.dll = ctypes.CDLL(str(path))
        self.dll.lt_native_version.restype = ctypes.c_char_p
        self.dll.lt_backend_info.argtypes = [ctypes.c_char_p, ctypes.c_int]
        self.dll.lt_backend_info.restype = ctypes.c_int
        self.dll.lt_analyze_rgb8.argtypes = [
            ctypes.c_void_p,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.POINTER(_NativeMetrics),
        ]
        self.dll.lt_analyze_rgb8.restype = ctypes.c_int
        self.dll.lt_enhance_rgb8.argtypes = [
            ctypes.c_void_p,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_void_p,
            ctypes.c_int,
            ctypes.c_float,
            ctypes.c_float,
            ctypes.c_float,
            ctypes.POINTER(_NativeMetrics),
        ]
        self.dll.lt_enhance_rgb8.restype = ctypes.c_int

    def version(self) -> str:
        raw = self.dll.lt_native_version()
        return raw.decode("utf-8", errors="replace") if raw else "unbekannt"

    def info(self) -> str:
        buffer = ctypes.create_string_buffer(2048)
        result = self.dll.lt_backend_info(buffer, len(buffer))
        if result != 0:
            return f"Native Backend meldet Fehlercode {result}"
        return buffer.value.decode("utf-8", errors="replace")

    def analyze(self, data: bytes, width: int, height: int, stride: int) -> NativeAnalysis:
        in_buffer = ctypes.create_string_buffer(data)
        metrics = _NativeMetrics()
        result = self.dll.lt_analyze_rgb8(in_buffer, width, height, stride, ctypes.byref(metrics))
        message = bytes(metrics.message).split(b"\0", 1)[0].decode("utf-8", errors="replace")
        if result != 0 or metrics.status != 0:
            return NativeAnalysis(False, 0, None, None, None, 0, message or f"Native Analyse fehlgeschlagen: {result}")
        if metrics.abi_version != ABI_VERSION:
            return NativeAnalysis(False, 0, None, None, None, 0, f"ABI-Mismatch: {metrics.abi_version} statt {ABI_VERSION}")
        return NativeAnalysis(
            available=True,
            backend_flags=int(metrics.backend_flags),
            brightness=float(metrics.brightness),
            contrast=float(metrics.contrast),
            sharpness=float(metrics.sharpness),
            pixels=int(metrics.pixels),
            message=message,
        )

    def enhance(
        self,
        data: bytes,
        width: int,
        height: int,
        src_stride: int,
        dst_stride: int,
        brightness_factor: float,
        contrast_factor: float,
        sharpen_amount: float,
    ) -> NativeEnhancement:
        in_buffer = ctypes.create_string_buffer(data)
        out_buffer = ctypes.create_string_buffer(dst_stride * height)
        metrics = _NativeMetrics()
        result = self.dll.lt_enhance_rgb8(
            in_buffer,
            width,
            height,
            src_stride,
            out_buffer,
            dst_stride,
            ctypes.c_float(brightness_factor),
            ctypes.c_float(contrast_factor),
            ctypes.c_float(sharpen_amount),
            ctypes.byref(metrics),
        )
        message = bytes(metrics.message).split(b"\0", 1)[0].decode("utf-8", errors="replace")
        if result != 0 or metrics.status != 0:
            return NativeEnhancement(False, 0, None, message or f"Native Enhancement fehlgeschlagen: {result}")
        if metrics.abi_version != ABI_VERSION:
            return NativeEnhancement(False, 0, None, f"ABI-Mismatch: {metrics.abi_version} statt {ABI_VERSION}")
        return NativeEnhancement(True, int(metrics.backend_flags), bytes(out_buffer.raw), message)


@lru_cache(maxsize=1)
def _load_library() -> _NativeLibrary | None:
    for candidate in _candidate_library_paths():
        if not candidate.exists():
            continue
        try:
            return _NativeLibrary(candidate)
        except OSError:
            continue
    return None


def _candidate_library_paths() -> tuple[Path, ...]:
    project_root = Path(__file__).resolve().parents[2]
    system = platform.system().lower()
    match system:
        case "windows":
            names = ("listingturbo_native.dll",)
        case "darwin":
            names = ("liblistingturbo_native.dylib", "listingturbo_native.dylib")
        case _:
            names = ("liblistingturbo_native.so", "listingturbo_native.so")

    roots = (
        project_root / "native" / "bin",
        project_root / "native" / "build",
        project_root,
    )
    return tuple(root / name for root in roots for name in names)


def runtime_status() -> dict[str, str | bool]:
    library = _load_library()
    if library is None:
        return {
            "available": False,
            "version": "nicht geladen",
            "detail": "Native DLL/SO nicht gefunden. build_native.ps1 oder native/build_native.ps1 ausführen.",
        }
    return {
        "available": True,
        "version": library.version(),
        "detail": library.info(),
    }


def backend_info_summary() -> str:
    status = runtime_status()
    if not status["available"]:
        return f"Native Backend: inaktiv — {status['detail']}"
    return f"Native Backend: aktiv — {status['detail']}"


def analyze_rgb_bytes(data: bytes, width: int, height: int, stride: int) -> NativeAnalysis | None:
    library = _load_library()
    if library is None:
        return None
    expected = stride * height
    if width <= 0 or height <= 0 or stride < width * 3 or len(data) < expected:
        return NativeAnalysis(False, 0, None, None, None, 0, "Ungültiger RGB8-Puffer")
    return library.analyze(data[:expected], width, height, stride)


def enhance_rgb_bytes(
    data: bytes,
    width: int,
    height: int,
    src_stride: int,
    *,
    brightness_factor: float = 1.0,
    contrast_factor: float = 1.0,
    sharpen_amount: float = 0.0,
) -> NativeEnhancement | None:
    library = _load_library()
    if library is None:
        return None
    expected = src_stride * height
    if width <= 0 or height <= 0 or src_stride < width * 3 or len(data) < expected:
        return NativeEnhancement(False, 0, None, "Ungültiger RGB8-Puffer")
    return library.enhance(
        data[:expected],
        width,
        height,
        src_stride,
        width * 3,
        brightness_factor,
        contrast_factor,
        sharpen_amount,
    )
