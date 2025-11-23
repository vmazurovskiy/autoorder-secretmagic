# Release Process - SecretMagic Microservice

## 📦 Версионирование

Используем **строгий Semantic Versioning (SemVer)** для всех production и stage релизов.

### Формат версий

**PROD (stable):**
```
v0.1.0
v0.2.0
v1.0.0
```

**STAGE (pre-release):**
```
v0.1.0-rc.1
v0.1.0-rc.2
v1.0.0-rc.1
```

**DEV (образы):**
```
dev-{BRANCH_SANITIZED}-{SHORT_SHA}

Примеры:
- dev-fix-nan-handling-a1b2c3d
- dev-feature-bom-explosion-e4f5g6h
- dev-develop-i7j8k9l
```

---

## 🎯 Правила версионирования (SemVer)

### MAJOR (X.0.0)
**Когда увеличивать:** Breaking changes (несовместимые изменения)

**Примеры:**
- Изменение gRPC контрактов (удаление/переименование полей)
- Изменение схемы БД без обратной совместимости
- Изменение формата выходных данных для trainer/inference (breaking)
- Удаление deprecated API endpoints

### MINOR (0.X.0)
**Когда увеличивать:** Новая функциональность (обратно совместимая)

**Примеры:**
- Добавление новых feature engineering функций (новые лаги, сезонность, погода)
- Новые capability-флаги
- Улучшения BOM explosion (новые уровни декомпозиции)
- Новые типы данных (bom_lvl3, kitchen_production)
- Расширение API (новые endpoints)
- Внутренние изменения, требующие миграций БД (но обратно совместимые)

### PATCH (0.0.X)
**Когда увеличивать:** Исправления багов, security fixes

**Примеры:**
- Bugfix без изменения API
- Security patches
- Оптимизации производительности
- Исправления lint ошибок (ruff, mypy)
- Обновление зависимостей (без breaking changes)
- Исправление NaN handling в фичах

---

## 🔄 Release Workflows

### 1. Feature Release (MINOR)

**Сценарий:** Добавление новой функциональности

```bash
# 1. Создать feature ветку от develop
git checkout develop
git pull origin develop
git checkout -b feature/weather-features

# 2. Разработка + тесты
# ... код ...

# 3. Создать PR в develop
# После мерджа в develop → автоматический деплой в DEV

# 4. Подготовить release candidate для STAGE
git checkout develop
git pull origin develop
git tag v0.2.0-rc.1 -m "Release candidate: weather features"
git push origin v0.2.0-rc.1

# → CI/CD автоматически деплоит в STAGE

# 5. После успешного тестирования в STAGE → PROD
git tag v0.2.0 -m "Release: weather features"
git push origin v0.2.0

# → CI/CD автоматически деплоит в PROD
```

---

### 2. Bugfix Release (PATCH)

**Сценарий:** Исправление бага в текущей версии

```bash
# 1. Создать fix ветку от develop
git checkout develop
git pull origin develop
git checkout -b fix/nan-handling

# 2. Исправить баг + тесты
# ... код ...

# 3. Создать PR в develop
# После мерджа → автоматический деплой в DEV

# 4. RC для STAGE
git checkout develop
git pull origin develop
git tag v0.1.1-rc.1 -m "Release candidate: fix NaN handling"
git push origin v0.1.1-rc.1

# 5. После теста → PROD
git tag v0.1.1 -m "Release: fix NaN handling"
git push origin v0.1.1
```

---

### 3. Hotfix Release (PATCH)

**Сценарий:** Критичный баг в production, требующий немедленного исправления

```bash
# 1. Создать hotfix ветку от master (не от develop!)
git checkout master
git pull origin master
git checkout -b hotfix/critical-security-fix

# 2. Исправить критичный баг
# ... минимальные изменения ...

# 3. RC для тестирования в STAGE
git tag v0.1.1-rc.1 -m "Hotfix RC: critical security fix"
git push origin v0.1.1-rc.1

# → CI/CD деплоит в STAGE

# 4. После успешного теста в STAGE → PROD
git tag v0.1.1 -m "Hotfix: critical security fix"
git push origin v0.1.1

# → CI/CD деплоит в PROD

# 5. КРИТИЧНО: Мердж обратно в develop
git checkout develop
git pull origin develop
git merge hotfix/critical-security-fix
git push origin develop

# 6. Удалить hotfix ветку
git branch -d hotfix/critical-security-fix
git push origin --delete hotfix/critical-security-fix
```

**ВАЖНО для hotfix:**
- ⚠️ Создаётся от `master`, НЕ от `develop`
- ⚠️ Содержит ТОЛЬКО минимальные изменения для исправления бага
- ⚠️ ОБЯЗАТЕЛЬНО мерджить обратно в `develop` после релиза
- ⚠️ Формат тега тот же: `v0.1.1-rc.1` / `v0.1.1` (без `-hotfix`)

---

### 4. Breaking Changes Release (MAJOR)

**Сценарий:** Несовместимые изменения, требующие миграции

```bash
# 1. Создать ветку от develop
git checkout develop
git pull origin develop
git checkout -b feature/breaking-api-changes

# 2. Разработка + migration guide
# ... код + документация миграции ...

# 3. PR в develop с BREAKING CHANGE в описании
# Commit message:
# feat!: redesign feature output format for better performance
#
# BREAKING CHANGE: Changed feature column names, removed deprecated fields

# 4. RC для STAGE
git checkout develop
git pull origin develop
git tag v1.0.0-rc.1 -m "Release candidate: v1.0.0 with breaking changes"
git push origin v1.0.0-rc.1

# 5. После тестирования → PROD
git tag v1.0.0 -m "Release: v1.0.0 with breaking changes"
git push origin v1.0.0
```

**ВАЖНО для breaking changes:**
- ⚠️ Обновить CHANGELOG с секцией BREAKING CHANGES
- ⚠️ Написать migration guide
- ⚠️ Уведомить команду заранее

---

## 📋 CHANGELOG

Используем формат [Keep a Changelog](https://keepachangelog.com/).

### Структура

```markdown
# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Feature in development

## [0.2.0] - 2025-11-25

### Added
- Weather features (temperature, precipitation, wind)
- Enhanced BOM explosion with level 3 support
- Promo impact features

### Changed
- Improved NaN handling with explicit decay semantics
- Optimized Polars operations for large datasets

### Fixed
- Fixed exponential moving average calculation for sparse data

## [0.1.1] - 2025-11-24

### Fixed
- Critical security vulnerability in credentials handling
- NaN propagation in rolling window calculations

## [0.1.0] - 2025-11-21

### Added
- Initial release
- Feature engineering pipeline (EMA, MA, STD, lags)
- BOM explosion engine (level 1-2)
- StarRocks integration
- PostgreSQL logging
```

### Типы изменений

- **Added** - новые фичи
- **Changed** - изменения существующей функциональности
- **Deprecated** - функциональность, которая будет удалена в будущем
- **Removed** - удалённая функциональность
- **Fixed** - исправления багов
- **Security** - исправления уязвимостей

---

## 🏷️ Git Tagging

### Создание тега

```bash
# Annotated tag (рекомендуется)
git tag v0.1.0 -m "Release: initial version"

# Lightweight tag (не рекомендуется для релизов)
git tag v0.1.0
```

### Push тега

```bash
# Push конкретного тега
git push origin v0.1.0

# Push всех тегов (осторожно!)
git push origin --tags
```

### Удаление тега

```bash
# Локально
git tag -d v0.1.0

# На remote
git push origin --delete v0.1.0
```

---

## 🐳 Docker образы

### Формат тегов

**PROD:**
```
cr.selcloud.ru/autoorder-platform/secretmagic:0.1.0
cr.selcloud.ru/autoorder-platform/secretmagic:0.2.0
cr.selcloud.ru/autoorder-platform/secretmagic:latest  # Указывает на последний stable
```

**STAGE:**
```
cr.selcloud.ru/autoorder-platform/secretmagic:0.1.0-rc.1
cr.selcloud.ru/autoorder-platform/secretmagic:0.2.0-rc.2
```

**DEV:**
```
cr.selcloud.ru/autoorder-platform/secretmagic:dev-fix-nan-handling-a1b2c3d
cr.selcloud.ru/autoorder-platform/secretmagic:dev-develop-i7j8k9l
```

### Версионирование в CI/CD

**GitHub Actions автоматически:**
1. Извлекает версию из git tag
2. Собирает Docker образ с соответствующим тегом
3. Пушит в Selectel Container Registry
4. Деплоит в соответствующее окружение

---

## 🎯 Checklist перед релизом

### Pre-release (RC)

- [ ] Все тесты проходят (CI green: pytest, ruff, mypy)
- [ ] Код прошёл code review
- [ ] CHANGELOG обновлён
- [ ] Документация обновлена
- [ ] Миграции БД протестированы (если есть)
- [ ] Создан git tag `vX.Y.Z-rc.N`
- [ ] Образ собран и запушен в registry
- [ ] Деплой в STAGE выполнен
- [ ] Smoke tests в STAGE пройдены

### Production Release

- [ ] RC успешно протестирован в STAGE
- [ ] Нет критичных багов в STAGE
- [ ] Команда уведомлена о релизе
- [ ] Создан git tag `vX.Y.Z`
- [ ] Образ собран и запушен в registry
- [ ] Деплой в PROD выполнен
- [ ] Smoke tests в PROD пройдены
- [ ] Мониторинг проверен (метрики, логи, алерты)
- [ ] Rollback plan готов (на случай проблем)

---

## 🔧 Troubleshooting

### Ошибка при создании тега

**Проблема:** `tag already exists`

**Решение:**
```bash
# Удалить локальный тег
git tag -d v0.1.0

# Удалить remote тег
git push origin --delete v0.1.0

# Создать заново
git tag v0.1.0 -m "Release message"
git push origin v0.1.0
```

### Нужно откатить релиз

**Проблема:** Релиз в PROD содержит критичный баг

**Решение:**
```bash
# 1. Откатить деплоймент на предыдущую версию через Helm
helm rollback secretmagic-prod

# 2. Создать hotfix (см. Hotfix Workflow выше)
```

### RC провалился в STAGE

**Проблема:** `v0.2.0-rc.1` содержит баг

**Решение:**
```bash
# 1. Исправить баг в develop
# 2. Создать новый RC
git tag v0.2.0-rc.2 -m "Release candidate 2: fix critical bug"
git push origin v0.2.0-rc.2

# 3. Старый RC можно НЕ удалять (история)
```

---

## 📚 Дополнительные ресурсы

- [Semantic Versioning](https://semver.org/)
- [Keep a Changelog](https://keepachangelog.com/)
- [Conventional Commits](https://www.conventionalcommits.org/)
- [Git Tagging](https://git-scm.com/book/en/v2/Git-Basics-Tagging)
