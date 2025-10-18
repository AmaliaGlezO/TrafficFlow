FROM apache/hadoop:3.3.6

USER root

COPY infra/hadoop/config/ /opt/hadoop/etc/hadoop/
COPY infra/hadoop/scripts/start-component.sh /opt/start-component.sh

RUN mkdir -p /hadoop/dfs/name /hadoop/dfs/data /hadoop/yarn/timeline \
    && chown -R hadoop:hadoop /hadoop /opt/hadoop/etc/hadoop /opt/start-component.sh \
    && chmod +x /opt/start-component.sh

USER hadoop

ENV HADOOP_ROLE=namenode \
    NAMENODE_DATA_DIR=/hadoop/dfs/name \
    DATANODE_DATA_DIR=/hadoop/dfs/data \
    HISTORYSERVER_DATA_DIR=/hadoop/yarn/timeline

ENTRYPOINT ["/usr/local/bin/dumb-init", "--", "/opt/start-component.sh"]
