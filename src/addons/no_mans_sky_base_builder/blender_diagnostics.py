"""Consent-gated diagnostics, sent by an isolated process without Blender APIs."""
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request

ENDPOINT = 'https://furiousfurby.com/support/api/diagnostics/blender'


def prepare(payload):
    try:
        from .furby_errors import redact
    except ImportError:
        from furby_errors import redact
    result = {key: redact(payload.get(key, ''))[:size] for key, size in (
        ('app', 20), ('version', 80), ('title', 160), ('description', 10000),
        ('environment', 500), ('createdUtc', 40))}
    result['description'] = result['description'].encode('utf-8')[:24000].decode('utf-8', errors='ignore')
    report_id = payload.get('report_id', '')
    if result['app'] not in ('bbe', 'nmscribe') or not re.fullmatch('[a-f0-9]{32}', report_id):
        raise ValueError('This diagnostic report has an invalid identifier.')
    if any(not result[key].strip() for key in result):
        raise ValueError('This diagnostic report is incomplete.')
    result.update(schema=1, consent=True, report_id=report_id)
    return result


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ValueError('The diagnostic endpoint redirected. Report kept locally.')


def send(payload):
    """Only called in the worker after the main process receives consent."""
    data = json.dumps(prepare(payload), ensure_ascii=False).encode('utf-8')
    if len(data) > 32000:
        raise ValueError('Diagnostic report is too large. Report kept locally.')
    request = urllib.request.Request(ENDPOINT, data=data, headers={
        'Content-Type': 'application/json', 'Accept': 'application/json',
        'User-Agent': 'FuriousFurby-Blender-Diagnostics/1'}, method='POST')
    with urllib.request.build_opener(NoRedirect()).open(request, timeout=15) as response:
        raw = response.read(4097)
        if response.status not in (200, 201) or len(raw) > 4096:
            raise ValueError('Unexpected diagnostic response. Report kept locally.')
        result = json.loads(raw)
        if result.get('ok') is not True or result.get('diagnosticsOnly') is not True or not re.fullmatch('[a-f0-9]{24}', result.get('id', '')):
            raise ValueError('No valid diagnostic receipt. Report kept locally.')
        return result['id']


class DiagnosticClient:
    def __init__(self):
        self.worker = None
        self.job = None
        self.message = ''
        self.started = 0
        self.sent = set()
        self.report_id = None

    @property
    def busy(self):
        return self.worker is not None

    def start(self, payload, *, consent=False, online=False):
        if not consent:
            raise ValueError('Sending requires your approval.')
        if not online:
            raise ValueError('Online Access is off. Report kept locally; enable it in Blender Preferences to send.')
        if self.busy:
            raise ValueError('A diagnostic report is already being sent.')
        request = prepare(payload)
        if request['report_id'] in self.sent:
            self.message = 'This diagnostic report was already sent.'
            return
        python = sys.executable
        if not Path(python).stem.lower().startswith('python'):
            python = next((str(p) for p in (Path(sys.prefix)/'bin/python.exe', Path(sys.prefix)/'bin/python3') if p.is_file()), None)
        if not python:
            raise ValueError('The bundled Python runtime was not found.')
        self.job = Path(tempfile.mkdtemp(prefix='furby-diagnostic-'))
        try:
            (self.job/'request.json').write_text(json.dumps(request), encoding='utf-8')
            self.worker = subprocess.Popen([python, str(Path(__file__).resolve()), '--worker', str(self.job)],
                stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
            self.report_id = request['report_id']
            self.started = time.monotonic()
            self.message = 'Sending diagnostic report…'
        except Exception:
            self.close()
            raise

    def poll(self, *, online=False):
        if not self.busy:
            return
        if not online or time.monotonic()-self.started > 25:
            self.message = 'Sending stopped: offline or timed out. Report kept locally; retry when ready.'
            self.close()
            return
        if self.worker.poll() is None:
            return
        try:
            result = json.loads((self.job/'result.json').read_text(encoding='utf-8'))
            if result.get('id') and re.fullmatch('[a-f0-9]{24}', result['id']):
                self.sent.add(self.report_id)
                self.message = 'Diagnostic sent: '+result['id']+'. No reply is expected.'
            else:
                self.message = result.get('error', 'Sending failed. Report kept locally.')
        except (OSError, ValueError):
            self.message = 'Sending failed. Report kept locally; retry when ready.'
        finally:
            self.close()

    def close(self):
        if self.worker is not None and self.worker.poll() is None:
            self.worker.terminate()
            try:
                self.worker.wait(timeout=.2)
            except subprocess.TimeoutExpired:
                self.worker.kill()
                self.worker.wait(timeout=1)
        self.worker = None
        if self.job is not None:
            shutil.rmtree(self.job, ignore_errors=True)
            self.job = None


def worker(folder):
    folder = Path(folder)
    try:
        request = json.loads((folder/'request.json').read_text(encoding='utf-8'))
        if request.get('consent') is not True:
            raise ValueError('Approval was not provided.')
        result = {'id': send(request)}
    except urllib.error.HTTPError as error:
        result = {'error': f'Diagnostic server returned {error.code}. Report kept locally; retry when ready.'}
    except Exception:
        result = {'error': 'Diagnostic could not be sent. Report kept locally; retry when ready.'}
    temporary = folder/'result.tmp'
    temporary.write_text(json.dumps(result), encoding='utf-8')
    os.replace(temporary, folder/'result.json')


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--worker', required=True)
    worker(parser.parse_args().worker)
