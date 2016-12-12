#!/usr/bin/env python3
# coding: utf-8
# add to crontab

import json, time
import time, datetime
import yaml
import argparse
import os

from influxdb import InfluxDBClient

MEASUREMENT_OUT = 'holtwinters'
MEASUREMENTS= [
    {
        'measurement_in': 'elasticsearch_jvm',
        'value_in': 'mem_heap_used_percent',
        'measurement_out': MEASUREMENT_OUT,
        'value_out': 'jvm_heap_used_percent',
        'group': [
            'node_name'
        ]
    },
    {
        'measurement_in': 'mem',
        'value_in': 'used_percent',
        'measurement_out': MEASUREMENT_OUT,
        'value_out': 'mem_used_percent',
        'group': [
            'host'
        ]
    },
    {
        'measurement_in': 'disk',
        'value_in': 'used_percent',
        'measurement_out': MEASUREMENT_OUT,
        'value_out': 'disk_used_percent',
        'group': [
            'host',
            'path'
        ]
    },
    {
        'measurement_in': 'system',
        'value_in': 'load1',
        'measurement_out': MEASUREMENT_OUT,
        'value_out': 'sys_load1',
        'group':[
            'host'
        ]
    }
]

def parse_arguments():
    parser = argparse.ArgumentParser()
    parser.add_argument('-c', '--config', default='config.yml')
    parser.add_argument('-p', '--predictions', default=1, type=int)
    parser.add_argument('-t', '--time', default=86400, type=int)
    parser.add_argument('-b', '--bucket', default='1h')
    parser.add_argument('--test', action='store_true', default=False)
    return parser.parse_args()

def parseConfig(file):
    with open(file, 'r') as ymlfile:
        return yaml.load(ymlfile)

def getPeriod(interval=60):
    timeformat = '%Y-%m-%d %H:%M:%S'
    now_epoch = time.time()
    then_epoch = now_epoch - interval
    now = str(datetime.datetime.fromtimestamp(now_epoch).strftime(timeformat))
    then = str(datetime.datetime.fromtimestamp(then_epoch).strftime(timeformat))
    return then, now

def holtwintersQuery(value, predictions, measurement, start, stop, bucket, group):
    group_by = ", ".join(group)
    return """select holt_winters(mean("%s"), %s, 0) from %s
                WHERE time >= \'%s\'
                AND time <= \'%s\'
                GROUP BY time(%s), %s """ % (
                    value,
                    predictions,
                    measurement,
                    start,
                    stop,
                    bucket,
                    group_by
                )

def connect(config):
    return InfluxDBClient(
        host=config['host'],
        port=config['port'],
        database=config['database'],
        username=config['username'],
        password=config['password'],
        ssl=config['ssl'],
        verify_ssl=config['verify_ssl']
    )

def main():

    args = parse_arguments()
    cfg = parseConfig(args.config)
    period = args.time

    db_in = connect(cfg['input'])
    if 'output' in cfg:
        db_out = connect(cfg['output'])
    else:
        db_out = db_in

    then, now = getPeriod(period)

    bulk = []
    for query in MEASUREMENTS:
        q = holtwintersQuery(
            value=query['value_in'],
            predictions=args.predictions,
            measurement=query['measurement_in'],
            start=then,
            stop=now,
            bucket=args.bucket,
            group=query['group']
        )
        results = db_in.query(q)
        for res in results._get_series():
            #print res
            for prediction in res['values']:
                json = {
                    'time': prediction[0],
                    'measurement': query['measurement_out'],
                    'tags': res['tags'],
                    'fields': {
                        query['value_out']: prediction[1]
                    }
                }
                bulk.append(json)
    if args.test == False:
        try:
            db_out.write_points(bulk, time_precision='s')
            print("Sent", (str(len(bulk))), "items to influxdb")
        except Exception as e:
            print("FAIL:", e)
    else:
        print(bulk)

if __name__ == "__main__":
    main()
