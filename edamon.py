import os
import sys
from datetime import timedelta, datetime
import subprocess
import re
from itertools import islice
import csv

from libraries.acdDict import acdDict
from libraries.acdTime import acdTime
from libraries.files import uncompress, remove_files, remove_old_files


timespan = None
if len(sys.argv) > 1:
    timespan = sys.argv[1]
else:
    print("No argument given!")
    exit()


timespan_no_delim = timespan.translate(None, " -:")

start_dt = datetime(
    year=int(timespan_no_delim[0:4]),
    month=int(timespan_no_delim[4:6]),
    day=int(timespan_no_delim[6:8]),
    hour=int(timespan_no_delim[8:10]),
    minute=int(timespan_no_delim[10:12]),
    second=int(timespan_no_delim[12:14])
)

end_dt = datetime(
    year=int(timespan_no_delim[14:18]),
    month=int(timespan_no_delim[18:20]),
    day=int(timespan_no_delim[20:22]),
    hour=int(timespan_no_delim[22:24]),
    minute=int(timespan_no_delim[24:26]),
    second=int(timespan_no_delim[26:28])
)

diff_dt = end_dt - start_dt

diff_dt_message = "The timespan is more than 2 days.\n" \
                    "Are you sure you want to continue? (y/n)"
if diff_dt.days > 2:
    if raw_input(diff_dt_message) != "y":
        exit()

dt_fmt = "%Y-%m-%d_%H.%M.%S"
job = start_dt.strftime(dt_fmt)+ "_to_" + end_dt.strftime(dt_fmt)

root_path = os.path.dirname(os.path.abspath(sys.argv[0]))
output_dir = os.path.join(root_path, "output")
temp_dir = os.path.join(root_path, "temp")
arc_dir = os.path.join(temp_dir, "archived")
unarc_dir = os.path.join(temp_dir, "unarchived")
job_file =  os.path.join(output_dir, job + ".csv")

cur_arc_dir = os.path.join(arc_dir, job)
cur_unarc_dir = os.path.join(unarc_dir, job)

if os.path.isdir(cur_arc_dir):
    remove_files(cur_arc_dir)

if not os.path.isdir(cur_unarc_dir):
    os.mkdir(cur_unarc_dir)
else:
    remove_files(cur_unarc_dir)
    os.mkdir(cur_unarc_dir)

remove_old_files(output_dir, 7)

bin_dir = os.path.abspath("/usr/local/pgngn/admin-tool-4.357/bin/")
proclog_adm = os.path.join(bin_dir, "proclog-admin-tool.sh")

subprocess.call([proclog_adm, '-et', timespan, '-p', arc_dir])

# Exclusion list
excl = [
    "FNSUB",
    "HLRSUB",
    "AUCSUB",
    "NPSUB",
    "FGNTC",
    "FGNTE",
    "FGNTI",
    "FGNTP",
    "{http://schemas.ericsson.com/pg/hlr/13.5/}PGSPI",
    "{http://schemas.ericsson.com/pg/hlr/13.5/}HESPLSP",
    "{http://schemas.ericsson.com/pg/hlr/13.5/}LOCATION"
]

r = acdDict()

reg = re.compile(r',(?=")')
for root, dirs, files in os.walk(os.path.abspath(cur_arc_dir)):
    for f in files:
        arc_f = os.path.join(root, f)
        arc_f_spl = os.path.splitext(arc_f)
        basename = os.path.basename(arc_f_spl[0])
        extension = os.path.splitext(arc_f_spl[1])[1]
        unarc_f = os.path.join(cur_unarc_dir, basename + extension)
        uncompress(arc_f, unarc_f)
        os.remove(arc_f)
        with open(unarc_f) as fh:
            while True:
                next_n_lines = list(islice(fh, 200000))
                if not next_n_lines:
                    break
                for i, s in enumerate(next_n_lines):
                    if "\"northbound\"" in s:
                        l = reg.split(next_n_lines[i])
                        trg = l[10]
                        if not ',' in trg:
                            err = l[13].replace("\"", "")
                            if err != "":
                                trg = l[10].replace("\"", "")
                                if trg not in excl:
                                    meth = l[5].replace("\"", "")
                                    status = l[6].replace("\"", "")
                                    r[trg][meth]['status'][status] += 1
                                    err = int(l[13].replace("\"", ""))
                                    if err != 0:
                                        r[trg][meth]['errors'][err] += 1
                                    usr = l[7].replace("\"", "")
                                    if usr != "":
                                        r[trg][meth]['users'][usr] += 1
                                    else:
                                        r[trg][meth]['users']["Invalid session"] += 1
                                    if not isinstance(r[trg][meth]['execTime'], list):
                                        r[trg][meth]['execTime'] = []
                                    hrs = int(l[12].replace("\"", "")[3:5])
                                    mnt = int(l[12].replace("\"", "")[6:8])
                                    sec = int(l[12].replace("\"", "")[9:11])
                                    msec = int(l[12].replace("\"", "")[12:])
                                    r[trg][meth]['execTime'].append(
                                        timedelta(
                                            hours=hrs,
                                            minutes=mnt,
                                            seconds=sec,
                                            microseconds=msec
                                        )
                                    )
        os.remove(unarc_f)
os.rmdir(cur_arc_dir)
os.rmdir(cur_unarc_dir)

header = ["Target", "Type", "OK", "NOK", "Average Time",
          "Maximum Time", "Error Codes", "Users"]
with open(job_file, 'wb') as f:
    writer = csv.writer(f)
    writer.writerow(header)
    for ok, ov in r.iteritems():
        for ik, iv in ov.iteritems():
            t = acdTime(r[ok][ik]['execTime'])
            writer.writerow([
                ok,
                ik,
                r[ok][ik]['status']['SUCCESSFUL'] if r[ok][ik]['status']['SUCCESSFUL'] else 0,
                r[ok][ik]['status']['FAILED'] if r[ok][ik]['status']['FAILED'] else 0,
                t.average(),
                t.maximum(),
                '; '.join(['{0} - {1}'.format(k,v) for k,v in r[ok][ik]['errors'].iteritems()]),
                '; '.join(['{0} - {1}'.format(k,v) for k,v in r[ok][ik]['users'].iteritems()])
            ])
