bind = '0.0.0.0:5000'   # Equivalent to `-b 0.0.0.0:5000`
accesslog = '-'         # Equivalent to `--access-logfile -`

# Log format
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" in %(D)sµs'
