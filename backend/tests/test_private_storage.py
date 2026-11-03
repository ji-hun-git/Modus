"""Real OS permission checks on isolated service-owned files."""
import json
import os
from pathlib import Path
import stat
import subprocess
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]/'scripts'))
from private_storage import secure_runtime_directory


def test_private_directory_preserves_existing_bytes_and_restricts_new_files(tmp_path):
    private = tmp_path/'runtime'
    private.mkdir()
    existing = private/'records.db'
    existing.write_bytes(b'original evidence bytes')
    secure_runtime_directory(private)
    created = private/'records.db-journal'
    created.write_bytes(b'journal')
    assert existing.read_bytes() == b'original evidence bytes'
    if os.name == 'nt':
        # Independently read back native ACLs; do not trust the helper's return.
        command = "$p=$env:MODUS_PERMISSION_TEST_PATH; $sid=[System.Security.Principal.WindowsIdentity]::GetCurrent().User.Value; $valid=@($sid,'S-1-5-18'); $paths=@($p,(Join-Path $p 'records.db'),(Join-Path $p 'records.db-journal')); $ok=$true; foreach($path in $paths){$acl=Get-Acl -LiteralPath $path; foreach($ace in $acl.Access){$id=$ace.IdentityReference.Translate([System.Security.Principal.SecurityIdentifier]).Value; if($id -notin $valid -or $ace.AccessControlType -ne 'Allow'){$ok=$false}}}; @{restricted=$ok;protected=(Get-Acl -LiteralPath $p).AreAccessRulesProtected}|ConvertTo-Json -Compress"
        # Do not inherit PowerShell 7's incompatible module path in Windows
        # PowerShell 5 (also relevant on the Windows CI runner).
        environment = {k: v for k, v in os.environ.items() if k.upper() != 'PSMODULEPATH'}
        process = subprocess.run(['powershell.exe', '-NoProfile', '-NonInteractive', '-Command', command],
            env={**environment, 'MODUS_PERMISSION_TEST_PATH': str(private)}, capture_output=True, text=True)
        assert process.returncode == 0, process.stderr
        assert json.loads(process.stdout) == {'restricted': True, 'protected': True}
    else:
        assert stat.S_IMODE(private.stat().st_mode) == 0o700
        assert stat.S_IMODE(existing.stat().st_mode) == 0o600
    # Subsequent startup also protects journal files created earlier.
    secure_runtime_directory(private)
    assert created.read_bytes() == b'journal'


def test_nested_or_linked_storage_is_rejected_without_rewriting_contents(tmp_path):
    private = tmp_path/'runtime'
    (private/'nested').mkdir(parents=True)
    with pytest.raises(ValueError, match='nested'):
        secure_runtime_directory(private)
    assert (private/'nested').is_dir()


def test_hardlinks_are_not_permission_modified(tmp_path):
    private = tmp_path/'runtime'
    private.mkdir()
    outside = tmp_path/'outside.db'
    outside.write_bytes(b'untouched')
    os.link(outside, private/'records.db')
    with pytest.raises(ValueError, match='links'):
        secure_runtime_directory(private)
    assert outside.read_bytes() == b'untouched'
