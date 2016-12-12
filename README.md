# influx-holtwinters
Tool for executing holt-winters query against metrics in InfluxDB. Output can be written back into InfluxDB or printed to standard output.

## Usage

Run test query against past weeks data. Refer to `config.yml.example` for correct configuration syntax.

```
time ./main.py -c ./config.yml --test -t 604800
```
