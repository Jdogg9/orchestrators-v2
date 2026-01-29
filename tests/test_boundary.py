"""Test boundary verification script."""
import subprocess
import os

def test_boundary_script_exists():
    """Verify boundary verification script exists and is executable."""
    script = os.path.join(os.path.dirname(__file__), '..', 'scripts', 'verify_public_boundary.sh')
    assert os.path.exists(script)
    assert os.access(script, os.X_OK)

def test_boundary_verification_passes():
    """Run boundary verification and ensure it passes."""
    script = os.path.join(os.path.dirname(__file__), '..', 'scripts', 'verify_public_boundary.sh')
    result = subprocess.run([script], capture_output=True, text=True, cwd=os.path.dirname(script) + '/..')
    
    # Should exit with 0 (success)
    assert result.returncode == 0, f"Boundary verification failed:\n{result.stdout}\n{result.stderr}"
    
    # Should contain success message
    assert '✅ PUBLIC BOUNDARY SAFE' in result.stdout, "Expected success message not found"
