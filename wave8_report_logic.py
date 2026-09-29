"""Pure next-step logic: terminal failures must not be described as awaiting scores."""
from safety_guards import classify_submission

def next_step(submissions, expected=5):
    rejected=[s for s in submissions if classify_submission(s)=='REJEITADA']
    waiting=[s for s in submissions if classify_submission(s)=='AGUARDANDO_NOTA']
    missing=max(0,expected-len(submissions))
    if rejected:
        if waiting or missing:
            return (f'{len(rejected)} envio(s) rejeitado(s): registrar e diagnosticar as falhas. '
                    f'{len(waiting)+missing} resultado(s) ainda pendente(s) ou ausente(s). '
                    'Não promover mecanismos; não reenviar arquivos idênticos.')
        return (f'Lote encerrado: {len(rejected)} envio(s) rejeitado(s), sem resultados suficientes para comparar mecanismos. '
                'Diagnosticar a reexecução antes de novos builds. Não aguardar notas desses erros nem reenviar arquivos idênticos.')
    if waiting or missing:
        return 'Aguardar as notas faltantes antes de escolher o próximo build. Sem retry de submits aceitos.'
    return 'Lote encerrado; interpretar notas somente com a guarda de atribuição e referência confirmada.'
