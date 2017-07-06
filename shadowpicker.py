import json
import os
import re
import subprocess
import sys
import shutil

import psutil

ss_program_name = "Shadowsocks.exe"
ss_config_name = "gui-config.json"
default_codec = "gbk"
ping_times = 10


def get_process():
    for pid in psutil.pids():
        try:
            p = psutil.Process(pid)
            if p.name() == ss_program_name:
                return p
        except psutil.AccessDenied as e:
            pass

    return None


def start_program(cmd):
    CREATE_NEW_PROCESS_GROUP = 0x00000200
    DETACHED_PROCESS = 0x00000008

    subprocess.Popen(
        [cmd],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        creationflags=DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP
    )


def main():
    ss_process = get_process()
    if not ss_process:
        SystemExit("ss not found.")

    assert len(ss_process.cmdline()) == 1

    cmd = ss_process.cmdline()[0]

    d, _ = os.path.split(cmd)
    conf_file = os.path.join(d, ss_config_name)

    with open(conf_file) as f:
        conf = json.load(f)
        server_list = [x['server'] for x in conf['configs']]
        current_index = conf['index']

    p_list = []
    for server in server_list:
        p = subprocess.Popen(["ping", server, "-n", str(ping_times)], stdout=subprocess.PIPE)
        p_list.append(p)

    tuples = []  # drop rate, response time, index, server name
    i = 0
    for p in p_list:
        p.wait()
        out = p.stdout.read().decode(default_codec).splitlines()
        avg_ms = re.findall(r"(\d+)(?=ms)", out[-1])
        drop_l = re.findall(r"(\d+)", out[-3])

        tuples.append(
            (int(drop_l[-1]) if drop_l else 100, int(avg_ms[-1]) if avg_ms else sys.maxint, i, server_list[i])
        )
        i += 1

    ts = sorted(tuples)
    better_index = ts[0][2]
    if better_index != current_index:
        print("server {} may be better, you are using {}".format(server_list[better_index], server_list[current_index]))
        print("killing process {} pid: {}".format(ss_process.name(), ss_process.pid))

        ss_process.terminate()
        shutil.move(conf_file, conf_file + ".bak")
        conf['index'] = better_index
        json.dump(conf, open(conf_file, 'w'))
        print("restart using server {}".format(server_list[better_index]))
        start_program(cmd)
        print("finished")
    else:
        print("your server {} seems the best".format(server_list[current_index]))


if __name__ == '__main__':
    main()
