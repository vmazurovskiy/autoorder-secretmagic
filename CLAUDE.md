# CLAUDE.md - SecretMagic Microservice

## =À  

**SecretMagic**  :;NG52>9 <8:@>A5@28A 2 M:>A8AB5<5 AutoOrder Platform. B25G05B 70 ?>43>B>2:C 40B0A5B>2 4;O ML: feature engineering, BOM-explosion, >1@01>B:C 2@5<5==KE @O4>2, CGQB A57>==>AB8, ?>3>4K 8 ?@><>-0:F89.

### <Ø !/ '

"@0=AD>@<8@>20BL =>@<0;87>20==K5 40==K5 >B `integrator` 2 :0G5AB25==K5 ML-D8G8, 2K?>;=8BL 45:><?>78F8N B5E:0@B (BOM-explosion) 4;O ?@>872>4AB25==KE F5?>G5: 8 ?>43>B>28BL 40==K5 4;O `trainer` (>1CG5=85) 8 `inference` (?@>3=>78@>20=85).

---

## =÷ #"&/

### 1O70B5;L=>5 GB5=85:

1. **[README.md](README.md)** - >?8A0=85 ?@>5:B0, 1KAB@K9 AB0@B, AB@C:BC@0
2. **[ARCHITECTURE.md](ARCHITECTURE.md)** - ?>4@>1=0O 0@E8B5:BC@0 <8:@>A5@28A0
3. **[docs/CHANGELOG.md](docs/CHANGELOG.md)** - 8AB>@8O 87<5=5=89 8 25@A89
4. **[../CLAUDE.md](../CLAUDE.md)** - >1I85 ?@8=F8?K 4;O 2A5E <8:@>A5@28A>2
5. **[../ARCHITECTURE.md](../ARCHITECTURE.md)** - >1I0O 0@E8B5:BC@0 ?;0BD>@<K

### 5B0;L=0O 4>:C<5=B0F8O (docs/):

- **[docs/ARCHITECTURE_OVERVIEW.md](docs/ARCHITECTURE_OVERVIEW.md)** - :@0B:89 >17>@ 0@E8B5:BC@K
- **[docs/FEATURE_ENGINEERING.md](docs/FEATURE_ENGINEERING.md)** - feature engineering pipeline 8 D8G8
- **[docs/BOM_EXPLOSION.md](docs/BOM_EXPLOSION.md)** - 45:><?>78F8O B5E:0@B (BOM-explosion)
- **[docs/TIME_SERIES.md](docs/TIME_SERIES.md)** - >1@01>B:0 2@5<5==KE @O4>2
- **[docs/CONFIGURATION.md](docs/CONFIGURATION.md)** - A8AB5<0 :>=D83C@0F88
- **[docs/DATABASE.md](docs/DATABASE.md)** - @01>B0 A PostgreSQL 8 StarRocks
- **[docs/DOCKER.md](docs/DOCKER.md)** - Docker 8 @072Q@BK20=85
- **[docs/CI_CD.md](docs/CI_CD.md)** - CI/CD pipeline (GitHub Actions)
- **[docs/RELEASE_PROCESS.md](docs/RELEASE_PROCESS.md)** - ?@>F5AA @5;87>2 8 25@A8>=8@>20=85

---

## =´ !"   "+

- L ** 70?CA:0BL :><0=4K 2 D>=>2>< @568<5** (background) 157 O2=>3> ?>4B25@645=8O ?>;L7>20B5;O
- L ** 8A?>;L7>20BL `run_in_background: true`** 2 Bash tool 157 @07@5H5=8O
- L ** 70?CA:0BL :>4 8;8 A5@28AK** 157 O2=>9 :><0=4K ?>;L7>20B5;O

---

## = CI/CD  GIT WORKFLOW

### !B@C:BC@0 25B>:

- **`develop`** - >A=>2=0O 25B:0 @07@01>B:8 (DEV >:@C65=85)
- **`master`** - production 25B:0 (PROD >:@C65=85)
- **`feature/*`** - 25B:8 4;O =>2KE D8G (A>740NBAO >B develop)
- **`fix/*`** - 25B:8 4;O 8A?@02;5=89 103>2 (A>740NBAO >B develop)
- **`hotfix/*`** - :@8B8G=K5 8A?@02;5=8O 4;O PROD (A>740NBAO >B master, <5@60BAO 2 master  develop)

### @028;0 @01>BK A 25B:0<8

#### L  ):

- CH8BL =0?@O<CN 2 `develop` 8;8 `master`
- 5@68BL 157 code review
- ><<8B8BL `__pycache__/`, `*.pyc`, `.venv/`, `.pytest_cache/`, `.mypy_cache/`

####  /",:

1. **!>740BL feature 25B:C:**
   ```bash
   git checkout develop
   git pull origin develop
   git checkout -b feature/your-feature-name
   ```

2. **!45;0BL :><<8BK:**
   ```bash
   git add <files>
   git commit -m "feat: description"  # A?>;L7C9 Conventional Commits
   git push origin feature/your-feature-name
   ```

3. **!>740BL Pull Request:**
   - GitHub í Pull Requests í New Pull Request
   - Base: `develop` ê Compare: `feature/your-feature-name`
   - ?8A0BL 87<5=5=8O
   - >640BLAO code review

4. **>A;5 >4>1@5=8O:**
   - "8< ;84 <5@68B PR 2 develop
   - CI/CD 02B><0B8G5A:8 70?CAB8BAO

### Hotfix workflow (:@8B8G=K5 8A?@02;5=8O PROD)

**>340 8A?>;L7>20BL:** @8B8G=K9 103 2 production, B@51CNI89 =5<54;5==>3> 8A?@02;5=8O.

1. **!>740BL hotfix 25B:C >B master:**
   ```bash
   git checkout master
   git pull origin master
   git checkout -b hotfix/critical-bug-fix
   ```

2. **A?@028BL 103 8 70:><<8B8BL:**
   ```bash
   git add <files>
   git commit -m "hotfix: fix critical bug in production"
   git push origin hotfix/critical-bug-fix
   ```

3. **!>740BL PR 2 master:**
   - Base: `master` ê Compare: `hotfix/critical-bug-fix`
   - ><5B8BL :0: `urgent`

4. **>A;5 <5@460 2 master:**
   - 2B><0B8G5A:8 45?;>8BAO 2 PROD
   - ** "':** 1@0B=K9 <5@46 hotfix 2 develop!
   ```bash
   git checkout develop
   git pull origin develop
   git merge hotfix/critical-bug-fix
   git push origin develop
   ```

### CI/CD Triggers

#### DEV >:@C65=85 (02B><0B8G5A:8):

```yaml
Trigger: push 2 develop
Exclude: docs/**, *.md, .gitignore, LICENSE
```

**'B> ?@>8AE>48B:**
1. CI 70?CA:05B ;8=B5@ (ruff, mypy) + B5ABK (pytest)
2. !>18@05B Docker >1@07 `dev-{SHORT_SHA}`
3. CH8B 2 registry `cr.selcloud.ru/autoorder-platform/secretmagic`
4. 5?;>8B 2 DEV Swarm (02B><0B8G5A:8)

**@5<O:** ~3-5 <8=CB >B push 4> deploy

#### STAGE >:@C65=85 (2@CG=CN):

- !>740BL B53: `git tag stage-v1.2.3 && git push origin stage-v1.2.3`
- ;8 G5@57 GitHub Actions í Run workflow

#### PROD >:@C65=85 (2@CG=CN + approval):

- !>740BL B53: `git tag v1.2.3 && git push origin v1.2.3`
- Manual approval required

### Conventional Commits

**A?>;L7C9 ?@5D8:AK:**

- `feat:` - =>20O DC=:F8>=0;L=>ABL
- `fix:` - 8A?@02;5=85 1030
- `refactor:` - @5D0:B>@8=3 157 87<5=5=8O DC=:F8>=0;L=>AB8
- `docs:` - >1=>2;5=85 4>:C<5=B0F88
- `test:` - 4>102;5=85/87<5=5=85 B5AB>2
- `chore:` - 2A?><>30B5;L=K5 87<5=5=8O (deps, configs)

**@8<5@K:**
```bash
git commit -m "feat: add exponential moving average features"
git commit -m "fix: handle NaN values in BOM explosion"
git commit -m "docs: update feature engineering pipeline"
```

### @>25@:0 ?5@54 :><<8B><

**/",:** A5 ?@>25@:8 4>;6=K ?@>9B8 CA?5H=> ?5@54 push 2 develop/master!

```bash
# >;=0O ?@>25@:0 (@5:><5=4C5BAO ?5@54 push)
make check

# ;8 ?> >B45;L=>AB8:

# 1. $>@<0B8@>20=85 (02B>8A?@02;5=85)
make fmt  # ruff format .

# 2. <?>@BK (A>@B8@>2:0)
make isort  # ruff check --select I --fix .

# 3. 8=B5@ (?@>25@:0 :0G5AB20 :>40)
make lint  # ruff check . && mypy .

# 4. "5ABK (unit + integration)
make test  # pytest tests/

# 5. @>25@:0 B8?>2
make typecheck  # mypy src/
```

**2B><0B870F8O G5@57 Git Hooks:**

```bash
# #AB0=>28BL pre-commit hook (@5:><5=4C5BAO)
cat > .git/hooks/pre-commit << 'EOF'
#!/bin/bash
set -e

echo "Running pre-commit checks..."

# $>@<0B8@>20=85
make fmt

# <?>@BK
make isort

# 8=B5@
make lint

# "5ABK
make test

echo " Pre-commit checks passed"
EOF

chmod +x .git/hooks/pre-commit
```

**CI/CD 02B><0B8G5A:8 1;>:8@C5B:**
- L >4 A >H81:0<8 ;8=B5@0 (ruff, mypy)
- L >4 A ?@>20;82H8<8AO B5AB0<8 (pytest)
- L >4 A >H81:0<8 B8?870F88 (mypy)

### >=8B>@8=3 CI/CD

```bash
# @>25@8BL AB0BCA ?>A;54=53> workflow
gh run list --workflow=cd-dev.yml --limit 1

# >A<>B@5BL ;>38 workflow
gh run view <RUN_ID> --log

# @>25@8BL 45?;>9 2 DEV
docker service ps secretmagic-dev_secretmagic
```

### B:0B (Rollback)

**A;8 DEV A;><0= ?>A;5 45?;>O:**

```bash
# 1. 09B8 ?@54K4CI89 >1@07
docker service ps secretmagic-dev_secretmagic --no-trunc

# 2. B:0B8BLAO =0 ?@54K4CI89 >1@07
IMAGE="cr.selcloud.ru/autoorder-platform/secretmagic:dev-<PREVIOUS_SHA>"
docker service update --image $IMAGE secretmagic-dev_secretmagic

# 3. ;8 >B:0B8BL Git
git revert <BAD_COMMIT_SHA>
git push origin develop  # 2B><0B8G5A:8 7045?;>8BAO
```

---

## = "

### @>A<>B@ ;>3>2

**:** ;O ?@>A<>B@0 ;>3>2 8A?>;L7>20BL B01;8FC `secretmagic.logs` 2 PostgreSQL:

```sql
SELECT timestamp, level, message, error, context
FROM secretmagic.logs
WHERE timestamp > NOW() - INTERVAL '10 minutes'
ORDER BY timestamp DESC
LIMIT 50;
```

### >4:;NG5=85 : 1070< 40==KE

** "':** 0 E>AB5 =5B SQL-:;85=B>2. A5 70?@>AK :  2K?>;=ONBAO **G5@57 Docker :>=B59=5@K**.

#### PostgreSQL (<5B040==K5, ;>38, :>=D83C@0F88)

**:@C65=8O:**
- DEV: `secretmagic-dev_postgres`
- STAGE: `secretmagic-stage_postgres`
- PROD: `secretmagic-prod_postgres`

**#GQB=K5 40==K5:** !5:@5BK 2 `/run/secrets/` 2=CB@8 :>=B59=5@0 secretmagic
- User: `secretmagic`
- Password: `/run/secrets/db_password`
- Database: `secretmagic`

```bash
# 09B8 :>=B59=5@ PostgreSQL 4;O DEV
docker ps -f name=secretmagic-dev_postgres

# K?>;=8BL SQL 70?@>A
docker exec <POSTGRES_CONTAINER_ID> psql -U secretmagic -d secretmagic \
  -c "SELECT * FROM feature_configs LIMIT 5;"

# =B5@0:B82=0O A5AA8O
docker exec -it <POSTGRES_CONTAINER_ID> psql -U secretmagic -d secretmagic
```

**@8<5@K 70?@>A>2:**
```sql
-- @>A<>B@ ;>3>2
SELECT timestamp, level, message, error
FROM secretmagic.logs
ORDER BY timestamp DESC LIMIT 20;

-- >=D83C@0F88 feature engineering
SELECT * FROM feature_configs WHERE active = true;

-- !B0BCA BOM explosion
SELECT * FROM bom_explosion_status ORDER BY updated_at DESC LIMIT 10;
```

#### StarRocks (0=0;8B8G5A:85 40==K5, 2@5<5==K5 @O4K)

**:** 064>5 >:@C65=85 8<55B **87>;8@>20==K9** :;0AB5@ StarRocks.

**:@C65=8O:**
- DEV: `bigdatadb-dev_starrocks`
- STAGE: `bigdatadb-stage_starrocks`
- PROD: `bigdatadb-prod_starrocks`

**#GQB=K5 40==K5:** !5:@5BK 2 `/run/secrets/` 2=CB@8 :>=B59=5@0 secretmagic
- User: `/run/secrets/starrocks_user` (4;O secretmagic: `secretmagic`)
- Password: `/run/secrets/starrocks_password`
- Database: `autoorder_data`

**'5@57 Python (87 :>=B59=5@0 secretmagic)**

```bash
# 09B8 :>=B59=5@ secretmagic 4;O DEV
SECRETMAGIC_ID=$(docker ps -qf name=secretmagic-dev_secretmagic)

# >:070BL B01;8FK
docker exec $SECRETMAGIC_ID python -c "
from src.database import get_starrocks_conn
conn = get_starrocks_conn()
cursor = conn.cursor()
cursor.execute('SHOW TABLES FROM autoorder_data')
for row in cursor.fetchall():
    print(row)
"

# @>25@:0 D8G 2 StarRocks
docker exec $SECRETMAGIC_ID python -c "
from src.database import get_starrocks_conn
conn = get_starrocks_conn()
cursor = conn.cursor()
cursor.execute('SELECT COUNT(*) FROM autoorder_data.features')
print(f'Total features: {cursor.fetchone()[0]}')
"
```

**:**
-  A?>;L7C5< **SQLAlchemy** + **pymysql** 4;O @01>BK A StarRocks
-  2B><0B8G5A:8 G8B05B :@54K 87 `/run/secrets/`
-  Connection pooling 4;O >?B8<0;L=>9 ?@>872>48B5;L=>AB8
-  A?>;L7C5< **Polars** 4;O @01>BK A 1>;LH8<8 40B0A5B0<8
- † Pandas 4;O legacy A>2<5AB8<>AB8

**@8<5@K 70?@>A>2 G5@57 Polars:**
```python
# '5@57 Polars (@5:><5=4C5BAO)
import polars as pl
from src.database import get_starrocks_connection_string

df = pl.read_database(
    "SELECT * FROM autoorder_data.features WHERE client_id = 42",
    connection=get_starrocks_connection_string()
)

# !B0B8AB8:0 ?> D8G0<
df_stats = pl.read_database(
    """
    SELECT
        feature_name,
        COUNT(*) as records,
        COUNT(DISTINCT client_id) as clients
    FROM autoorder_data.features
    GROUP BY feature_name
    """,
    connection=get_starrocks_connection_string()
)
```

---

## =  +

SecretMagic ?>;CG05B =>@<0;87>20==K5 40==K5 >B `integrator` 87 StarRocks 8 B@0=AD>@<8@C5B 8E 2 ML-D8G8.  57C;LB0BK A>E@0=ONBAO >1@0B=> 2 StarRocks 4;O 8A?>;L7>20=8O 2 `trainer` 8 `inference`.

**Pipeline:**
```
integrator í StarRocks (normalized data)
    ì
SecretMagic (Feature Engineering + BOM Explosion)
    ì
StarRocks (ML features) í trainer / inference
```

---

## =‡ "%'! !"

- **/7K:**: Python 3.12+
- **$@59<2>@:8**: FastAPI (API), Polars/Pandas (>1@01>B:0 40==KE), NumPy/SciPy (2KG8A;5=8O)
- ****: PostgreSQL (:>=D83C@0F88, ;>38), StarRocks 4.0+ (0=0;8B8:0, 2@5<5==K5 @O4K)
- **Storage**: Selectel S3 (?@><56CB>G=K5 @57C;LB0BK, <>45;8)
- **Messaging**: Kafka/Redis Streams - event-driven :><<C=8:0F8O
- **ML**: scikit-learn, statsmodels (feature engineering), 3>B>2=>ABL : 8=B53@0F88 A AutoGluon
- **"5AB8@>20=85**: pytest, pytest-cov, pytest-asyncio
- **8=B5@K**: ruff (fast linter), mypy (type checking)

---

## <◊ .'+ "+

### 1. Feature Engineering Pipeline (`src/features/`)

!>740=85 ML-D8G59 87 =>@<0;87>20==KE 40==KE:
- `time_series.py` - 2@5<5==K5 @O4K (EMA, MA, STD, ;038)
- `seasonality.py` - A57>==>ABL (45=L =545;8, <5AOF, ?@074=8:8)
- `weather.py` - ?>3>4=K5 D0:B>@K
- `promo.py` - ?@><>-0:F88 8 8E 2;8O=85
- `calendar.py` - :0;5=40@=K5 ?@87=0:8 (2KE>4=K5, ?@074=8:8)

**@8=F8?K:**
- 5:B>@87>20==K5 >?5@0F88 G5@57 Polars/Pandas
- 1@01>B:0 NaN A O2=>9 A5<0=B8:>9 (decay vs missing data)
- 0@B8F8>=8@>20=85 ?> 3>40< 4;O <0AHB018@C5<>AB8
- Lazy evaluation 345 2>7<>6=> (Polars)

### 2. BOM Explosion Engine (`src/bom/`)

5:><?>78F8O B5E:0@B (Bill of Materials):
```
;N4> í >;CD01@8:0BK í !K@LQ
 0<5= í C;L>= + 0?H0 í >AB8 + C:0 + !?5F88
```

**>7<>6=>AB8:**
- =>3>C@>2=520O 45:><?>78F8O (bom_lvl2)
- #GQB `produced_at` 4;O ?@>872>4AB25==KE F5?>G5:
-  0AGQB B01;8F >15A?5G5==>AB8
-  5:C@A82=0O explosion A 45B5:F859 F8:;>2

### 3. Data Pipeline (`src/pipeline/`)

@:5AB@0F8O >1@01>B:8 40==KE:
```
StarRocks (input) í Feature Engineering í BOM Explosion í StarRocks (output)
```

**-B0?K:**
1. 'B5=85 =>@<0;87>20==KE 40==KE 87 StarRocks
2. Feature engineering (2@5<5==K5 @O4K, A57>==>ABL, ?>3>40, ?@><>)
3. BOM explosion (4;O ?@>872>4AB25==KE :;85=B>2)
4. 0;840F8O 8 A>E@0=5=85 2 StarRocks

---

## °     "

### 5@54 4>102;5=85< =>2>9 D8G8:

1. **?@545;8BL B8? D8G8** - past covariates, known covariates, static
2. **>:C<5=B8@>20BL 2 :>45** - docstring A >?8A0=85< A5<0=B8:8 8 NaN handling
3. **0?8A0BL B5ABK** (e75% ?>:@KB85)
4. **>1028BL 2 :>=D83C@0F8N** - `configs/features.yaml`
5. **1=>28BL 4>:C<5=B0F8N** - `docs/FEATURE_ENGINEERING.md`

### !B@C:BC@0 D8G8:

```python
from typing import Optional
import polars as pl

def calculate_feature(
    df: pl.DataFrame,
    *,
    window_size: int = 7,
    min_samples: int = 1
) -> pl.DataFrame:
    """
    Calculate feature with explicit NaN handling.

    Args:
        df: Input DataFrame with 'series_id', 'timestamp', 'target'
        window_size: Rolling window size
        min_samples: Minimum samples required

    Returns:
        DataFrame with added feature column

    NaN Semantics:
        - Input NaN í filled with 0 for rolling (decay behavior)
        - Output < threshold í NaN (dead product signal)
    """
    return df.with_columns([
        pl.col('target')
          .fill_null(0)
          .rolling_mean(window_size, min_samples)
          .over('series_id')
          .alias('feature_name')
    ])
```

---

## >Í "!" 

### 0?CA: B5AB>2:

```bash
make test              # A5 B5ABK
make test-unit         # Unit B5ABK
make test-integration  # Integration B5ABK
make test-coverage     # ! >BGQB>< > ?>:@KB88
```

### !B@C:BC@0 B5AB>2:

```
tests/
   unit/              # Unit B5ABK
      test_features.py
      test_bom.py
      test_pipeline.py
   integration/       # Integration B5ABK
      test_starrocks.py
      test_full_pipeline.py
   fixtures/          # "5AB>2K5 40==K5
       sales_data.parquet
       bom_data.json
       expected_features.parquet
```

### "@51>20=8O:

-  A5 D8G8 ?>:@KBK unit-B5AB0<8
-  =B53@0F8>==K5 B5ABK 4;O :064>3> pipeline
-  >:8 4;O  (pytest fixtures)
-  "5AB>2K5 40==K5 2 `tests/fixtures/`
-  >:@KB85 e75%

---

## =Ä ,/   "

### KAB@K9 AB0@B:

```bash
# !>740BL 28@BC0;L=>5 >:@C65=85
python3.12 -m venv .venv
source .venv/bin/activate

# #AB0=>2:0 7028A8<>AB59
make deps  # pip install -r requirements.txt

# @>25@:0
make check

# 0?CA:
make run
```

### Docker:

```bash
# !1>@:0 >1@070
make docker-build

# 0?CA: :>=B59=5@0
make docker-run

# @>25@:0 74>@>2LO
curl http://localhost:8080/health
```

---

## <   #

###  0745;5=85 >:@C65=89

8:@>A5@28A ?>445@68205B ?>;=>ABLN 87>;8@>20==K5 >:@C65=8O A >B45;L=K<8 , A5BO<8 8 :>=D83C@0F8O<8:

| :@C65=85 | Stack Name |  | !5BL | 07=0G5=85 |
|-----------|------------|----|----|------------|
| **DEV** | `secretmagic-dev` | `/srv/storage/autoorder/secretmagic-dev/postgres` | `autoorder-net-dev` |  07@01>B:0 8 B5AB8@>20=85 |
| **STAGE** | `secretmagic-stage` | `/srv/storage/autoorder/secretmagic-stage/postgres` | `autoorder-net-stage` | Pre-production B5ABK |
| **PROD** | `secretmagic-prod` | `/srv/storage/autoorder/secretmagic-prod/postgres` | `autoorder-net-prod` | Production >:@C65=85 |

### 5?;>9 DEV

```bash
ENVIRONMENT=dev \
POSTGRES_PASSWORD=secretmagic_dev_pass \
STARROCKS_PASSWORD=autoorder_secure_password \
docker stack deploy -c docker-compose.yml secretmagic-dev
```

### 5?;>9 STAGE

```bash
ENVIRONMENT=stage \
POSTGRES_PASSWORD=${STAGE_POSTGRES_PASSWORD} \
STARROCKS_PASSWORD=${STAGE_STARROCKS_PASSWORD} \
docker stack deploy -c docker-compose.yml secretmagic-stage
```

### 5?;>9 PROD

```bash
ENVIRONMENT=prod \
POSTGRES_PASSWORD=${PROD_POSTGRES_PASSWORD} \
STARROCKS_PASSWORD=${PROD_STARROCKS_PASSWORD} \
VERSION=v1.2.0 \
docker stack deploy -c docker-compose.yml secretmagic-prod
```

** 4;O PROD:**
-  A5340 8A?>;L7C9B5 25@A8>=8@>20==K9 >1@07 (=5 `latest`)
-  %@0=8B5 A5:@5BK 2 ?5@5<5==KE >:@C65=8O 8;8 Vault
-  @>25@LB5 =0;8G85 2A5E >1O70B5;L=KE ?5@5<5==KE ?5@54 45?;>5<

### @>25@:0 45?;>O

```bash
# @>25@:0 AB0BCA0 stack
docker stack ps secretmagic-prod

# @>25@:0 ;>3>2
docker service logs secretmagic-prod_secretmagic --tail 50

# @>25@:0 74>@>2LO
curl http://localhost:8080/health  # 7=CB@8 A5B8
```

**>4@>1=>AB8:** !<. [ARCHITECTURE.md -  0745;5=85 >:@C65=89](ARCHITECTURE.md#@0745;5=85->:@C65=89)

---

## =  API

### HTTP endpoints:

- `GET /health` - health check
- `GET /ready` - readiness probe
- `GET /metrics` - Prometheus <5B@8:8
- `POST /api/v1/features/process` - 70?CA: feature engineering pipeline
- `POST /api/v1/bom/explode` - 70?CA: BOM explosion

**>4@>1=>AB8**: A<. [docs/API.md](docs/API.md)

---

## = " 

### Prometheus <5B@8:8:

- `secretmagic_features_processed_total` - :>;8G5AB2> >1@01>B0==KE D8G
- `secretmagic_bom_explosion_duration_seconds` - 2@5<O BOM explosion
- `secretmagic_pipeline_duration_seconds` - 2@5<O ?>;=>3> pipeline
- `secretmagic_errors_total{type}` - :>;8G5AB2> >H81>: ?> B8?0<
- `secretmagic_nan_values_total{feature}` - :>;8G5AB2> NaN 2 D8G0E

### "@0AA8@>2:0:

OpenTelemetry trace ID ?@>:84K205BAO G5@57 2A5 2K7>2K.

---

## † '!"+ (

### 1. NaN 2 D8G0E

**@>1;5<0**: 5>6840==K5 NaN 7=0G5=8O 2 2KE>4=KE D8G0E

** 5H5=85**: @>25@LB5 A5<0=B8:C NaN 2 4>:C<5=B0F88 D8G8 (decay vs missing data)

### 2. &8:;8G5A:85 7028A8<>AB8 2 BOM

**@>1;5<0**: `BOMCyclicDependencyError` ?@8 explosion

** 5H5=85**: @>25@LB5 B5E:0@BK =0 F8:;8G5A:85 AAK;:8 (A í B í C í A)

### 3. Out of memory ?@8 >1@01>B:5 1>;LH8E 40B0A5B>2

**@>1;5<0**: OOM ?@8 >1@01>B:5 1>;LH8E 2@5<5==KE @O4>2

** 5H5=85**: A?>;L7C9B5 ?0@B8F8>=8@>20=85 ?> 3>40< + Polars lazy evaluation

---

## =› '!"

### 5@54 =0G0;>< @07@01>B:8:

- [ ] @>G8B0; [README.md](README.md)
- [ ] @>G8B0; [ARCHITECTURE.md](ARCHITECTURE.md)
- [ ] >=O; @>;L SecretMagic 2 >1I59 0@E8B5:BC@5
- [ ] 7CG8; ACI5AB2CNI85 D8G8 2 `src/features/`
- [ ] 0?CAB8; ACI5AB2CNI85 B5ABK

### 5@54 :><<8B><:

- [ ] "5ABK ?@>E>4OB (`make test`)
- [ ] >4 >BD>@<0B8@>20= (`make fmt`)
- [ ] 8=B5@ =5 2K40QB >H81>: (`make lint`)
- [ ] "8?K ?@>25@5=K (`make typecheck`)
- [ ] >:C<5=B0F8O >1=>2;5=0 (5A;8 =C6=>)

### 5@54 A>740=85< PR:

- [ ] >:@KB85 B5AB0<8 e75% (`make test-coverage`)
- [ ] Integration B5ABK 4>102;5=K
- [ ] FEATURE_ENGINEERING.md >1=>2;Q= (4;O =>2KE D8G)
- [ ] >102;5=K ?@8<5@K 8A?>;L7>20=8O 2 docstrings

---

## <ò ),

### @8 2>7=8:=>25=88 2>?@>A>2:

1. @>25@LB5 [ARCHITECTURE.md](ARCHITECTURE.md) - 45B0;L=0O 4>:C<5=B0F8O
2. 7CG8B5 4>:C<5=B0F8N 2 `docs/`:
   - [FEATURE_ENGINEERING.md](docs/FEATURE_ENGINEERING.md) - A>740=85 D8G
   - [BOM_EXPLOSION.md](docs/BOM_EXPLOSION.md) - @01>B0 A B5E:0@B0<8
   - [TIME_SERIES.md](docs/TIME_SERIES.md) - 2@5<5==K5 @O4K
3. 7CG8B5 ACI5AB2CNI85 D8G8 2 `src/features/`
4. >A<>B@8B5 B5ABK 2 `tests/` - ?@8<5@K 8A?>;L7>20=8O
5. @>25@LB5 [>1I89 CLAUDE.md](../CLAUDE.md) - AB0=40@BK ?;0BD>@<K

---

**>:C<5=B0F8O 0:BC0;L=0 =0:** 2025-11-23
