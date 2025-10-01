#!/usr/bin/env bash
mvn -B package
java -jar target/iems-0.0.1-SNAPSHOT.jar
