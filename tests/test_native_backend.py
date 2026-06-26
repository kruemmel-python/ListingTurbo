from __future__ import annotations

from listingturbo.native.backend import analyze_rgb_bytes, backend_info_summary, runtime_status


def test_native_backend_status_is_safe() -> None:
    status = runtime_status()
    assert "available" in status
    assert "detail" in status
    assert backend_info_summary().startswith("Native Backend:")


def test_native_analyze_rgb_buffer_if_library_exists() -> None:
    data = bytes((255, 0, 0, 0, 255, 0, 0, 0, 255, 255, 255, 255))
    result = analyze_rgb_bytes(data, 2, 2, 6)
    if result is None:
        return
    assert result.available
    assert result.pixels == 4
    assert result.brightness is not None and result.brightness > 0
    assert result.contrast is not None and result.contrast >= 0
    assert result.sharpness is not None and result.sharpness >= 0
