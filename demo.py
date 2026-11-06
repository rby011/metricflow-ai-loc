"""Run from the project directory: python demo.py setup | serve | check | export."""
import argparse
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent

def run(*args):
    env = dict(os.environ, DBT_SEND_ANONYMOUS_USAGE_STATS='false', DBT_PROFILES_DIR=str(ROOT))
    subprocess.run(args, cwd=ROOT, env=env, check=True)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('command', choices=['setup', 'serve', 'check', 'export'])
    parser.add_argument('--port', type=int, default=8000)
    args = parser.parse_args()
    os.chdir(ROOT)
    if args.command == 'setup':
        run(sys.executable, 'scripts/generate_data.py')
        dbt = Path(sys.executable).parent / ('dbt.exe' if os.name == 'nt' else 'dbt')
        run(str(dbt), 'build', '--profiles-dir', '.')
    elif args.command == 'serve':
        import uvicorn
        uvicorn.run('app:app', host='127.0.0.1', port=args.port, workers=1)
    elif args.command == 'check':
        run(sys.executable, '-m', 'unittest', 'discover', '-s', 'checks', '-v')
    elif args.command == 'export':
        run(sys.executable, 'scripts/export_preview.py')

if __name__ == '__main__':
    main()
