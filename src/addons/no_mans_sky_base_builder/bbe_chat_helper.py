"""Short-lived network worker for BBE chat. Runs outside Blender's process."""

import base64
import json
import hashlib
import http.client
import secrets
import time
import os
from pathlib import Path
import sys
import urllib.error
import urllib.request


API = 'https://furiousfurby.com/bbe-chat/api/'
MAX_BYTES = 20 * 1024 * 1024
MAX_FILE_BYTES = 2 * 1024 * 1024 * 1024
CHUNK_BYTES = 4 * 1024 * 1024
LARGE_SUFFIXES = {".blend", ".zip", ".pdf"}
MEDIA_SUFFIXES = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".mp4", ".webm"}
MIMES = {'.png', '.jpg', '.jpeg', '.gif', '.webp', '.mp4', '.webm', '.blend', '.zip', '.pdf', '.json', '.nmsbase', '.nmsship', '.txt', '.log'}


class ChatError(RuntimeError):
    def __init__(self, message, retryable=False):
        super().__init__(message)
        self.retryable = retryable


def file_limit(path):
    return MAX_FILE_BYTES if Path(path).suffix.lower() in LARGE_SUFFIXES else MAX_BYTES


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise RuntimeError('Chat server redirected the request')


OPENER = urllib.request.build_opener(NoRedirect)


def request(action, data=None, *, raw=None, headers=None, binary=False, timeout=5):
    url = API + action
    if not url.startswith('https://furiousfurby.com/bbe-chat/api/'):
        raise RuntimeError('Invalid chat server')
    if raw is None:
        payload = json.dumps(data or {}).encode('utf-8') if data is not None else None
        headers = {'Content-Type': 'application/json', **(headers or {})}
    else:
        payload = raw
    query = urllib.request.Request(url, data=payload, headers={'User-Agent': 'BBE-Chat/18.2.2 (+https://furiousfurby.com)', **(headers or {})},
                                   method='POST' if payload is not None else 'GET')
    try:
        with OPENER.open(query, timeout=timeout) as response:
            received = response.read(MAX_BYTES + 1)
            if len(received) > MAX_BYTES:
                raise RuntimeError('Chat response is too large')
            return received if binary else json.loads(received.decode('utf-8'))
    except urllib.error.HTTPError as error:
        try:
            body = error.read(2048).decode('utf-8')
            problem = json.loads(body).get('error', '')
        except (ValueError, UnicodeError):
            problem = 'Chat was blocked by the website security filter' if error.code == 403 else ''
        raise ChatError(problem or f'Chat request failed ({error.code})', error.code in (408, 429, 500, 502, 503, 504)) from None
    except urllib.error.URLError:
        raise ChatError('Cannot reach the chat server', True) from None


def _check_cancel(cancel):
    if cancel and cancel.is_set():
        raise RuntimeError('Transfer cancelled')


def _retry(function, cancel=None):
    for attempt in range(3):
        _check_cancel(cancel)
        try:
            return function()
        except (ChatError, TimeoutError, ConnectionError, http.client.IncompleteRead) as error:
            if isinstance(error, ChatError) and not error.retryable:
                raise
            if attempt == 2:
                raise
            if cancel:
                cancel.wait(attempt + 1)
            else:
                time.sleep(attempt + 1)


def upload_file(file, detail):
    cancel, progress = detail.get('_cancel'), detail.get('_progress', lambda done, total: None)
    original = file.stat()
    size = original.st_size
    headers = {'Authorization': 'Bearer ' + detail['secret'], 'X-BBE-As': detail.get('as') or ''}
    upload_id = secrets.token_hex(16)
    committed = False
    try:
        started = _retry(lambda: request('file-start', {'secret': detail['secret'], 'as': detail.get('as'),
                            'to': detail.get('to') or None, 'name': file.name, 'size': size,
                            'text': detail.get('text', ''), 'uploadId': upload_id}), cancel)
        if started.get('id') != upload_id or started.get('chunkBytes') != CHUNK_BYTES:
            raise RuntimeError('Unexpected upload response')
        headers['X-BBE-Upload'] = upload_id
        whole = hashlib.sha256()
        offset = 0
        progress(0, size)
        with file.open('rb') as stream:
            while offset < size:
                _check_cancel(cancel)
                chunk = stream.read(min(CHUNK_BYTES, size - offset))
                if not chunk:
                    raise RuntimeError('The file changed while uploading. Save it, then try again.')
                digest = hashlib.sha256(chunk).hexdigest()
                result = _retry(lambda: request('file-chunk', raw=chunk, headers={**headers,
                    'X-BBE-Offset': str(offset), 'X-BBE-SHA256': digest,
                    'Content-Type': 'application/octet-stream'}, timeout=60), cancel)
                if result.get('offset') != offset + len(chunk):
                    raise RuntimeError('Unexpected upload position')
                whole.update(chunk)
                offset += len(chunk)
                progress(offset, size)
            if stream.read(1):
                raise RuntimeError('The file grew while uploading. Save it, then try again.')
        if file.stat().st_mtime_ns != original.st_mtime_ns:
            raise RuntimeError('The file changed while uploading. Save it, then try again.')
        _check_cancel(cancel)
        result = _retry(lambda: request('file-finish', raw=b'', headers={**headers,
                         'X-BBE-SHA256': whole.hexdigest()}, timeout=30), cancel)
        if not result.get('message'):
            raise RuntimeError('Server did not confirm the transfer')
        committed = True
        return result
    finally:
        if not committed:
            try:
                request('file-cancel', raw=b'', headers={**headers, 'X-BBE-Upload': upload_id})
            except Exception:
                pass  # Server also expires abandoned reservations and partial files.


def download_file(detail):
    cancel, progress = detail.get('_cancel'), detail.get('_progress', lambda done, total: None)
    destination = Path(detail['path'])
    size = detail.get('size')
    if not isinstance(size, int) or not 0 < size <= MAX_FILE_BYTES:
        # Older callers use this only for small image previews.
        content = request('media/' + detail['id'], headers={'Authorization': 'Bearer ' + detail['secret'],
                          'X-BBE-As': detail.get('as') or ''}, binary=True, timeout=60)
        _check_cancel(cancel)
        with destination.open('xb') as stream:
            stream.write(content)
        return str(destination)
    temporary = destination.with_name(destination.name + '.' + secrets.token_hex(8) + '.bbe-part')
    digest = hashlib.sha256()
    offset = 0
    try:
        if destination.exists():
            raise FileExistsError('Choose a new filename; chat will not overwrite a file')
        with temporary.open('xb') as stream:
            progress(0, size)
            while offset < size:
                _check_cancel(cancel)
                end = min(offset + CHUNK_BYTES, size) - 1
                chunk = _retry(lambda: request('media/' + detail['id'], headers={
                    'Authorization': 'Bearer ' + detail['secret'], 'X-BBE-As': detail.get('as') or '',
                    'Range': f'bytes={offset}-{end}'}, binary=True, timeout=60), cancel)
                if len(chunk) != end - offset + 1:
                    raise RuntimeError('Download was incomplete; please try again')
                stream.write(chunk); digest.update(chunk); offset += len(chunk)
                progress(offset, size)
        if detail.get('sha256') and digest.hexdigest() != detail['sha256']:
            raise RuntimeError('Download checksum mismatch; please try again')
        _check_cancel(cancel)
        # Hard-link promotion is atomic and refuses to overwrite an existing destination.
        if os.name == 'nt':
            os.rename(temporary, destination)  # Windows rename refuses an existing destination.
        else:
            os.link(temporary, destination)
        return str(destination)
    finally:
        temporary.unlink(missing_ok=True)


def sync_chat(detail):
    data = {'secret': detail.get('secret'), 'as': detail.get('as'), 'to': detail.get('to') or None}
    value = request('sync', data)
    full = {m['id']: m for m in value.get('messages', [])}
    known = set(detail.get('known_content', []))
    # The server's inbox is intentionally sparse. Fetch at most one additional
    # conversation, only when it has new content, never one request per message.
    missing = [m for m in value.get('inbox', []) if m['id'] not in full and m['id'] not in known]
    if missing:
        latest = missing[-1]
        room = latest['from'] if latest.get('to') else None
        if room != data['to']:
            try:
                extra = request('sync', {**data, 'to': room})
                full.update((m['id'], m) for m in extra.get('messages', []))
            except (RuntimeError, OSError):
                pass  # Keep presence/history working; retry content next poll.
    value['inbox'] = [{**m, **full.get(m['id'], {})} for m in value.get('inbox', [])]
    return value


def run(action, detail):
    secret = detail.get('secret')
    if action == 'claim':
        return request('claim', {'name': detail['name'], 'secret': secret})
    if action == 'sync':
        return sync_chat(detail)
    if action == 'send':
        if detail['file']:
            file = Path(detail['file'])
            if not 0 < file.stat().st_size <= file_limit(file):
                raise RuntimeError('Use BLEND, ZIP or PDF up to 2 GB; other supported files up to 20 MB')
            if file.suffix.lower() not in MIMES:
                raise RuntimeError('Choose an image, video, BLEND, ZIP, PDF, JSON, NMSBASE, NMSSHIP, TXT or LOG')
            if file.suffix.lower() not in MEDIA_SUFFIXES and detail.get('_chunkedFiles', True):
                return upload_file(file, detail)
            if file.stat().st_size > MAX_BYTES:
                raise RuntimeError('Large files require the updated chat server')
            _check_cancel(detail.get('_cancel'))
            return request('upload', raw=file.read_bytes(), headers={
                'Authorization': 'Bearer ' + secret,
                'X-BBE-As': detail.get('as') or '',
                'X-BBE-Recipient': detail['to'] or 'main',
                'X-BBE-File-Name': file.name.encode('ascii', 'replace').decode('ascii'),
                'X-BBE-Text': base64.urlsafe_b64encode(detail['text'].encode('utf-8')).rstrip(b'=').decode('ascii'),
                'Content-Type': 'application/octet-stream',
            }, timeout=40)
        if detail['text']:
            return request('send', {'secret': secret, 'as': detail.get('as'), 'to': detail['to'] or None, 'text': detail['text']})
        raise RuntimeError('Add text or a file before sending')
    if action == 'download':
        return download_file(detail)
    raise RuntimeError('Unknown chat action')


def main():
    destination = Path(sys.argv[1])
    try:
        input_data = json.load(sys.stdin)
        response = {'output': run(input_data['action'], input_data['detail'])}
    except Exception as error:
        response = {'error': str(error)}
    # Destination is in a private per-profile temp folder, chosen by Blender.
    with open(destination, 'x', encoding='utf-8') as stream:
        json.dump(response, stream)
    try:
        os.chmod(destination, 0o600)
    except OSError:
        pass


if __name__ == '__main__':
    main()
