FROM apache/airflow:3.2.2
USER root
RUN python -m venv /opt/retail-venv && chown -R airflow:0 /opt/retail-venv
USER airflow
COPY requirements.txt /tmp/retail-requirements.txt
RUN PIP_USER=false /opt/retail-venv/bin/pip install --no-cache-dir -r /tmp/retail-requirements.txt && /opt/retail-venv/bin/pip check
