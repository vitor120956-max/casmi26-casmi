#!/data/data/com.termux/files/usr/bin/bash
# replica_watch.sh — RÉPLICAS NOTURNAS (rascunho p/ adaptar ao ksubmit.py do usuário)
# Uso: bash replica_watch.sh <VERSAO_KERNEL> <QTD_REPLICAS>
# Ex.: bash replica_watch.sh 4 3   → ressubmete a versão 4 três vezes (novo seed do ranker a cada run)
#
# ADAPTAR após usuário colar ~/ksubmit.py e ~/night_watch.sh:
#  - linha de submissão (SUBMIT_CMD) com a assinatura exata do ksubmit.py dele
#  - leitura de score (STATUS_CMD) com o que o night_watch.sh já usa
VER=$1
N=${2:-2}
COMP=enveda-CASMI26-molecule-id-mass-spectra
SLUG=victor120956/casmi26-prvsiyan-canonical-fp-v6-ensemble
LOG=~/night_watch.log

echo "[$(date -u +%FT%TZ)] replica_watch iniciado: ver=$VER n=$N" >> $LOG
for i in $(seq 1 "$N"); do
  # 1) SUBMETER (placeholder — trocar pela chamada real do ksubmit.py)
  # SUBMIT_CMD: python ~/ksubmit.py "$COMP" --slug "$SLUG" --version "$VER" -m "replica $i/$N seed-noise"
  echo "[$(date -u +%FT%TZ)] replica $i/$N: SUBMIT_CMD aqui" >> $LOG

  # 2) ESPERAR O SCORE (scoreamento = re-execução do kernel no hidden, ~60-110 min)
  sleep 6600
  # STATUS_CMD: ler 'kaggle competitions submissions' e logar a linha mais recente
  echo "[$(date -u +%FT%TZ)] replica $i/$N: STATUS_CMD aqui" >> $LOG
  sleep 600
done
echo "[$(date -u +%FT%TZ)] replica_watch concluído" >> $LOG
