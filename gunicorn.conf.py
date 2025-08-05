# gunicorn.conf.py

# Aumenta o timeout para 600 segundos (10 minutos)
timeout = 600

# Tempo máximo para um worker responder antes de ser reiniciado
graceful_timeout = 600

# Número de workers (mantenha 1-2 para ambientes gratuitos)
workers = 1

# Tipo de worker (sync é o padrão)
worker_class = "sync"

# Nome do módulo da aplicação
bind = "0.0.0.0:10000"

# Log de atividades
loglevel = "info"
accesslog = "-"
errorlog = "-"