FROM apache/spark:3.5.1

USER root
WORKDIR /opt/spark/work-dir

COPY services/streaming/app.py /opt/spark/work-dir/app.py
RUN chown -R spark:spark /opt/spark/work-dir

USER spark

ENTRYPOINT ["/opt/spark/bin/spark-submit", "--master", "spark://spark-master:7077", "--deploy-mode", "client", "app.py"]
