#!/bin/bash
# harness_download.sh — baixa dados p/ validação OFFLINE de frag-derivados (sem slots)
export PATH="$HOME/.local/bin:$PATH"
D=/home/user/harness_data
LOG=/home/user/harness_download.log
mkdir -p $D
echo "[$(date -u +%FT%TZ)] início downloads" >> $LOG
kaggle competitions download -c enveda-CASMI26-molecule-id-mass-spectra -p $D >> $LOG 2>&1
echo "[$(date -u +%FT%TZ)] competition baixada" >> $LOG
for ds in prvsiyan/coconut-casmi26-candidates prvsiyan/chebi-lipidmaps-casmi26 prvsiyan/casmi26-ranker-features prvsiyan/casmi26-fp-models-v2; do
  n=$(basename $ds)
  mkdir -p $D/$n
  kaggle datasets download $ds -p $D/$n --unzip >> $LOG 2>&1
  echo "[$(date -u +%FT%TZ)] $n ok" >> $LOG
done
cd $D && unzip -o -q *.zip >> $LOG 2>&1 && rm -f *.zip
echo "[$(date -u +%FT%TZ)] FIM" >> $LOG
du -sh $D/* >> $LOG 2>&1
