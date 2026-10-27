"""Opt-in env-file reader and loopback-only Streamlit launcher."""
import argparse
import os
from pathlib import Path
import shlex
import subprocess
import sys

from promptpatch.config import load_settings
from promptpatch.security import reject_credentials

NAMES = frozenset({'GEMINI_API_KEY', 'GEMINI_MODEL', 'PROMPTPATCH_MODE', 'PROMPTPATCH_DB_PATH',
                   'PROMPTPATCH_CHECKPOINT_DB_PATH', 'PROMPTPATCH_DEMO_REPO'})


def launch_environment(path=None, environ=None, *, recorded_demo=False):
    env = dict(os.environ if environ is None else environ)
    if path is not None:
        path = Path(path)
        if path.stat().st_size > 65536:
            raise ValueError('Environment file exceeds its bound.')
        for line in path.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith('#') or '=' not in line:
                continue
            name, value = line.removeprefix('export ').split('=', 1)
            name = name.strip()
            if name not in NAMES:
                continue
            parts = shlex.split(value, comments=True)
            if len(parts) > 1:
                raise ValueError('Invalid environment value.')
            env.setdefault(name, parts[0] if parts else '')
    if recorded_demo:
        root = Path(__file__).resolve().parents[2]
        domain = root/'data/module08/live/memory.sqlite3'
        checkpoints = root/'data/module08/live/checkpoints.sqlite3'
        if not domain.is_file() or not checkpoints.is_file():
            raise ValueError('Recorded demo runtime is unavailable; inspect committed artifacts instead.')
        env.update(PROMPTPATCH_DB_PATH=str(domain), PROMPTPATCH_CHECKPOINT_DB_PATH=str(checkpoints),
                   PROMPTPATCH_DEMO_REPO=str(root/'samples/demo_git_repo'))
    settings = load_settings(env)
    reject_credentials(settings.model_dump(), extra=(settings.gemini_api_key.get_secret_value(),) if settings.gemini_api_key else ())
    if settings.db_path.resolve() == settings.checkpoint_db_path.resolve():
        raise ValueError('Domain and checkpoint files must differ.')
    # Preserve the caller's path meaning even though the child runs at the checkout.
    for name, value in [('PROMPTPATCH_DB_PATH', settings.db_path),
                        ('PROMPTPATCH_CHECKPOINT_DB_PATH', settings.checkpoint_db_path),
                        ('PROMPTPATCH_DEMO_REPO', settings.demo_repo)]:
        env[name] = str(value.resolve())
    return env


def main(argv=None):
    parser = argparse.ArgumentParser(description='Launch PromptPatch on localhost; no model calls on page load.')
    parser.add_argument('--env-file', type=Path, help='Explicitly parse recognized settings; never source shell code.')
    parser.add_argument('--recorded-demo', action='store_true', help='View existing Module 08 runtime without reseeding.')
    parser.add_argument('--port', type=int, default=8501)
    args = parser.parse_args(argv)
    try:
        if not 1 <= args.port <= 65535:
            raise ValueError('Invalid port.')
        import importlib.util
        if importlib.util.find_spec('streamlit') is None:
            print("Install the UI extra: python -m pip install -e '.[ui]'", file=sys.stderr)
            return 1
        env = launch_environment(args.env_file, recorded_demo=args.recorded_demo)
        app = Path(__file__).with_name('ui.py')
        return subprocess.run([sys.executable, '-m', 'streamlit', 'run', str(app),
                               '--server.address', '127.0.0.1', '--server.port', str(args.port),
                               '--server.headless', 'true', '--server.fileWatcherType', 'none',
                               '--browser.gatherUsageStats', 'false'], env=env,
                              cwd=Path(__file__).resolve().parents[2], check=False).returncode
    except (OSError, ValueError):
        print('UI launch failed. Check env-file syntax, local paths, distinct database files and port. Values are not displayed.', file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        return 130


if __name__ == '__main__':
    raise SystemExit(main())
