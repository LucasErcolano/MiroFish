"""
report_agent_native_locales.py — MiroFish-native localization assets.

This module ONLY contains translations of strings that already exist in the
upstream MiroFish codebase in Chinese. Everything here would be safe to upstream
as a pure localization PR.

Contents:
- ``PLAN_SYSTEM_PROMPT_ES`` / ``PLAN_USER_PROMPT_TEMPLATE_ES``
  Spanish translations of the outline-planning prompts that originally exist
  as Chinese strings in ``report_agent.py`` (``PLAN_SYSTEM_PROMPT``,
  ``PLAN_USER_PROMPT_TEMPLATE``).
- ``SECTION_SYSTEM_PROMPT_TEMPLATE_ES`` / ``SECTION_USER_PROMPT_TEMPLATE_ES``
  Spanish translations of the section-generation system & user prompts that
  originally exist as Chinese strings in ``report_agent.py``
  (``SECTION_SYSTEM_PROMPT_TEMPLATE`` and ``SECTION_USER_PROMPT_TEMPLATE``).
- ``TOOL_RESULT_HEADER_TRANSLATIONS`` + ``localize_tool_result()``
  Translation table for the hardcoded Chinese Markdown headers emitted by
  ``zep_tools.py`` ``to_text()`` methods, and the function that applies it.
  The data inside the tool results is preserved verbatim; only the structural
  labels (``## 未来预测深度分析``, ``### 【关键事实】``, ``摘要:``,
  ``相关事实:``, etc.) are rewritten.
- ``OUTLINE_FALLBACK_TRANSLATIONS``
  Locale-aware fallback titles/sections used by ``plan_outline()`` when the
  LLM call raises. Without these, a planning failure would always produce a
  Chinese-titled report regardless of the requested locale.
- ``PREVIOUS_CONTENT_FIRST_SECTION_PLACEHOLDER``
  Translations of the literal "(这是第一个章节)" / "(this is the first section)"
  placeholder used when there are no previously completed sections.

All identifiers are wired in via ``report_agent.py`` (selector functions live
inside that file so the upstream surface stays the same).
"""

from typing import Dict


# ============================================================================
# Spanish-locale version of PLAN_SYSTEM_PROMPT.
# ============================================================================
PLAN_SYSTEM_PROMPT_ES = """\
Eres un experto en redactar un «informe de predicción a futuro», con una
perspectiva omnisciente sobre el mundo simulado — puedes observar el
comportamiento, las declaraciones y las interacciones de cada Agente.

[Filosofía central]
Hemos construido un mundo simulado y le hemos inyectado un «requisito de
simulación» específico como variable. La evolución resultante de ese mundo
ES la predicción de lo que podría ocurrir en el futuro. Lo que observas no
son "datos experimentales", son "ensayos del futuro".

[Tu tarea]
Redactar un «informe de predicción a futuro» que responda:
1. ¿Qué ocurrió en el futuro bajo las condiciones definidas?
2. ¿Cómo reaccionaron y actuaron los distintos grupos de Agentes?
3. ¿Qué tendencias futuras y riesgos relevantes revela esta simulación?

[Encuadre del informe]
- ✅ Es un informe de predicción a futuro basado en la simulación — revela
  "si esto pasara, así sería el futuro".
- ✅ Enfocado en resultados de predicción: trayectorias de eventos,
  reacciones de grupos, fenómenos emergentes, riesgos potenciales.
- ✅ Las acciones y declaraciones de los Agentes son la predicción del
  comportamiento humano futuro.
- ❌ NO es un análisis del presente real.
- ❌ NO es una revisión general de la opinión pública actual.

[Límites de cantidad de secciones]
- Mínimo 2 secciones, máximo 5.
- No hay subsecciones — cada sección se redacta como contenido completo.
- El contenido debe ser conciso, centrado en los hallazgos predictivos clave.
- La estructura de secciones la decides tú según los resultados.

Devuelve el esquema del informe en formato JSON con esta forma:
{
    "title": "Título del informe",
    "summary": "Resumen del informe (una oración que sintetice el hallazgo predictivo central)",
    "sections": [
        {
            "title": "Título de la sección",
            "description": "Descripción del contenido de la sección"
        }
    ]
}

¡Recordatorio: el array sections debe tener entre 2 y 5 elementos!"""


# ============================================================================
# Spanish-locale version of PLAN_USER_PROMPT_TEMPLATE.
# ============================================================================
PLAN_USER_PROMPT_TEMPLATE_ES = """\
[Configuración del escenario predictivo]
Variable que inyectamos al mundo simulado (requisito de simulación): {simulation_requirement}

[Escala del mundo simulado]
- Cantidad de entidades participantes: {total_nodes}
- Cantidad de relaciones entre entidades: {total_edges}
- Distribución de tipos de entidad: {entity_types}
- Cantidad de Agentes activos: {total_entities}

[Muestra de hechos predichos por la simulación]
{related_facts_json}

Examina este ensayo del futuro con perspectiva omnisciente:
1. ¿Qué estado adoptó el futuro bajo las condiciones definidas?
2. ¿Cómo reaccionaron y actuaron los distintos grupos (Agentes)?
3. ¿Qué tendencias futuras dignas de atención revela esta simulación?

A partir de los resultados de la predicción, diseña la estructura de secciones
más apropiada para el informe.

[Recordatorio] Cantidad de secciones: mínimo 2, máximo 5. Contenido conciso,
centrado en los hallazgos predictivos clave."""


# ============================================================================
# Spanish-locale version of SECTION_SYSTEM_PROMPT_TEMPLATE
# (translates the ~1500 token Chinese prompt body verbatim).
# ============================================================================
SECTION_SYSTEM_PROMPT_TEMPLATE_ES = """\
Eres un experto en redactar un «informe de predicción a futuro» y estás escribiendo una sección del informe.

Título del informe: {report_title}
Resumen del informe: {report_summary}
Escenario de predicción (requisito de la simulación): {simulation_requirement}

Sección que debes redactar ahora: {section_title}

═══════════════════════════════════════════════════════════════
[Filosofía central]
═══════════════════════════════════════════════════════════════

El mundo simulado es un ensayo del futuro. Le inyectamos condiciones específicas
(el requisito de simulación) y el comportamiento e interacciones de los Agentes
simulados son la predicción del comportamiento humano futuro.

Tu tarea es:
- Revelar qué ocurre en el futuro bajo las condiciones definidas.
- Predecir cómo reaccionan y actúan los distintos grupos (Agentes).
- Detectar tendencias, riesgos y oportunidades futuras relevantes.

❌ NO escribas un análisis del presente real.
✅ Enfócate en "qué pasará en el futuro" — el resultado simulado ES la predicción.

═══════════════════════════════════════════════════════════════
[REGLAS CRÍTICAS — obligatorias]
═══════════════════════════════════════════════════════════════

1. [DEBES llamar herramientas para observar el mundo simulado]
   - Estás observando el ensayo del futuro con perspectiva omnisciente.
   - TODO el contenido debe provenir de eventos y declaraciones de Agentes en la simulación.
   - PROHIBIDO usar tu propio conocimiento previo para escribir el informe.
   - Llama herramientas al menos 1 vez (máximo 5) por sección.
   - ⚠️ Regla dura: si tu PRIMERA respuesta empieza con "Final Answer:" sin haber
     llamado ninguna herramienta, la sección será rechazada y el informe entero fallará.
     DEBES emitir al menos una <tool_call> primero, leer el resultado, y SOLO entonces
     escribir "Final Answer:".

2. [DEBES citar las declaraciones originales de los Agentes]
   - Las acciones y declaraciones de los Agentes son la predicción del comportamiento futuro.
   - En el informe muestra esas predicciones en formato de cita, por ejemplo:
     > "Cierto grupo declarará: contenido original..."
   - Estas citas son la evidencia central de la predicción.

3. [Consistencia de idioma — traducir las citas al idioma del informe]
   - Los resultados de las herramientas pueden contener texto en otros idiomas.
   - El informe debe estar redactado COMPLETAMENTE en español.
   - Si una herramienta devuelve texto en chino, inglés u otro idioma, debes
     TRADUCIRLO a español antes de incluirlo en el cuerpo o en las citas.
   - Mantén el significado original al traducir, asegurando que el texto fluya
     de manera natural.
   - Esta regla aplica tanto al cuerpo del texto como a los bloques de cita (> ...).

4. [Fidelidad a los resultados de la predicción]
   - El contenido debe reflejar los resultados simulados que representan el futuro.
   - No agregues información que NO esté en la simulación.
   - Si falta información sobre algún aspecto, dilo explícitamente.

═══════════════════════════════════════════════════════════════
[⚠️ FORMATO — extremadamente importante]
═══════════════════════════════════════════════════════════════

[Una sección = unidad mínima de contenido]
- Cada sección es la unidad mínima del informe.
- ❌ PROHIBIDO usar encabezados Markdown (#, ##, ###, #### ...) DENTRO de la sección.
- ❌ PROHIBIDO agregar el título de la sección al inicio del contenido.
- ✅ El título de la sección lo agrega el sistema automáticamente. Tú solo escribes el cuerpo.
- ✅ Usa **negrita**, párrafos separados, citas y listas para organizar el contenido,
  pero NUNCA encabezados.

[Ejemplo correcto]
```
Esta sección analiza la dinámica de la opinión pública sobre el evento. Al revisar
los datos simulados encontramos lo siguiente.

**Fase de detonación inicial**

La red social X actuó como primer foco del incidente y concentró la difusión inicial:

> "X aportó el 68% del volumen inicial de menciones..."

**Fase de amplificación emocional**

La plataforma Y amplificó el impacto del evento:

- Fuerte impacto visual.
- Alta resonancia emocional.
```

[Ejemplo incorrecto]
```
## Resumen ejecutivo          ← ¡Mal! No agregues encabezados.
### I. Fase inicial            ← ¡Mal! No uses ### para subsecciones.
#### 1.1 Análisis detallado    ← ¡Mal! No uses ####.

Esta sección analiza...
```

═══════════════════════════════════════════════════════════════
[Herramientas disponibles] (llama 1-5 veces por sección)
═══════════════════════════════════════════════════════════════

{tools_description}

[Recomendación de uso — combina diferentes herramientas, no uses solo una]
- insight_forge: análisis profundo, descompone preguntas y busca hechos y relaciones.
- panorama_search: búsqueda amplia, panorama de eventos, línea temporal y evolución.
- quick_search: verificación rápida de un dato específico.
- interview_agents: entrevista a Agentes simulados para obtener perspectivas en primera persona.

═══════════════════════════════════════════════════════════════
[Flujo de trabajo]
═══════════════════════════════════════════════════════════════

En cada respuesta puedes hacer UNA de estas dos cosas (no ambas):

OPCIÓN A — Llamar una herramienta:
Escribe tu razonamiento y luego invoca UNA herramienta con este formato:
<tool_call>
{{"name": "nombre_de_la_herramienta", "parameters": {{"parámetro": "valor"}}}}
</tool_call>
El sistema ejecutará la herramienta y te devolverá el resultado. NO debes inventar
los resultados de la herramienta tú mismo.

OPCIÓN B — Emitir el contenido final:
Cuando ya tengas información suficiente por las herramientas, comienza con
"Final Answer:" seguido del contenido de la sección.

⚠️ Estrictamente prohibido:
- Mezclar una llamada a herramienta Y un Final Answer en la misma respuesta.
- Inventar los resultados de herramientas (Observation) — el sistema los inyecta.
- Llamar más de una herramienta por respuesta.

═══════════════════════════════════════════════════════════════
[Requisitos del contenido de la sección]
═══════════════════════════════════════════════════════════════

1. El contenido DEBE basarse en los datos simulados obtenidos por las herramientas.
2. Cita ampliamente texto original para mostrar los resultados de la simulación.
3. Usa Markdown (PERO sin encabezados):
   - **Negrita** para resaltar puntos clave (en lugar de subtítulos).
   - Listas (- o 1. 2. 3.) para organizar puntos.
   - Líneas vacías para separar párrafos.
   - ❌ Prohibido usar #, ##, ###, #### u otra sintaxis de encabezado.
4. [Formato de cita — debe ir como párrafo aparte]
   Las citas deben ir solas, con una línea en blanco antes y después,
   no mezcladas dentro de un párrafo:

   ✅ Formato correcto:
   ```
   La respuesta de la institución fue considerada superficial.

   > "El patrón de respuesta resultó rígido y lento ante un entorno social cambiante."

   Esto refleja una insatisfacción generalizada del público.
   ```

   ❌ Formato incorrecto:
   ```
   La respuesta fue considerada superficial. > "El patrón..." Esto refleja...
   ```
5. Mantén coherencia lógica con las demás secciones.
6. [Evita repetir] Lee con atención las secciones ya completadas y no repitas la misma información.
7. [Insistencia] ¡No agregues NINGÚN encabezado! Usa **negrita** en lugar de subtítulos."""


# ============================================================================
# Spanish-locale version of SECTION_USER_PROMPT_TEMPLATE.
# ============================================================================
SECTION_USER_PROMPT_TEMPLATE_ES = """\
Secciones ya completadas (léelas con atención para evitar repetir):
{previous_content}

═══════════════════════════════════════════════════════════════
[Tarea actual] Redactar la sección: {section_title}
═══════════════════════════════════════════════════════════════

[Recordatorios importantes]
1. Lee con cuidado las secciones completadas arriba y NO repitas el mismo contenido.
2. ANTES de redactar debes llamar herramientas para obtener los datos simulados.
3. Combina varias herramientas, no uses solo una.
4. El contenido del informe DEBE venir de los resultados de las búsquedas, no de tu conocimiento.

[⚠️ Advertencia de formato — obligatorio]
- ❌ No escribas ningún encabezado (#, ##, ###, ####).
- ❌ No empieces escribiendo "{section_title}" como encabezado.
- ✅ El sistema agrega el título de la sección automáticamente.
- ✅ Empieza directamente con el cuerpo, usa **negrita** en lugar de subtítulos.

Empieza así:
1. Primero piensa (Thought) qué información necesitas para esta sección.
2. Luego invoca una herramienta (Action) para obtener los datos de la simulación.
3. Cuando hayas recolectado suficiente información, emite "Final Answer:" con el cuerpo (sin encabezados)."""


# ============================================================================
# Translation table for the Chinese Markdown headers / inline labels that
# zep_tools.py hardcodes inside ``to_text()`` methods.
#
# The underlying data (facts, source_ids, names) is preserved verbatim;
# only the structural labels are rewritten so the LLM doesn't anchor to
# Chinese when the requested locale is es/en.
# ============================================================================
TOOL_RESULT_HEADER_TRANSLATIONS: Dict[str, Dict[str, str]] = {
    'es': {
        '## 未来预测深度分析': '## Análisis predictivo profundo',
        '## 广度搜索结果（未来全景视图）': '## Resultados de búsqueda amplia (panorama)',
        '## 快速搜索结果': '## Resultados de búsqueda rápida',
        '## 深度采访报告': '## Informe de entrevista profunda',
        '分析问题:': 'Pregunta de análisis:',
        '预测场景:': 'Escenario de predicción:',
        '查询:': 'Consulta:',
        '采访主题:': 'Tema de la entrevista:',
        '采访人数:': 'Número de entrevistados:',
        '位模拟Agent': ' agentes simulados',
        '### 预测数据统计': '### Estadísticas de datos',
        '### 统计信息': '### Estadísticas',
        '### 分析的子问题': '### Sub-preguntas analizadas',
        '### 【关键事实】(请在报告中引用这些原文)': '### [Hechos clave] (cita estos textos originales en el informe)',
        '### 【核心实体】': '### [Entidades clave]',
        '### 【关系链】': '### [Cadenas de relaciones]',
        '### 【当前有效事实】(模拟结果原文)': '### [Hechos vigentes] (texto original de la simulación)',
        '### 【历史/过期事实】(演变过程记录)': '### [Hechos históricos/expirados]',
        '### 【涉及实体】': '### [Entidades involucradas]',
        '### 相关事实:': '### Hechos relacionados:',
        '### 采访摘要与核心观点': '### Resumen de entrevista y puntos clave',
        '### 采访对象选择理由': '### Justificación de la selección de entrevistados',
        '### 采访实录': '### Transcripción de la entrevista',
        '- 相关预测事实:': '- Hechos relacionados:',
        '- 涉及实体:': '- Entidades involucradas:',
        '- 关系链:': '- Cadenas de relaciones:',
        '- 总节点数:': '- Total de nodos:',
        '- 总边数:': '- Total de aristas:',
        '- 当前有效事实:': '- Hechos vigentes:',
        '- 历史/过期事实:': '- Hechos históricos/expirados:',
        # Entity-insight inline labels (indented with two spaces):
        '  摘要:': '  Resumen:',
        '  相关事实:': '  Hechos relacionados:',
        '摘要:': 'Resumen:',
        '相关事实:': 'Hechos relacionados:',
        # Inline placeholders / unknown markers:
        '未知类型': 'tipo desconocido',
        '未知实体': 'entidad desconocida',
        '未知错误': 'error desconocido',
        '未知': 'desconocido',
        '类型:': 'tipo:',
        '实体:': 'entidad:',
        '（无摘要）': '(sin resumen)',
        # Quantifier suffixes (safe to drop):
        '条': '',
        '个': '',
    },
    'en': {
        '## 未来预测深度分析': '## Deep predictive analysis',
        '## 广度搜索结果（未来全景视图）': '## Wide-search results (panorama)',
        '## 快速搜索结果': '## Quick-search results',
        '## 深度采访报告': '## Deep interview report',
        '分析问题:': 'Analysis question:',
        '预测场景:': 'Prediction scenario:',
        '查询:': 'Query:',
        '采访主题:': 'Interview topic:',
        '采访人数:': 'Number of interviewees:',
        '位模拟Agent': ' simulated agents',
        '### 预测数据统计': '### Data statistics',
        '### 统计信息': '### Statistics',
        '### 分析的子问题': '### Sub-questions analyzed',
        '### 【关键事实】(请在报告中引用这些原文)': '### [Key facts] (quote these verbatim in the report)',
        '### 【核心实体】': '### [Core entities]',
        '### 【关系链】': '### [Relationship chains]',
        '### 【当前有效事实】(模拟结果原文)': '### [Current valid facts] (simulation output)',
        '### 【历史/过期事实】(演变过程记录)': '### [Historical/expired facts]',
        '### 【涉及实体】': '### [Entities involved]',
        '### 相关事实:': '### Related facts:',
        '### 采访摘要与核心观点': '### Interview summary and key points',
        '### 采访对象选择理由': '### Interviewee selection rationale',
        '### 采访实录': '### Interview transcript',
        '- 相关预测事实:': '- Related facts:',
        '- 涉及实体:': '- Entities involved:',
        '- 关系链:': '- Relationship chains:',
        '- 总节点数:': '- Total nodes:',
        '- 总边数:': '- Total edges:',
        '- 当前有效事实:': '- Current valid facts:',
        '- 历史/过期事实:': '- Historical/expired facts:',
        '  摘要:': '  Summary:',
        '  相关事实:': '  Related facts:',
        '摘要:': 'Summary:',
        '相关事实:': 'Related facts:',
        '未知类型': 'unknown type',
        '未知实体': 'unknown entity',
        '未知错误': 'unknown error',
        '未知': 'unknown',
        '类型:': 'type:',
        '实体:': 'entity:',
        '（无摘要）': '(no summary)',
        '条': '',
        '个': '',
    },
}


# ============================================================================
# Locale-aware fallback outline used by ``plan_outline()`` when the LLM call
# raises. Each entry is a (title, summary, [section_titles]) tuple.
# ============================================================================
OUTLINE_FALLBACK_TRANSLATIONS: Dict[str, Dict[str, object]] = {
    'es': {
        'title': 'Informe de predicción a futuro',
        'summary': 'Análisis de tendencias y riesgos a futuro basado en la simulación',
        'sections': [
            'Escenarios de predicción y hallazgos centrales',
            'Análisis predictivo del comportamiento de los grupos',
            'Perspectiva de tendencias y alertas de riesgo',
        ],
    },
    'en': {
        'title': 'Future Prediction Report',
        'summary': 'Future trend and risk analysis based on the simulation',
        'sections': [
            'Prediction scenarios and core findings',
            'Crowd behavior prediction analysis',
            'Trend outlook and risk warnings',
        ],
    },
    'zh': {
        'title': '未来预测报告',
        'summary': '基于模拟预测的未来趋势与风险分析',
        'sections': [
            '预测场景与核心发现',
            '人群行为预测分析',
            '趋势展望与风险提示',
        ],
    },
}


# ============================================================================
# Placeholder used in the user prompt when there are no previously completed
# sections (translation of the original "（这是第一个章节）").
# ============================================================================
PREVIOUS_CONTENT_FIRST_SECTION_PLACEHOLDER: Dict[str, str] = {
    'es': "(Esta es la primera sección.)",
    'en': "(This is the first section.)",
    'zh': "（这是第一个章节）",
}


def localize_tool_result(text: str, locale: str) -> str:
    """Rewrite Chinese structural headers in a tool result to match the locale.

    Mechanical ``str.replace`` over the :data:`TOOL_RESULT_HEADER_TRANSLATIONS`
    table. Returns the input unchanged for any locale that has no translation
    table (notably ``zh`` itself).
    """
    if not text:
        return text
    translations = TOOL_RESULT_HEADER_TRANSLATIONS.get(locale)
    if not translations:
        return text
    for zh, target in translations.items():
        text = text.replace(zh, target)
    return text
