#!/bin/bash
# Watchdog: monitorea las 40 rondas, descarga resultados y apaga la VM al terminar.

RUN_DIR_PATTERN="runs/headless/40rounds-ollama-*"
LOG="/tmp/watchdog_40rounds.log"
SSH_PASS='135297lucas'
VM_IP='100.103.29.117'

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG"; }

log "Watchdog iniciado. PID del runner: ${1:-desconocido}"

# Esperar a que aparezca el run dir
while true; do
    RUN_DIR=$(ls -td $RUN_DIR_PATTERN 2>/dev/null | head -1)
    if [ -n "$RUN_DIR" ] && [ -f "$RUN_DIR/request_trace.json" ]; then
        break
    fi
    sleep 30
done

log "Run dir detectado: $RUN_DIR"

# Poll hasta que aparezca run_manifest.json o el proceso termine
RUNNER_PID="${1}"
while true; do
    # Chequear si existe el manifest
    if [ -f "$RUN_DIR/run_manifest.json" ]; then
        log "run_manifest.json encontrado. Run completado."
        break
    fi

    # Chequear si el proceso sigue vivo
    if [ -n "$RUNNER_PID" ] && ! kill -0 "$RUNNER_PID" 2>/dev/null; then
        log "Proceso $RUNNER_PID terminó (sin manifest). Verificando..."
        sleep 10
        if [ -f "$RUN_DIR/run_manifest.json" ]; then
            log "Manifest apareció post-proceso."
            break
        else
            log "ERROR: Proceso terminó pero no hay manifest."
            break
        fi
    fi

    # Log de progreso cada 5 min
    LAST_TRACE=$(python3 -c "
import json
try:
    trace = json.load(open('$RUN_DIR/request_trace.json'))
    for t in reversed(trace):
        r = t.get('response',{})
        if isinstance(r, dict) and r.get('data'):
            d = r['data']
            if 'message' in d:
                print(f'{d.get(\"status\")}|{d.get(\"progress\",\"?\")}%|{d.get(\"message\",\"\")[:80]}')
                break
except: pass
" 2>/dev/null)
    log "Progreso: $LAST_TRACE"
    sleep 120
done

# ── Run completado ──
log "=== RESULTADOS ==="
if [ -f "$RUN_DIR/run_manifest.json" ]; then
    python3 -c "
import json
m = json.load(open('$RUN_DIR/run_manifest.json'))
print(f'  Status: {m.get(\"status\")}')
print(f'  is_real_mirofish: {m.get(\"is_real_mirofish_system\")}')
print(f'  Rounds: {m.get(\"num_rounds_or_epochs\")}')
print(f'  Report: {m.get(\"report_id\", \"N/A\")}')
" 2>/dev/null | tee -a "$LOG"
fi

# Empaquetar resultados
ARCHIVE="/home/lucas76hz/Desktop/MiroFish/runs/headless/results-40rounds-$(date +%Y%m%d-%H%M%S).tar.gz"
log "Empaquetando resultados en $ARCHIVE ..."
tar czf "$ARCHIVE" -C "$RUN_DIR" . 2>/dev/null
log "Archivo creado: $(ls -lh "$ARCHIVE" | awk '{print $5, $NF}')"

# Apagar la VM
log "Apagando VM ($VM_IP)..."
sshpass -p "$SSH_PASS" ssh -o StrictHostKeyChecking=accept-new "lucas76hz@$VM_IP" "sudo shutdown -h now" 2>/dev/null
log "Comando de apagado enviado a la VM."

log "Watchdog finalizado."
