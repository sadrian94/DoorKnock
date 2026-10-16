import base64
import json
import time

import httpx
import pytest
from fastapi.testclient import TestClient

from app import gmail_sync
from app.database import get_db, init_db
from app.main import app


def part(text, mime='text/plain', **extra):
    return {'mimeType': mime, 'body': {'data': base64.urlsafe_b64encode(text.encode()).decode()}, **extra}


@pytest.fixture
def preview_google(tmp_path, monkeypatch):
    monkeypatch.setenv('DOORKNOCK_DB_PATH', str(tmp_path / 'preview.db'))
    init_db()
    token = tmp_path / 'synthetic-token.json'
    token.write_text(json.dumps({'access_token': 'synthetic', 'expires_at': time.time() + 3600}))
    monkeypatch.setattr(gmail_sync, 'TOKEN_PATH', token)
    with get_db() as conn:
        conn.execute("INSERT INTO gmail_review_items(message_id,thread_id,received_at,event_code,reason_code,candidate_application_ids) VALUES('preview-mail','preview-thread','2026-10-16T12:00:00Z','related','unclear_event','[]')")
        conn.commit()
    original = httpx.AsyncClient
    calls = []

    def install(payload=None, status=200):
        def handler(request):
            calls.append(request)
            return httpx.Response(status, json=payload or {'error': {'message': 'private provider error'}})
        monkeypatch.setattr(gmail_sync.httpx, 'AsyncClient', lambda **kwargs: original(transport=httpx.MockTransport(handler), **kwargs))
    return install, calls


def database_snapshot():
    with get_db() as conn:
        return '\n'.join(conn.iterdump())


def test_preview_reads_selected_message_without_persisting_content(preview_google):
    install, calls = preview_google
    install({'id': 'preview-mail', 'payload': part('A synthetic interview invitation.\nPlease select a time.', headers=[{'name': 'Subject', 'value': 'Synthetic session invitation'}])})
    with TestClient(app) as client:
        before = database_snapshot()
        result = client.get('/api/gmail/reviews/preview-mail/preview')
        assert result.status_code == 200, result.text
        assert result.json() == {'message_id': 'preview-mail', 'subject': 'Synthetic session invitation', 'body': 'A synthetic interview invitation.\nPlease select a time.', 'truncated': False}
        assert database_snapshot() == before
    assert calls[0].method == 'GET'
    assert calls[0].url.path.endswith('/messages/preview-mail')
    assert calls[0].url.params['format'] == 'full'
    assert 'no-store' in result.headers['cache-control']


def test_preview_prefers_plain_text_and_omits_attachments(preview_google):
    install, _ = preview_google
    install({'id': 'preview-mail', 'payload': {'mimeType': 'multipart/mixed', 'parts': [
        {'mimeType': 'multipart/alternative', 'parts': [part('<p>Duplicate HTML</p>', 'text/html'), part('Readable text')]},
        part('Private attachment', filename='notes.txt'),
        part('Another attachment', headers=[{'name': 'Content-Disposition', 'value': 'attachment'}]),
    ]}})
    with TestClient(app) as client:
        result = client.get('/api/gmail/reviews/preview-mail/preview').json()
    assert result['body'] == 'Readable text'


def test_html_preview_is_text_without_remote_resources_or_executable_markup(preview_google):
    install, calls = preview_google
    install({'id': 'preview-mail', 'payload': part('<html><head><style>secret-style</style></head><body><p>Hello &amp; welcome</p><script>secret-script()</script><img src="https://example.test/pixel"><p>Choose a session</p></body></html>', 'text/html')})
    with TestClient(app) as client:
        body = client.get('/api/gmail/reviews/preview-mail/preview').json()['body']
    assert body == 'Hello & welcome\nChoose a session'
    assert len(calls) == 1


def test_preview_honors_declared_text_charset(preview_google):
    install, _ = preview_google
    payload = part('placeholder', headers=[{'name': 'Content-Type', 'value': 'text/plain; charset=iso-8859-1'}])
    payload['body']['data'] = base64.urlsafe_b64encode('Synthetic café invitation'.encode('iso-8859-1')).decode()
    install({'id': 'preview-mail', 'payload': payload})
    with TestClient(app) as client:
        assert client.get('/api/gmail/reviews/preview-mail/preview').json()['body'] == 'Synthetic café invitation'


def test_preview_reports_reconnect_without_changing_review(preview_google):
    install, calls = preview_google
    install()
    gmail_sync.TOKEN_PATH.write_text(json.dumps({'reconnect_required': True}))
    with TestClient(app) as client:
        before = database_snapshot()
        result = client.get('/api/gmail/reviews/preview-mail/preview')
        assert result.status_code == 400
        assert 'reconnect' in result.json()['detail'].lower()
        assert 'no-store' in result.headers['cache-control']
        assert database_snapshot() == before
    assert not calls


def test_preview_is_bounded_and_can_be_read_after_processing(preview_google):
    install, _ = preview_google
    install({'id': 'preview-mail', 'payload': part('x' * 25000)})
    with TestClient(app) as client:
        assert client.post('/api/gmail/reviews/preview-mail/resolve', json={'action': 'dismiss'}).status_code == 200
        result = client.get('/api/gmail/reviews/preview-mail/preview').json()
    assert len(result['body']) == 20000
    assert result['truncated'] is True


def test_unknown_or_filtered_messages_cannot_be_used_to_read_arbitrary_mail(preview_google):
    install, calls = preview_google
    install({'id': 'preview-mail', 'payload': part('Synthetic text')})
    with TestClient(app) as client:
        result = client.get('/api/gmail/reviews/unknown-mail/preview')
        assert result.status_code == 404
        with get_db() as conn:
            conn.execute("UPDATE gmail_review_items SET status='filtered'")
            conn.commit()
        assert client.get('/api/gmail/reviews/preview-mail/preview').status_code == 404
    assert not calls
    assert 'no-store' in result.headers['cache-control']


@pytest.mark.parametrize('provider_status,expected_status', [(404, 404), (503, 502)])
def test_preview_errors_are_safe_and_not_cached(preview_google, provider_status, expected_status):
    install, _ = preview_google
    install(status=provider_status)
    with TestClient(app) as client:
        result = client.get('/api/gmail/reviews/preview-mail/preview')
    assert result.status_code == expected_status
    assert 'private provider error' not in result.text
    assert 'no-store' in result.headers['cache-control']
