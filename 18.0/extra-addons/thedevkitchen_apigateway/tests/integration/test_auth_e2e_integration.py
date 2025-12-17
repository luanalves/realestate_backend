#!/usr/bin/env python3
"""Automated authentication scenarios executed via HTTP requests.

This suite executes the documented login/logout/me security scenarios against the
running API Gateway instance. It relies on environment variables defined in
18.0/.env and runs with the local Python virtual environment (ADR-002).
"""

import os
import sys
from contextlib import closing
from pathlib import Path
from typing import Dict, Optional, Tuple

import jwt
import psycopg2
from psycopg2.extras import RealDictCursor
import requests


class DatabaseSession:
    """Lightweight helper to query and mutate API session data."""

    def __init__(self) -> None:
        self._conn = self._connect()
        self._conn.autocommit = True

    def _connect(self) -> psycopg2.extensions.connection:
        dbname = os.getenv('DB_NAME') or os.getenv('POSTGRES_DB') or 'realestate'
        user = os.getenv('POSTGRES_USER', 'odoo')
        password = os.getenv('POSTGRES_PASSWORD', 'odoo')
        port = int(os.getenv('DB_PORT') or os.getenv('POSTGRES_PORT') or 5432)
        host_candidates = []
        for candidate in (
            os.getenv('DB_HOST'),
            os.getenv('POSTGRES_HOST'),
            'localhost',
            '127.0.0.1',
        ):
            if candidate and candidate not in host_candidates:
                host_candidates.append(candidate)
        last_error: Optional[Exception] = None
        for host in host_candidates:
            try:
                return psycopg2.connect(
                    dbname=dbname,
                    user=user,
                    password=password,
                    host=host,
                    port=port,
                )
            except psycopg2.OperationalError as exc:  # pragma: no cover - informative only
                last_error = exc
        raise RuntimeError(f'Unable to connect to database: {last_error}')

    def fetch_one(self, query: str, params: Tuple = ()) -> Optional[Dict]:
        with closing(self._conn.cursor(cursor_factory=RealDictCursor)) as cursor:
            cursor.execute(query, params)
            return cursor.fetchone()

    def execute(self, query: str, params: Tuple = ()) -> None:
        with closing(self._conn.cursor()) as cursor:
            cursor.execute(query, params)

    def close(self) -> None:
        if self._conn:
            self._conn.close()


def load_env_file() -> None:
    """Populate os.environ with values from the local .env file."""

    current = Path(__file__).resolve()
    project_root = current.parent.parent.parent.parent.parent
    env_file = project_root / '.env'
    if not env_file.exists():
        print(f'✗ .env not found at {env_file}', file=sys.stderr)
        sys.exit(1)
    with env_file.open('r', encoding='utf-8') as handler:
        for line in handler:
            line = line.strip()
            if not line or line.startswith('#') or '=' not in line:
                continue
            key, value = line.split('=', 1)
            if key and key not in os.environ:
                os.environ[key] = value


def unwrap_payload(data: Dict) -> Dict:
    if isinstance(data, dict) and 'result' in data and isinstance(data['result'], dict):
        return data['result']
    return data


def extract_error(data: Dict) -> Optional[Dict]:
    if not isinstance(data, dict):
        return None
    if 'error' in data and isinstance(data['error'], dict):
        return data['error']
    result = data.get('result') if isinstance(data, dict) else None
    if isinstance(result, dict) and 'error' in result:
        return result['error']
    return None


class AuthScenarioSuite:
    """Runs the documented authentication security scenarios sequentially."""

    def __init__(self) -> None:
        load_env_file()
        self.base_url = os.getenv('API_BASE_URL') or os.getenv('ODOO_BASE_URL') or 'http://localhost:8069'
        self.client_id = os.getenv('OAUTH_CLIENT_ID') or ''
        self.client_secret = os.getenv('OAUTH_CLIENT_SECRET') or ''
        self.user_email = os.getenv('TEST_USER_A_EMAIL') or 'joao@imobiliaria.com'
        self.user_password = os.getenv('TEST_USER_A_PASSWORD') or 'test123'
        self.user_agent = 'QA-Test-Agent/1.0'
        self.accept_language = 'pt-BR,en;q=0.9'
        self.timeout = float(os.getenv('HTTP_TIMEOUT', '30'))
        if not self.client_id or not self.client_secret:
            print('✗ Missing OAuth credentials in environment.', file=sys.stderr)
            sys.exit(1)
        self.user_b_email = os.getenv('TEST_USER_B_EMAIL')
        self.user_b_password = os.getenv('TEST_USER_B_PASSWORD')
        if not self.user_email or not self.user_password or not self.user_b_email or not self.user_b_password:
            print('✗ Missing test user credentials (TEST_USER_A_* and TEST_USER_B_*)', file=sys.stderr)
            sys.exit(1)
        self.db = DatabaseSession()
        user_row = self.db.fetch_one(
            'SELECT id FROM res_users WHERE login = %s LIMIT 1', (self.user_email,)
        )
        if not user_row:
            raise RuntimeError(f'Test user not found: {self.user_email}')
        self.user_id = user_row['id']
        victim_row = self.db.fetch_one(
            'SELECT id FROM res_users WHERE login = %s LIMIT 1', (self.user_b_email,)
        )
        if not victim_row:
            raise RuntimeError(f'Test user not found: {self.user_b_email}')
        self.user_b_id = victim_row['id']
        self.database_secret: Optional[str] = None
        self.results = []

    # ------------------------------------------------------------------
    # HTTP Helpers
    # ------------------------------------------------------------------
    def _post(self, path: str, payload: Dict, headers: Dict) -> Tuple[requests.Response, Dict]:
        response = requests.post(
            f'{self.base_url}{path}',
            json=payload,
            headers=headers,
            timeout=self.timeout,
        )
        try:
            data = response.json()
        except ValueError as exc:
            raise AssertionError(f'Invalid JSON response: {response.text}') from exc
        return response, data

    def obtain_bearer_token(self) -> str:
        headers = {'Content-Type': 'application/json'}
        payload = {
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'grant_type': 'client_credentials',
        }
        response, data = self._post('/api/v1/auth/token', payload, headers)
        assert response.status_code == 200, f'Bearer token request failed: {response.status_code} {data}'
        body = unwrap_payload(data)
        assert 'access_token' in body, f'Bearer token missing in response: {body}'
        return body['access_token']

    def login(
        self,
        token: str,
        user_agent: Optional[str] = None,
        email: Optional[str] = None,
        password: Optional[str] = None,
    ) -> Tuple[requests.Response, Dict, Optional[Dict]]:
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {token}',
            'User-Agent': user_agent or self.user_agent,
            'Accept-Language': self.accept_language,
        }
        payload = {
            'email': email or self.user_email,
            'password': password or self.user_password,
        }
        response, data = self._post('/api/v1/users/login', payload, headers)
        return response, unwrap_payload(data), extract_error(data)

    def call_me(
        self,
        token: str,
        session_id: str,
        user_agent: Optional[str] = None,
    ) -> Tuple[requests.Response, Dict, Optional[Dict]]:
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {token}',
            'X-Openerp-Session-Id': session_id,
            'User-Agent': user_agent or self.user_agent,
            'Accept-Language': self.accept_language,
        }
        response, data = self._post('/api/v1/me', {}, headers)
        return response, unwrap_payload(data), extract_error(data)

    def logout(self, token: str, session_id: Optional[str]) -> Tuple[requests.Response, Dict, Optional[Dict]]:
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {token}',
            'User-Agent': self.user_agent,
            'Accept-Language': self.accept_language,
        }
        payload: Dict[str, str] = {}
        if session_id:
            payload['session_id'] = session_id
        response, data = self._post('/api/v1/users/logout', payload, headers)
        return response, unwrap_payload(data), extract_error(data)

    # ------------------------------------------------------------------
    # Database helpers
    # ------------------------------------------------------------------
    def get_session_row(self, session_id: str) -> Optional[Dict]:
        return self.db.fetch_one(
            'SELECT id, user_id, is_active, security_token FROM thedevkitchen_api_session WHERE session_id = %s ORDER BY id DESC LIMIT 1',
            (session_id,),
        )

    def clear_security_token(self, session_id: str) -> None:
        self.db.execute(
            'UPDATE thedevkitchen_api_session SET security_token = NULL WHERE session_id = %s',
            (session_id,),
        )

    def update_security_token(self, session_id: str, token: str) -> None:
        self.db.execute(
            'UPDATE thedevkitchen_api_session SET security_token = %s WHERE session_id = %s',
            (token, session_id),
        )

    def deactivate_active_sessions(self) -> None:
        for uid in (self.user_id, self.user_b_id):
            self.db.execute(
                'UPDATE thedevkitchen_api_session SET is_active = FALSE, logout_at = NOW() WHERE user_id = %s AND is_active = TRUE',
                (uid,),
            )

    def get_database_secret(self) -> str:
        if self.database_secret:
            return self.database_secret
        row = self.db.fetch_one(
            "SELECT value FROM ir_config_parameter WHERE key = 'database.secret' LIMIT 1"
        )
        if not row or not row.get('value'):
            raise RuntimeError('database.secret not configured')
        self.database_secret = row['value']
        return self.database_secret

    # ------------------------------------------------------------------
    # Scenarios
    # ------------------------------------------------------------------
    def scenario_login_requires_bearer(self) -> None:
        payload = {'email': self.user_email, 'password': self.user_password}
        headers = {
            'Content-Type': 'application/json',
            'User-Agent': self.user_agent,
            'Accept-Language': self.accept_language,
        }
        response, data = self._post('/api/v1/users/login', payload, headers)
        error = extract_error(data)
        assert response.status_code == 401, f'Expected 401, got {response.status_code}: {data}'
        assert error and error.get('code') == 'unauthorized', f'Unexpected error payload: {error}'

    def scenario_login_success_and_me(self) -> None:
        token = self.obtain_bearer_token()
        response, body, error = self.login(token)
        assert response.status_code == 200, f'Login failed: {response.status_code} {body or error}'
        session_id = body.get('session_id')
        assert session_id, f'Missing session_id in login response: {body}'
        me_response, me_body, me_error = self.call_me(token, session_id)
        assert me_response.status_code == 200, f'/me failed: {me_response.status_code} {me_body or me_error}'
        assert 'user' in me_body, f'Missing user payload: {me_body}'
        assert me_body['user'].get('email') == self.user_email, f'Unexpected user email: {me_body}'
        session_row = self.get_session_row(session_id)
        assert session_row and session_row.get('security_token'), 'Session record missing security_token'

    def scenario_login_rotates_session(self) -> None:
        token = self.obtain_bearer_token()
        first_response, first_body, _ = self.login(token, user_agent='QA-Agent/1.0')
        assert first_response.status_code == 200, f'First login failed: {first_response.status_code}'
        first_session = first_body.get('session_id')
        assert first_session, f'First session missing: {first_body}'
        second_response, second_body, _ = self.login(token, user_agent='QA-Agent/2.0')
        assert second_response.status_code == 200, f'Second login failed: {second_response.status_code}'
        second_session = second_body.get('session_id')
        assert second_session and second_session != first_session, 'Login did not rotate session'
        legacy_me, _, legacy_error = self.call_me(token, first_session, user_agent='QA-Agent/1.0')
        legacy_status = legacy_error.get('status') if legacy_error else legacy_me.status_code
        assert legacy_status == 401, f'Legacy session should be invalid: status={legacy_me.status_code}, error={legacy_error}'
        new_me, new_body, new_error = self.call_me(token, second_session, user_agent='QA-Agent/2.0')
        assert new_me.status_code == 200, f'Current session rejected: {new_me.status_code} {new_error}'
        assert new_body.get('user', {}).get('email') == self.user_email, f'Unexpected /me response: {new_body}'

    def scenario_logout_revokes_session(self) -> None:
        token = self.obtain_bearer_token()
        login_response, login_body, _ = self.login(token)
        assert login_response.status_code == 200, f'Login failed: {login_response.status_code}'
        session_id = login_body.get('session_id')
        assert session_id, 'Login response missing session_id'
        me_response, _, me_error = self.call_me(token, session_id)
        assert me_response.status_code == 200, f'/me before logout failed: {me_response.status_code} {me_error}'
        logout_response, logout_body, logout_error = self.logout(token, session_id)
        assert logout_response.status_code == 200, f'Logout failed: {logout_response.status_code} {logout_body or logout_error}'
        post_me, _, post_error = self.call_me(token, session_id)
        post_status = post_error.get('status') if post_error else post_me.status_code
        assert post_status == 401, f'/me should fail after logout: status={post_me.status_code}, error={post_error}'

    def scenario_logout_requires_session_id(self) -> None:
        token = self.obtain_bearer_token()
        response, body, error = self.logout(token, session_id=None)
        status = error.get('status') if error else response.status_code
        assert status == 400, f'Logout without session_id should fail: status={response.status_code}, body={body}, error={error}'

    def scenario_me_requires_security_token(self) -> None:
        token = self.obtain_bearer_token()
        response, body, _ = self.login(token)
        assert response.status_code == 200, f'Login failed: {response.status_code}'
        session_id = body.get('session_id')
        assert session_id, 'Login missing session_id'
        self.clear_security_token(session_id)
        me_response, _, me_error = self.call_me(token, session_id)
        message = (me_error or {}).get('message') if me_error else ''
        status = (me_error or {}).get('status') if me_error else me_response.status_code
        assert status == 401 and 'Session token' in message, f'/me should reject missing token: status={status}, message={message}'

    def scenario_me_detects_fingerprint_mismatch(self) -> None:
        token = self.obtain_bearer_token()
        response, body, _ = self.login(token)
        assert response.status_code == 200, f'Login failed: {response.status_code}'
        session_id = body.get('session_id')
        assert session_id, 'Login missing session_id'
        session_row = self.get_session_row(session_id)
        assert session_row and session_row.get('security_token'), 'Session missing original security token'
        original_token = session_row['security_token']
        secret = self.get_database_secret()
        try:
            payload = jwt.decode(original_token, secret, algorithms=['HS256'])
        except jwt.InvalidSignatureError:
            payload = jwt.decode(
                original_token,
                options={'verify_signature': False},
                algorithms=['HS256'],
            )
        fingerprint = payload.get('fingerprint', {})
        fingerprint['ua'] = 'Tampered-Agent/9.9'
        payload['fingerprint'] = fingerprint
        forged = jwt.encode(payload, secret, algorithm='HS256')
        if isinstance(forged, bytes):
            forged = forged.decode('utf-8')
        self.update_security_token(session_id, forged)
        try:
            me_response, _, me_error = self.call_me(token, session_id, user_agent='Tampered-Agent/9.9')
            status = (me_error or {}).get('status') if me_error else me_response.status_code
            message = (me_error or {}).get('message') if me_error else ''
            assert status == 401 and ('Invalid session token' in message or 'Session validation failed' in message), (
                f'Fingerprint tampering not detected: status={status}, message={message}'
            )
        finally:
            self.update_security_token(session_id, original_token)

    def scenario_session_hijack_displays_stolen_identity(self) -> None:
        token = self.obtain_bearer_token()
        attacker_response, attacker_body, _ = self.login(
            token,
            user_agent='Hijacker-Agent/1.0',
            email=self.user_email,
            password=self.user_password,
        )
        assert attacker_response.status_code == 200, f'Attacker login failed: {attacker_response.status_code}'
        attacker_session = attacker_body.get('session_id')
        assert attacker_session

        victim_response, victim_body, _ = self.login(
            token,
            user_agent='Victim-Agent/2.0',
            email=self.user_b_email,
            password=self.user_b_password,
        )
        assert victim_response.status_code == 200, f'Victim login failed: {victim_response.status_code}'
        victim_session = victim_body.get('session_id')
        assert victim_session

        hijack_response, hijack_body, hijack_error = self.call_me(
            token,
            victim_session,
            user_agent='Victim-Agent/2.0',
        )
        assert hijack_response.status_code == 200, f'Hijack /me failed: {hijack_response.status_code} {hijack_error}'
        assert hijack_body.get('user', {}).get('email') == self.user_b_email, (
            f'Stolen session should resolve to victim: {hijack_body}'
        )

        attacker_me, attacker_body, attacker_error = self.call_me(
            token,
            attacker_session,
            user_agent='Hijacker-Agent/1.0',
        )
        assert attacker_me.status_code == 200, f'Attacker own /me failed: {attacker_me.status_code} {attacker_error}'
        assert attacker_body.get('user', {}).get('email') == self.user_email

    # ------------------------------------------------------------------
    # Runner
    # ------------------------------------------------------------------
    def run_scenario(self, name: str, func) -> None:
        print('\n' + '=' * 80)
        print(f'SCENARIO: {name}')
        print('=' * 80)
        try:
            self.deactivate_active_sessions()
            func()
        except AssertionError as exc:
            print(f'✗ FAIL: {exc}')
            self.results.append((name, False, str(exc)))
        except Exception as exc:  # pragma: no cover - unexpected errors
            print(f'✗ ERROR: {exc}')
            self.results.append((name, False, str(exc)))
        else:
            print('✓ PASS')
            self.results.append((name, True, ''))
        finally:
            self.deactivate_active_sessions()

    def summary(self) -> int:
        print('\n' + '=' * 80)
        print('SUMMARY')
        print('=' * 80)
        total = len(self.results)
        passed = sum(1 for _, ok, _ in self.results if ok)
        failed = total - passed
        for name, ok, detail in self.results:
            status = 'PASS' if ok else 'FAIL'
            print(f'- {status:4} | {name}' + (f' :: {detail}' if detail else ''))
        print('-' * 80)
        print(f'Total: {total}  |  Passed: {passed}  |  Failed: {failed}')
        return 0 if failed == 0 else 1

    def run(self) -> int:
        scenarios = [
            ('Login cria sessão válida e habilita /me', self.scenario_login_success_and_me),
            ('Novo login invalida sessão anterior', self.scenario_login_rotates_session),
            ('Logout revoga sessão ativa', self.scenario_logout_revokes_session),
            ('Logout sem session_id deve falhar', self.scenario_logout_requires_session_id),
            ('/me exige security_token', self.scenario_me_requires_security_token),
            ('/me detecta fingerprint alterada', self.scenario_me_detects_fingerprint_mismatch),
            ('/me com sessão roubada exibe dono real', self.scenario_session_hijack_displays_stolen_identity),
        ]
        for name, func in scenarios:
            self.run_scenario(name, func)
        self.db.close()
        return self.summary()


def main() -> int:
    try:
        suite = AuthScenarioSuite()
        return suite.run()
    except Exception as exc:  # pragma: no cover - bootstrap errors
        print(f'✗ Fatal error: {exc}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
