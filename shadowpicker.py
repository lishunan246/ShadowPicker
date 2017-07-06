import json
import os
import re
import shutil
import subprocess

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
        SystemExit("Shadowsocks.exe not running.")

    cmd = ss_process.cmdline()[0]
    d, _ = os.path.split(cmd)
    conf_file = os.path.join(d, ss_config_name)

    with open(conf_file) as f:
        conf = json.load(f)
        server_list = [x['server'] for x in conf['configs']]
        current_index = conf['index']

    print("Start evaluating, please wait.")
    p_list = [subprocess.Popen(["ping", x, "-n", str(ping_times)], stdout=subprocess.PIPE) for x in server_list]
    tuples = []  # drop rate, response time, index, server name

    for i in range(0, len(p_list)):
        p_list[i].wait()
        out = p_list[i].stdout.read().decode(default_codec).splitlines()
        ping = re.findall(r"(\d+)(?=ms)", out[-1])
        pl = re.findall(r"(\d+)", out[-3])
        tuples.append(
            (int(pl[-1]) if pl else 100, int(ping[-1]) if ping else 500, i, server_list[i])
        )

    ts = sorted(tuples)

    for t in ts:
        print("{}: packet loss rate: {}%, ping: {}ms".format(t[-1], t[0], t[1]))

    better_index = ts[0][2]

    if better_index != current_index:
        print("Server {} may be better, you are using {}".format(server_list[better_index], server_list[current_index]))
        print("Killing process {} pid: {}".format(ss_process.name(), ss_process.pid))
        ss_process.terminate()
        shutil.move(conf_file, conf_file + ".bak")
        conf['index'] = better_index
        json.dump(conf, open(conf_file, 'w'))
        print("Restart using server {}".format(server_list[better_index]))
        start_program(cmd)
    else:
        print("your server {} seems the best".format(server_list[current_index]))

    print("Finished")


if __name__ == '__main__':
    main()
