#!/usr/bin/env python3
"""Fluxo oficial de dispositivo GitHub para a branch de exportação limpa.

Diferenças vs github_device_once.py: (1) não depende do binário gh (ausente após
restauração, E007); (2) empurra a branch `export-clean` (árvore sanitizada sem
gemma/official), nunca main; (3) token usado apenas em memória na URL do push,
nunca exibido nem gravado fora de .cache (excluído de snapshots).
Uma única troca após confirmação do usuário; sem polling; sem force-push.
"""
import datetime, json, os, pathlib, subprocess, sys
import requests
from safety_guards import GITHUB_CLI_CLIENT_ID, validate_oauth

ROOT = pathlib.Path('/home/user')
CACHE = ROOT / '.device-tmp'  # .cache não sobrevive entre turnos; removido após o push
CACHE.mkdir(parents=True, exist_ok=True, mode=0o700)
CLIENT = GITHUB_CLI_CLIENT_ID
validate_oauth(CLIENT)
BRANCH = 'export-clean'
REPO_URL = 'https://github.com/vitor120956-max/casmi26-casmi.git'
HEADERS = {'Accept': 'application/json', 'User-Agent': 'GitHub-CLI-device-flow'}


def private(name, data):
    p = CACHE / name
    p.write_text(json.dumps(data))
    p.chmod(0o600)


if sys.argv[1] == 'begin':
    r = requests.post('https://github.com/login/device/code', headers=HEADERS,
                      data={'client_id': CLIENT, 'scope': 'public_repo'}, timeout=30)
    r.raise_for_status()
    d = r.json()
    assert 'device_code' in d, d.get('error', 'No device code')
    private('device.json', d)
    print('URL:', d['verification_uri'])
    print('CÓDIGO:', d['user_code'])
    print('Validade (segundos):', d['expires_in'])
elif sys.argv[1] == 'complete':
    d = json.loads((CACHE / 'device.json').read_text())
    r = requests.post('https://github.com/login/oauth/access_token', headers=HEADERS,
                      data={'client_id': CLIENT, 'device_code': d['device_code'],
                            'grant_type': 'urn:ietf:params:oauth:grant-type:device_code'}, timeout=30)
    r.raise_for_status()
    auth = r.json()
    if not auth.get('access_token'):
        print('Autorização não concluída:', auth.get('error'), auth.get('error_description'))
        sys.exit(1)
    scopes = {s.strip() for s in auth.get('scope', '').replace(' ', ',').split(',') if s.strip()}
    validate_oauth(CLIENT, scopes)
    private('session.json', auth)
    print('Escopos confirmados:', ', '.join(sorted(scopes)), flush=True)
    headers = {'Authorization': 'Bearer ' + auth['access_token'], 'Accept': 'application/vnd.github+json'}
    user = requests.get('https://api.github.com/user', headers=headers, timeout=30)
    user.raise_for_status()
    print('GitHub autorizado:', user.json()['login'], flush=True)
    repo = requests.get('https://api.github.com/repos/vitor120956-max/casmi26-casmi', headers=headers, timeout=30)
    repo.raise_for_status()
    assert repo.json().get('permissions', {}).get('push'), 'Conta sem permissão push neste projeto'
    # O .git não sobrevive entre chamadas (E038): reconstruir e commitar no mesmo processo do push.
    subprocess.run(['bash', str(ROOT / 'rebuild_export.sh'),
                    'Clean export: reconciled state of both sessions (Wave9 5/5 submitted, refs 56659089-96)'],
                   check=True, timeout=300)
    # Push da branch limpa; token só nesta chamada, em memória.
    push_url = 'https://x-access-token:' + auth['access_token'] + '@github.com/vitor120956-max/casmi26-casmi.git'
    env = dict(os.environ, GIT_TERMINAL_PROMPT='0')
    subprocess.run(['git', '-C', str(ROOT / 'recovered'), 'push', push_url,
                    BRANCH + ':' + BRANCH], env=env, check=True, timeout=180)
    local = subprocess.check_output(['git', '-C', str(ROOT / 'recovered'), 'rev-parse', BRANCH], text=True).strip()
    remote = subprocess.check_output(['git', 'ls-remote', REPO_URL, 'refs/heads/' + BRANCH], text=True, timeout=30).split()[0]
    assert local == remote, 'HEAD remoto diverge; não usar force-push'
    print('PUSH_CONFIRMED', BRANCH, local)
    import shutil
    shutil.rmtree(CACHE, ignore_errors=True)  # segredos nunca persistem além desta chamada
    now = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=-3))).isoformat(timespec='seconds')
    with (ROOT / 'day_watch.log').open('a') as f:
        f.write(now + ' GitHub PUSH_CONFIRMED origin/' + BRANCH + '=' + local +
                ' árvore limpa (sem gemma/official); OAuth public_repo; sem force-push; segredo fora de snapshots.\n')
else:
    print('uso: github_device_export.py begin|complete')
    sys.exit(2)
