# SPDX-License-Identifier: AGPL-3.0-only
# Copyright 2026-present the Unsloth AI Inc. team. All rights reserved. See /studio/LICENSE.AGPL-3.0

"""Gives uv a whitespace-free -c/--override/-r file path. uv splits UV_OVERRIDE with
split_whitespace (every Unicode space, not only U+0020) and split -c/--override the same way
before 0.13: 8.3 short name on Windows, else a temp copy removed at exit; falls back to the
original path on error."""

from __future__ import annotations

import atexit
import os
import platform
import shutil
import tempfile

IS_WINDOWS = platform.system() == "Windows"

_UV_SAFE_PATH_TMPDIRS: list[str] = []


def _has_whitespace(value: str) -> bool:
    """True when uv's UV_OVERRIDE parser (``split_whitespace``) would split ``value``."""
    return any(ch.isspace() for ch in value)


@atexit.register
def _cleanup_uv_safe_path_tmpdirs() -> None:
    while _UV_SAFE_PATH_TMPDIRS:
        shutil.rmtree(_UV_SAFE_PATH_TMPDIRS.pop(), ignore_errors = True)


def _windows_short_path(s: str) -> str | None:
    """The 8.3 alias of ``s``, or None when the volume has none (common off the system drive)."""
    try:
        import ctypes
        from ctypes import wintypes

        get_short = ctypes.windll.kernel32.GetShortPathNameW
        get_short.argtypes = [wintypes.LPCWSTR, wintypes.LPWSTR, wintypes.DWORD]
        get_short.restype = wintypes.DWORD
        buf = ctypes.create_unicode_buffer(32768)
        rc = get_short(s, buf, 32768)
        # A whitespace-free alias can still fail to resolve (#11290).
        if 0 < rc < 32768 and not _has_whitespace(buf.value) and os.path.exists(buf.value):
            return buf.value
    except Exception:
        pass
    return None


def uv_safe_path(path: object) -> str:
    s = str(path)
    if not _has_whitespace(s):
        return s
    if IS_WINDOWS:
        short = _windows_short_path(s)
        if short is not None and not _has_whitespace(short):
            return short
        # No 8.3 name (often off on non-system volumes): copy, as install.ps1's Get-UvSafeRequirementsPath does.
    tmp_dir = None
    try:
        if not os.path.isfile(s):
            return s
        tmp_dir = tempfile.mkdtemp(prefix = "unsloth_uv_")
        if _has_whitespace(tmp_dir) and IS_WINDOWS:
            tmp_dir = _windows_short_path(tmp_dir) or tmp_dir
        if _has_whitespace(tmp_dir):
            shutil.rmtree(tmp_dir, ignore_errors = True)
            return s
        source_name = os.path.basename(s) or "uv_args.txt"
        if _has_whitespace(source_name):
            safe_name = "".join("_" if ch.isspace() else ch for ch in source_name) or "uv_args.txt"
            dst = os.path.join(tmp_dir, safe_name)
            shutil.copyfile(s, dst)
        else:
            alias_dir = os.path.join(tmp_dir, "source")
            source_dir = os.path.abspath(os.path.dirname(s) or os.curdir)
            try:
                os.symlink(source_dir, alias_dir, target_is_directory = True)
                dst = os.path.join(alias_dir, source_name)
            except OSError:
                # No symlink permission: copy instead; loses relative -r/-c includes but keeps the file.
                dst = os.path.join(tmp_dir, source_name)
                shutil.copyfile(s, dst)
        _UV_SAFE_PATH_TMPDIRS.append(tmp_dir)
        tmp_dir = None
        return dst
    except Exception:
        if tmp_dir is not None:  # don't leak the temp dir if the copy failed
            shutil.rmtree(tmp_dir, ignore_errors = True)
        return s
