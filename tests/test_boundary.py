"""Test boundary verification script."""
import os
import subprocess
from pathlib import Path


def _clear_runtime_state(public_root: Path) -> None:
    instance_dir = public_root / "instance"
    if not instance_dir.exists():
        return
    for entry in instance_dir.iterdir():
        if entry.is_file():
            entry.unlink()

def test_boundary_script_exists():
    """Verify boundary verification script exists and is executable."""
    script = os.path.join(os.path.dirname(__file__), '..', 'scripts', 'verify_public_boundary.sh')
    assert os.path.exists(script)
    assert os.access(script, os.X_OK)

def test_boundary_verification_passes():
    """Run boundary verification and ensure it passes."""
    script = os.path.join(os.path.dirname(__file__), '..', 'scripts', 'verify_public_boundary.sh')
    public_root = Path(os.path.dirname(script)).parent
    _clear_runtime_state(public_root)
    result = subprocess.run([script], capture_output=True, text=True, cwd=str(public_root))
    
    # Should exit with 0 (success)
    assert result.returncode == 0, f"Boundary verification failed:\n{result.stdout}\n{result.stderr}"
    
    # Should contain success message
    assert '✅ PUBLIC BOUNDARY SAFE' in result.stdout, "Expected success message not found"
