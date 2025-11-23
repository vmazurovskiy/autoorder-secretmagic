# Stage 1: Builder
FROM python:3.12-slim AS builder

# #AB0=02;8205< =5>1E>48<K5 ?0:5BK 4;O A1>@:8
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    git \
    && rm -rf /var/lib/apt/lists/*

#  01>G0O 48@5:B>@8O
WORKDIR /build

# >?8@C5< requirements 4;O :5H8@>20=8O 7028A8<>AB59
COPY requirements.txt ./
RUN pip install --no-cache-dir --user -r requirements.txt

# Stage 2: Runtime
FROM python:3.12-slim

# #AB0=02;8205< runtime 7028A8<>AB8 8 CB8;8BK
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    tzdata \
    && rm -rf /var/lib/apt/lists/*

# !>740Q< ?>;L7>20B5;O 4;O 70?CA:0 ?@8;>65=8O (=5 root)
RUN groupadd -g 1000 secretmagic && \
    useradd -m -u 1000 -g secretmagic secretmagic

#  01>G0O 48@5:B>@8O
WORKDIR /app

# >?8@C5< CAB0=>2;5==K5 ?0:5BK 87 builder stage
COPY --from=builder /root/.local /home/secretmagic/.local

# >102;O5< .local/bin 2 PATH
ENV PATH=/home/secretmagic/.local/bin:$PATH

# >?8@C5< 8AE>4=K9 :>4 ?@8;>65=8O
COPY --chown=secretmagic:secretmagic src/ /app/src/
COPY --chown=secretmagic:secretmagic __init__.py /app/

# !>740Q< 48@5:B>@88 4;O :>=D83C@0F88 8 ;>3>2
RUN mkdir -p /app/configs /app/logs /app/tests/fixtures && \
    chown -R secretmagic:secretmagic /app

# >?8@C5< :>=D83C@0F8>==K5 D09;K 4;O @07=KE >:@C65=89
COPY --chown=secretmagic:secretmagic configs/ /app/configs/

# >?8@C5< fixtures 4;O B5AB>2
COPY --chown=secretmagic:secretmagic tests/fixtures /app/tests/fixtures

# 5@5:;NG05<AO =0 =5?@828;538@>20==>3> ?>;L7>20B5;O
USER secretmagic

# >@BK
EXPOSE 8080 9000

# Healthcheck
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD pgrep -f python || exit 1

# 0?CA: ?@8;>65=8O
CMD ["python", "-m", "src.main"]
