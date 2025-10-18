#!/usr/bin/env bash
set -euo pipefail

ROLE=${HADOOP_ROLE:-namenode}
NAMENODE_DATA_DIR=${NAMENODE_DATA_DIR:-/hadoop/dfs/name}
DATANODE_DATA_DIR=${DATANODE_DATA_DIR:-/hadoop/dfs/data}
HISTORYSERVER_DATA_DIR=${HISTORYSERVER_DATA_DIR:-/hadoop/yarn/timeline}

case "$ROLE" in
  namenode)
    mkdir -p "${NAMENODE_DATA_DIR}"
    if [ ! -d "${NAMENODE_DATA_DIR}/current" ]; then
      echo "Formatting HDFS NameNode at ${NAMENODE_DATA_DIR}"
      hdfs namenode -format -force -nonInteractive
    fi
    exec hdfs namenode
    ;;
  datanode)
    mkdir -p "${DATANODE_DATA_DIR}"
    exec hdfs datanode
    ;;
  resourcemanager)
    exec yarn resourcemanager
    ;;
  nodemanager)
    exec yarn nodemanager
    ;;
  historyserver)
    mkdir -p "${HISTORYSERVER_DATA_DIR}"
    exec mapred historyserver
    ;;
  *)
    echo "Unknown HADOOP_ROLE: ${ROLE}" >&2
    exit 1
    ;;
esac
