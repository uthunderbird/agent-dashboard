---
title: Screen agent-UX — сценарии, риски и mitigation
status: draft
created: 2026-04-26
---

# Screen agent-UX — сценарии, риски и mitigation

Исследование того, как агент взаимодействует с rendered screens, и какие
UX-риски возникают когда screen не инструктирует агента о том, как им
пользоваться.

Источник: Swarm Mode design session, 2026-04-26.

---

## Контекст: как screen попадает к агенту

В femtobot промпт агента имеет три слоя:

```
You are femtobot operating over dashboard `{dashboard_id}` on screen `{screen_id}`.

Bootstrap context:
{bootstrap_context}       ← SOUL.md + AGENTS.md + SKILL.md файлы
                           долгосрочная рабочая память

Current dashboard context:
{attention_context}        ← render_screen() output
                           рабочая память текущего момента

Navigation policy:
{navigation_policy}        ← динамические инструкции (сейчас: hard-coded,
                           только для communications/messages)

Recent session actions:
{recent_session_actions}
```

`attention_context` — это то что производит `agent-dashboard`. Это рабочая
память агента о текущем экране. `bootstrap_context` — долгосрочные
инструкции. `navigation_policy` — динамический bridge между ними.

Ключевой факт: `navigation_policy` богато реализован только для одного
экрана (`communications/messages`). Все остальные экраны получают одну
генерическую фразу: "Do not emit dashboard_control or screen_control unless
you need a real workspace change."

---

## Смоделированные сценарии

### Сценарий 1 — "Первый экран, нет скиллов" (affordance gap)

Агент видит `mail/inbox_summary`. Bootstrap пуст или содержит только общий
SOUL.md без mail-специфичных skills. Rendered screen:

```
Attention items: 3
Breadcrumb: Mail > Inbox Summary
View state: collapsed
Highlights:
  - [high/active] alice@company.com needs review — mail surfaced with posture immediate_attention
    next: Open or expand the screen before taking any external action.
Screen actions:
  - inbox_summary.mark_explored: Mark explored — Record that the current screen has been reviewed.
```

Агент видит три сообщения и одну screen_action. Что делать с `msg-001`?
Как "открыть или расширить" экран? Агент не знает что `screen_control` с
`operation="expand"` — это валидный следующий шаг. Интерфейс показывает
*что есть*, но не *что делать*.

### Сценарий 2 — "Богатый bootstrap, повторный вызов" (coverage asymmetry)

Агент видит `communications/messages` с rich navigation policy:
"You are already on the only shared communications screen. Do not emit
dashboard_control or screen_control... Prefer a reply/send action for the
primary pending message."

Этот сценарий **работает хорошо** — именно потому что `navigation_policy`
для этого экрана содержит task framing. Агент знает: что сделать (reply),
к чему (primary pending message), чего не делать. Это доказывает что
navigation_policy — правильный паттерн. Проблема в том что он реализован
только для одного экрана.

### Сценарий 3 — "Сложная задача, несколько transitions" (task model mismatch)

Агент на `mail/thread_detail`. Должен ответить, но сначала нужно проверить
список участников на `thread_summary`. Rendered screen содержит tool_calls с
`action_id="reply-msg-42"` и `kind="send_message"`. Нет инструкций: нужно
ли сначала `mark_explored`, потом tool_call? Или можно сразу? Агент
оперирует task-моделью ("ответить"), но интерфейс предлагает только action
primitives без task-level sequence.

### Сценарий 4 — "Novice vs expert агент" (no progressive disclosure)

Человек осваивает программу через три стадии: ориентация → обучение →
expertise. Для каждой стадии — разный UX: tooltip → tutorial → shortcuts.
Агент без memory о системе (new context) и агент с богатым memory получают
одинаковый rendered screen. В человеческом UX это была бы серьёзная ошибка.

### Сценарий 5 — "Кастомный экран от consumer" (kind semantics opacity)

Корпоративный проект строит кастомный `tasks/overview` screen. Builder
создаёт `DashboardActionRef(action_id="complete-task-42", kind="complete_task")`.
Агент видит action. Требует ли это approval? Это reversible? Агент не знает.
`kind` — открытая строка без онтологии. `description` заполнен частично.
Агент принимает решение об исполнении без явного сигнала об approval semantics.

---

## Каталог рисков

| ID | Риск | Severity | Затронутые сценарии |
|----|------|----------|---------------------|
| R1 | **Affordance gap** — screen показывает что есть, не показывает что делать | High | Сц. 1, 3 |
| R2 | **Coverage asymmetry** — navigation_policy богатая для communications, пустая для остальных | High | Сц. 2 (по контрасту), 1 |
| R3 | **Task model mismatch** — action primitives без task-level sequence | Medium | Сц. 3 |
| R4 | **No progressive disclosure** — novice и expert агент получают одинаковый rendering | Medium | Сц. 4 |
| R5 | **Kind semantics opacity** — approval semantics action'а не видны агенту | Medium-High | Сц. 5 |

---

## Метауровень: UX аналогия

Как пользователь-человек осваивает программу и как это применимо к агентам:

| Стадия | Human UX | Agent equivalent |
|--------|----------|-----------------|
| Ориентация | Tooltip, onboarding | `screen_instructions` + `suggested_next_step` в rendered output |
| Обучение | Docs, tutorial | `navigation_policy` динамический + SKILL.md в bootstrap |
| Expertise | Keyboard shortcuts, command palette | Компактный render без объяснений, memory о прошлых actions |

Текущий дизайн покрывает стадию "ориентация" частично (`suggested_next_step`)
и стадию "обучение" только для одного экрана. Стадия "expertise" —
подразумевается но не спроектирована.

**Три уровня инструктирования** (из subgroup анализа):

1. **Field-level** — `description` и `suggested_next_step` в rendered output.
   Всегда присутствует. Уже реализован частично.

2. **Screen-level policy** — navigation_policy per screen. Присутствует если
   screen имеет non-obvious navigation semantics. Сейчас hard-coded для одного
   экрана.

3. **Skill layer** — SKILL.md для screen-family. Загружается через bootstrap
   selection если screen сложный или впервые встречается.

---

## Mitigation рекомендации

### M1 — `DashboardScreen.screen_instructions: str | None` (библиотечный)

Добавить опциональное поле в `DashboardScreen`. Renderer рендерит его между
`View state:` и `Highlights:` если не None.

```python
@dataclass(frozen=True)
class DashboardScreen:
    ...
    screen_instructions: str | None = None  # NEW
    ...
```

Rendered output при наличии:
```
View state: collapsed
Screen: На этом экране ты видишь входящую почту. Просмотри highlights и
выбери следующее действие: открыть тред, ответить, или отложить.
Highlights:
  ...
```

**Кто пишет:** builder. **Обязателен ли:** нет, optional с default None.
**Когда использовать:** для любого экрана с non-obvious semantics или новой
screen family. **Не использовать:** для хорошо известных экранов где агент
уже имеет context из bootstrap или recent_actions.

### M2 — `DashboardActionRef.requires_approval: bool = False` (библиотечный)

Добавить explicit approval signal на каждую action reference. Renderer
добавляет `[requires approval]` suffix если `True`.

```python
@dataclass(frozen=True)
class DashboardActionRef:
    ...
    requires_approval: bool = False  # NEW
    ...
```

Rendered output:
```
Tool calls:
  - reply-msg-42: Reply to Alice [requires approval] — Compose and send a reply.
  - snooze-msg-42: Snooze for 1 hour — Defer to later.
```

Агент немедленно видит: reply требует approval, snooze — нет. Это снимает
R5 (kind semantics opacity) без необходимости в строгой kind онтологии.

**Важно:** все `tool_calls` SHOULD иметь `requires_approval=True` по умолчанию
в типичных consumer builders — но library default `False` для backward compat.
Рекомендовать в agent-dx/ документации.

### M3 — `navigation_policy` как declarative поле (femtobot-level)

*Не входит в library protocol.* Рекомендация для femtobot и consumers:

Builder возвращает navigation_policy вместе с screen объектом (или как часть
вспомогательного контейнера). Session assembly layer (`_load_navigation_policy`)
использует его если provided, fallback на generic если нет.

```python
# Пример: build_tasks_screen возвращает и screen, и policy
def build_tasks_overview(tasks, ...) -> tuple[DashboardScreen, str | None]:
    screen = DashboardScreen(...)
    policy = (
        "На этом экране — список задач команды. "
        "Приоритизируй overdue (severity=high). "
        "Для завершения задачи используй tool_call complete_task. "
        "Не используй session_complete пока есть невыполненные overdue задачи."
    ) if tasks else None
    return screen, policy
```

Это решает R2 (coverage asymmetry): каждый builder контролирует свой
navigation policy, а не только communications/messages.

### M4 — SKILL.md per screen-family (naming convention)

*Не входит в library protocol.* Naming convention и шаблон:

```
.agents/skills/{dashboard_id}-screen/SKILL.md
```

Например: `.agents/skills/tasks-screen/SKILL.md`

Bootstrap selection уже фильтрует по `dashboard_id` и `screen_id`.
Если добавить фильтр по `{dashboard_id}-screen`, skills загружаются
автоматически при входе в соответствующий dashboard.

Шаблон SKILL.md для экрана (минимальный):
```markdown
---
name: {dashboard_id}-screen
description: Skills for {dashboard_id} dashboard. Use when agent is on {screen_id}.
---
# {Dashboard} Screen

## Primary goal
{Одна фраза: что агент должен достичь на этом экране}

## Recommended action sequence
1. {Первый шаг}
2. {Второй шаг}
3. {Условие завершения}

## Anti-patterns
- {Что не нужно делать и почему}

## Examples
{Пример успешного прохождения}
```

---

## Приоритизация

| Приоритет | Mitigation | Сложность | Риски которые снимает |
|-----------|-----------|-----------|----------------------|
| 🔴 Высокий | M2: `requires_approval` в протоколе | Низкая | R5 |
| 🔴 Высокий | M1: `screen_instructions` в протоколе | Низкая | R1, R4 |
| 🟡 Средний | M3: `navigation_policy` declarative | Средняя | R2 |
| 🟡 Средний | M4: SKILL.md naming convention | Средняя | R3, R4 |

M1 и M2 — библиотечные изменения, реализуются вместе при имплементации
`agent-dashboard`. M3 и M4 — femtobot-side, реализуются как часть migration.

---

## Следующие шаги

1. Добавить `screen_instructions` и `requires_approval` в `proposals/boundary.md`
   как Decision 7 и Decision 8.
2. Добавить их в `proposals/external-dev-api.md` в секцию public surface.
3. Обновить DX rubric (R-11, R-12) для новых полей.
4. Для femtobot: описать M3 и M4 как migration guidance в boundary.md.
5. Создать `agent-dx/screen-skill-template.md` с шаблоном SKILL.md для экрана.
