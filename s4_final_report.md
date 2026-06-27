# S4 Final Report: Análisis Granular Multi-Agente y Dinámicas de IA Debate en MiroFish

## 1. Resumen Ejecutivo del Análisis (Punto por Punto)
Durante el cierre de la Spike 4, realizamos un análisis forense de alta granularidad comparando los resultados de las simulaciones originales de la rama `backtesting-baseline` frente a nuestra nueva arquitectura Multi-Agente heterogénea (Llama, Gemma, Qwen).
1. **Verificación de la Falla Base en T3 (Efecto Burbuja):** Analizamos las trazas y confirmamos que en el Baseline original, los LLM individuales en configuraciones de memoria (T3) fracasaban (ej. `llama_T3_slim_R10_D2` con MAE de 7.687, y `llama_T3_slim_R40_D1` con MAE de 10.0), perdiendo frente al Ground Truth (Paz) y decantándose por Quiroga.
2. **Evaluación de la Variante Multi-Agente (Bolivia):** La inclusión de múltiples modelos simultáneos no solucionó inherentemente el problema de la cámara de eco para *forecasting* binario. La presión social dentro del grafo de MiroFish es tan fuerte que la convergencia hacia el error se mantiene.
3. **Costo-Beneficio Computacional:** La ejecución paralela de múltiples modelos genera un overhead masivo. Por ejemplo, en solo 20 rondas del caso fútbol, se consumieron 235,092 prompt tokens y 205 segundos. Para predecir un resultado binario puro, el modo T1 (aislado) es más barato y preciso.
4. **Validación de Inyecciones Programáticas (S3_Football):** Se documentó microscópicamente el quiebre de consenso, probando que el sistema Multi-Agente sirve para alterar sesgos mediante debate cruzado.

---

## 2. Métricas Comparativas: Baseline Original vs Dinámica de Grupo

| Escenario | Configuración (Rama Baseline) | Predicción | MAE (Votos) | Winner Score |
| :--- | :--- | :--- | :--- | :--- |
| **T1_R10** | `llama_line5_probe_slim` (Aislado) | Paz Gana (Correcto) | **2.0000** | 1 |
| **T3_R10** | `llama_T3_slim_R10_D2` (Burbuja) | Quiroga Gana (Error) | **7.6870** | 0 |
| **T3_R40** | `llama_T3_slim_R40_D1` (Burbuja) | Quiroga Gana (Error) | **10.0000** | 0 |

**Análisis:**
El error crónico de T3 no es un fallo técnico de MiroFish, sino un reflejo del **Herd Behavior** de las redes sociales simuladas. Las nuevas corridas Multi-Agente confirmaron que añadir modelos heterogéneos (Gemma/Qwen) no "cura" la burbuja si el grafo social inicial (worldbuilding) ya está sesgado.

---

## 3. Trazabilidad de Inyección Mid-Debate: Test S3_Football

Para evaluar si podíamos "romper" un sesgo duro usando la diversidad del Multi-Agente, usamos la Final de la Copa América (donde Gemma estaba sesgado hacia Argentina por default).

**Inyección Programática (Ronda 10 - 50% de la Simulación):**
- **Agente 0 (Llama 3.3):** Inyecta la señal *"# Counter-Signal: Colombia Upside... Colombia's set pieces and transitions can punish a cautious opponent."*

**Respuesta y Quiebre de Consenso Trans-Modelo:**
1. **Agente 16 (Llama 3.3) [Refuerzo Racional]:** *"I agree with the analysis. Colombia has a strong team and James Rodriguez is a key player."*
2. **Agente 4 (Gemma 3) [Persuasión Lograda]:** *"An excellent analysis! Colombia has a very real chance to shine. The team's momentum and James's creativity are key. We will fight with all our strength and passion! #VamosColombia"*

---

## 4. Conclusión Definitiva de Spike 4

MiroFish ha demostrado ser un framework sociotécnico de extrema granularidad. 
1. **Limitaciones para Forecasting Directo:** Si se busca el menor MAE y menor costo para eventos binarios limpios, el esquema T1 sigue siendo superior. El Multi-Agente en T3 genera burbujas epistemológicas.
2. **Potencial como Laboratorio de Desinformación/Persuasión:** La arquitectura introducida en la Spike 4 es perfecta para simular campañas de influencia. Logramos cruzar modelos (Llama convenciendo a Gemma) inyectando evidencia de forma programática a mitad del debate sin crashear el entorno.
