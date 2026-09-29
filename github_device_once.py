#!/usr/bin/env python3
"""Fluxo oficial de dispositivo GitHub; uma troca após confirmação, sem polling."""
import sys,os,json,pathlib,requests,subprocess,datetime
from safety_guards import GITHUB_CLI_CLIENT_ID,validate_oauth
ROOT=pathlib.Path('/home/user');CACHE=ROOT/'.cache/github-device'
CACHE.mkdir(parents=True,exist_ok=True,mode=0o700)
CLIENT=GITHUB_CLI_CLIENT_ID
validate_oauth(CLIENT)
HEADERS={'Accept':'application/json','User-Agent':'GitHub-CLI-device-flow'}
def private(name,data):
 p=CACHE/name;p.write_text(json.dumps(data));p.chmod(0o600)
if sys.argv[1]=='begin':
 r=requests.post('https://github.com/login/device/code',headers=HEADERS,data={'client_id':CLIENT,'scope':'public_repo'},timeout=30);r.raise_for_status()
 d=r.json();assert 'device_code' in d, d.get('error','No device code')
 private('device.json',d)
 print('URL:',d['verification_uri']);print('CÓDIGO:',d['user_code']);print('Validade (segundos):',d['expires_in'])
elif sys.argv[1]=='complete':
 d=json.loads((CACHE/'device.json').read_text())
 r=requests.post('https://github.com/login/oauth/access_token',headers=HEADERS,data={'client_id':CLIENT,'device_code':d['device_code'],'grant_type':'urn:ietf:params:oauth:grant-type:device_code'},timeout=30);r.raise_for_status()
 auth=r.json()
 if not auth.get('access_token'):
  print('Autorização não concluída:',auth.get('error'),auth.get('error_description'));sys.exit(1)
 scopes={s.strip() for s in auth.get('scope','').replace(' ', ',').split(',') if s.strip()}
 validate_oauth(CLIENT,scopes)
 private('session.json',auth)
 print('Escopos confirmados:', ', '.join(sorted(scopes)),flush=True)
 env=dict(os.environ,GH_TOKEN=auth['access_token'],GH_CONFIG_DIR=str(ROOT/'.cache/gh-auth'),GIT_TERMINAL_PROMPT='0')
 headers={'Authorization':'Bearer '+auth['access_token'],'Accept':'application/vnd.github+json'}
 user=requests.get('https://api.github.com/user',headers=headers,timeout=30);user.raise_for_status()
 print('GitHub autorizado:',user.json()['login'],flush=True)
 repo=requests.get('https://api.github.com/repos/vitor120956-max/casmi26-casmi',headers=headers,timeout=30);repo.raise_for_status()
 assert repo.json().get('permissions',{}).get('push'), 'Conta sem permissão push neste projeto'
 cmd=['git','-C',str(ROOT/'recovered'),'-c','credential.helper=!/home/user/.local/bin/gh auth git-credential','push','origin','main']
 subprocess.run(cmd,env=env,check=True,timeout=120)
 local=subprocess.check_output(['git','-C',str(ROOT/'recovered'),'rev-parse','HEAD'],text=True).strip()
 remote=subprocess.check_output(['git','ls-remote','https://github.com/vitor120956-max/casmi26-casmi.git','refs/heads/main'],text=True,timeout=30).split()[0]
 assert local==remote, 'HEAD remoto diverge; não usar force-push'
 print('PUSH_CONFIRMED',local)
 now=datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=-3))).isoformat(timespec='seconds')
 with (ROOT/'day_watch.log').open('a') as f:f.write(now+' GitHub PUSH_CONFIRMED origin/main='+local+' sem force-push; OAuth public_repo, segredo excluído de snapshots.\n')
