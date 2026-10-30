"""Report deployment prerequisites without exposing credentials."""
from pathlib import Path
from playwright.sync_api import sync_playwright
from app import adapters, store
from app.config import google_client_config


def inspect():
    try:
        google_client_config()
        oauth_ready = True
    except (OSError, ValueError, TypeError, KeyError):
        oauth_ready = False
    with sync_playwright() as browser:
        chromium_installed = Path(browser.chromium.executable_path).is_file()
    gmail_count = len(store.accounts())
    enabled = sum(bool(adapters.summary(slug, config)['enabled'])
                  for slug, config in adapters.all_configs().items())
    checks = [
        {'id': 'oauth', 'ready': oauth_ready, 'message': 'Konfigurasi OAuth Google tersedia.' if oauth_ready else 'Konfigurasi OAuth Google belum tersedia atau tidak valid.'},
        {'id': 'gmail', 'ready': gmail_count > 0, 'message': f'{gmail_count} Gmail tersimpan. Akses API diperiksa kembali sebelum registrasi.'},
        {'id': 'browser', 'ready': chromium_installed, 'message': 'Chromium terpasang; kemampuan menjalankan browser belum diuji oleh pemeriksaan ini.' if chromium_installed else 'Chromium belum terpasang pada server.'},
        {'id': 'adapters', 'ready': enabled > 0, 'message': f'{enabled} adapter lolos pemeriksaan konfigurasi. Keberhasilan trial tetap ditentukan platform.'},
    ]
    return {'ready': all(check['ready'] for check in checks), 'checks': checks}
