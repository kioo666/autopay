"""Start a local personal workspace, reusing existing encrypted storage."""
import os
from pathlib import Path
import runpy
import threading
import webbrowser


def main():
    os.chdir(Path(__file__).resolve().parent)
    if not Path('.env').exists():
        runpy.run_path('setup_local.py', run_name='__main__')
    from dotenv import load_dotenv
    load_dotenv()
    if os.getenv('PUBLIC_BASE_URL') or os.getenv('RENDER_EXTERNAL_URL'):
        raise SystemExit('Hosted configuration detected. Use start_hosted.py.')
    from cryptography.fernet import Fernet
    Fernet(os.environ['MASTER_KEY'].encode())
    # Fragment stays in the browser; dashboard removes it after cookie exchange.
    url = 'http://127.0.0.1:8000/#access=' + os.environ['APP_TOKEN']
    threading.Timer(1.5, lambda: webbrowser.open(url)).start()
    print('TrialFlow: http://127.0.0.1:8000 — Ctrl+C untuk berhenti.')
    import uvicorn
    uvicorn.run('app.main:app', host='127.0.0.1', port=8000, access_log=False)


if __name__ == '__main__':
    main()
