"""Restrict the checked launcher's dedicated runtime directory to its OS owner.

Not encryption or account isolation. Administrators and the same OS user retain
access. Call only for a service-owned directory, never a project or home folder.
"""
import os
from pathlib import Path
import stat


def _windows_restrict(path, directory):
    import ctypes as c
    from ctypes import wintypes as w

    adv = c.WinDLL('advapi32', use_last_error=True)
    kernel = c.WinDLL('kernel32', use_last_error=True)
    ptr = c.c_void_p
    kernel.GetCurrentProcess.restype = w.HANDLE
    kernel.CloseHandle.argtypes = [w.HANDLE]
    kernel.LocalFree.argtypes = [ptr]
    kernel.LocalFree.restype = ptr
    adv.OpenProcessToken.argtypes = [w.HANDLE, w.DWORD, c.POINTER(w.HANDLE)]
    adv.GetTokenInformation.argtypes = [w.HANDLE, c.c_int, ptr, w.DWORD, c.POINTER(w.DWORD)]
    adv.ConvertSidToStringSidW.argtypes = [ptr, c.POINTER(w.LPWSTR)]
    adv.ConvertStringSecurityDescriptorToSecurityDescriptorW.argtypes = [w.LPCWSTR, w.DWORD, c.POINTER(ptr), c.POINTER(w.DWORD)]
    adv.GetSecurityDescriptorDacl.argtypes = [ptr, c.POINTER(w.BOOL), c.POINTER(ptr), c.POINTER(w.BOOL)]
    adv.SetNamedSecurityInfoW.argtypes = [w.LPWSTR, c.c_int, w.DWORD, ptr, ptr, ptr, ptr]
    adv.SetNamedSecurityInfoW.restype = w.DWORD

    token, sid_text, descriptor = w.HANDLE(), w.LPWSTR(), ptr()
    try:
        if not adv.OpenProcessToken(kernel.GetCurrentProcess(), 8, c.byref(token)):
            raise c.WinError(c.get_last_error())
        required = w.DWORD()
        adv.GetTokenInformation(token, 1, None, 0, c.byref(required))
        if not required.value:
            raise c.WinError(c.get_last_error())
        buffer = c.create_string_buffer(required.value)
        if not adv.GetTokenInformation(token, 1, buffer, required, c.byref(required)):
            raise c.WinError(c.get_last_error())
        # TOKEN_USER begins with SID_AND_ATTRIBUTES; its first member is PSID.
        sid = c.cast(buffer, c.POINTER(ptr))[0]
        if not adv.ConvertSidToStringSidW(sid, c.byref(sid_text)):
            raise c.WinError(c.get_last_error())
        inherit = 'OICI' if directory else ''
        sddl = f'D:P(A;{inherit};FA;;;SY)(A;{inherit};FA;;;{sid_text.value})'
        if not adv.ConvertStringSecurityDescriptorToSecurityDescriptorW(sddl, 1, c.byref(descriptor), None):
            raise c.WinError(c.get_last_error())
        present, defaulted, dacl = w.BOOL(), w.BOOL(), ptr()
        if not adv.GetSecurityDescriptorDacl(descriptor, c.byref(present), c.byref(dacl), c.byref(defaulted)) or not present or not dacl:
            raise OSError('Unable to construct private record permissions')
        # SE_FILE_OBJECT, DACL_SECURITY_INFORMATION | PROTECTED_DACL_SECURITY_INFORMATION.
        status = adv.SetNamedSecurityInfoW(str(path), 1, 0x80000004, None, None, dacl, None)
        if status:
            raise c.WinError(status)
    finally:
        if descriptor: kernel.LocalFree(descriptor)
        if sid_text: kernel.LocalFree(c.cast(sid_text, ptr))
        if token: kernel.CloseHandle(token)


def _ordinary(path, *, directory=False):
    info = path.lstat()
    if (stat.S_ISLNK(info.st_mode) or getattr(info, 'st_file_attributes', 0) & 0x400
            or (not directory and (not stat.S_ISREG(info.st_mode) or info.st_nlink != 1))
            or (directory and not stat.S_ISDIR(info.st_mode))):
        raise ValueError('Private storage cannot contain links or nested directories')


def secure_runtime_directory(directory):
    """Fail closed before opening SQLite; do not alter or delete file contents."""
    directory = Path(directory).absolute()
    directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    _ordinary(directory, directory=True)
    files = list(directory.iterdir())
    # Validate every child before changing permissions. This is deliberately
    # non-recursive: only the launcher's private flat runtime directory belongs here.
    for path in files:
        _ordinary(path)
    if os.name == 'nt':
        _windows_restrict(directory, True)
        for path in files:
            _windows_restrict(path, False)
    else:
        directory.chmod(0o700)
        for path in files:
            path.chmod(0o600)
    return directory


def secure_file(path):
    """Restrict one existing application-owned regular file, never its parent."""
    path = Path(path).absolute()
    _ordinary(path)
    if os.name == 'nt':
        _windows_restrict(path, False)
    else:
        path.chmod(0o600)
    return path
