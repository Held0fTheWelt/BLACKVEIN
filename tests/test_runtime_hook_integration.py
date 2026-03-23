"""Integration tests for /runtime hook handler."""
import subprocess
import json
import sys
from pathlib import Path

def run_runtime_command(action, *args):
    """Execute runtime.py via subprocess and parse JSON output."""
    cmd = [sys.executable, str(Path('runtime.py')), action] + list(args)
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=Path(__file__).parent.parent)
    if result.returncode != 0:
        raise RuntimeError(f"Command failed: {result.stderr}")
    return json.loads(result.stdout)


class TestRuntimeHookIntegration:
    """Test /runtime hook handler integration."""

    def test_hook_get_mode(self):
        """Test /runtime get via hook (calls runtime.py)."""
        result = run_runtime_command('get')
        assert result['status'] == 'ok'
        assert result['mode'] in ['default', 'adaptive', 'claude-min']
        assert 'message' in result
        assert 'description' in result

    def test_hook_set_mode_default(self):
        """Test /runtime set default."""
        result = run_runtime_command('set', 'default')
        assert result['status'] == 'ok'
        assert result['mode'] == 'default'
        
        # Verify mode persisted
        verify = run_runtime_command('get')
        assert verify['mode'] == 'default'

    def test_hook_set_mode_adaptive(self):
        """Test /runtime set adaptive."""
        result = run_runtime_command('set', 'adaptive')
        assert result['status'] == 'ok'
        assert result['mode'] == 'adaptive'
        
        verify = run_runtime_command('get')
        assert verify['mode'] == 'adaptive'

    def test_hook_set_mode_claude_min(self):
        """Test /runtime set claude-min."""
        result = run_runtime_command('set', 'claude-min')
        assert result['status'] == 'ok'
        assert result['mode'] == 'claude-min'
        
        verify = run_runtime_command('get')
        assert verify['mode'] == 'claude-min'

    def test_hook_list_modes(self):
        """Test /runtime list shows all modes."""
        result = run_runtime_command('list')
        assert result['status'] == 'ok'
        assert 'modes' in result
        assert 'default' in result['modes']
        assert 'adaptive' in result['modes']
        assert 'claude-min' in result['modes']

    def test_hook_menu_interactive(self):
        """Test /runtime menu returns interactive structure."""
        result = run_runtime_command('menu')
        assert result['status'] == 'ok'
        assert result['interactive'] is True
        assert 'modes' in result
        assert len(result['modes']) == 3

    def test_hook_info_detailed(self):
        """Test /runtime info returns detailed mode information."""
        result = run_runtime_command('info')
        assert result['status'] == 'ok'
        assert 'modes' in result
        
        # Each mode should have required fields
        for mode in ['default', 'adaptive', 'claude-min']:
            assert mode in result['modes']
            mode_info = result['modes'][mode]
            assert 'allows_ollama' in mode_info
            assert 'allows_claude' in mode_info
            assert 'description' in mode_info

    def test_hook_invalid_mode_rejected(self):
        """Test /runtime set invalid-mode returns error."""
        result = run_runtime_command('set', 'invalid-mode')
        assert result['status'] == 'error'
        assert 'invalid' in result['message'].lower()

    def test_config_json_has_runtime_command(self):
        """Test config.json has /runtime command registered."""
        config_path = Path(__file__).parent.parent / '.claude' / 'config.json'
        assert config_path.exists(), f"Config file not found: {config_path}"
        
        with open(config_path) as f:
            config = json.load(f)
        
        assert 'commands' in config
        assert 'runtime' in config['commands']
        
        runtime_cmd = config['commands']['runtime']
        assert runtime_cmd['handler'] == '.claude/hooks/input-command.js'
        assert set(runtime_cmd['actions']) == {'menu', 'list', 'get', 'set', 'info'}

    def test_hook_handler_exists(self):
        """Test hook handler file exists."""
        hook_path = Path(__file__).parent.parent / '.claude' / 'hooks' / 'input-command.js'
        assert hook_path.exists(), f"Hook handler not found: {hook_path}"

    def test_mode_switch_persists_across_calls(self):
        """Test that mode switch persists across multiple get calls."""
        # Set to adaptive
        result1 = run_runtime_command('set', 'adaptive')
        assert result1['mode'] == 'adaptive'
        
        # Get multiple times - should stay adaptive
        result2 = run_runtime_command('get')
        assert result2['mode'] == 'adaptive'
        
        result3 = run_runtime_command('get')
        assert result3['mode'] == 'adaptive'

    def test_all_json_responses_have_status(self):
        """Test all responses have status field."""
        for action in ['get', 'list', 'menu', 'info']:
            result = run_runtime_command(action)
            assert 'status' in result
            assert result['status'] in ['ok', 'error']
