import psutil
import os
import json
import subprocess
import re

ss_program_name = "Shadowsocks.exe"
ss_config_name = "gui-config.json"


def get_process():
    for pid in psutil.pids():
        try:
            p = psutil.Process(pid)
            if p.name() == ss_program_name:
                return p
        except psutil.AccessDenied as e:
            pass

    return None


def main():
    p = get_process()
    if not p:
        SystemExit("ss not found.")

    assert len(p.cmdline()) == 1

    cmd = p.cmdline()[0]

    d, _ = os.path.split(cmd)
    conf_file = os.path.join(d, ss_config_name)
    server_list = []
    current_index = -1
    with open(conf_file) as f:
        conf = json.load(f)
        server_list = [x['server'] for x in conf['configs']]
        current_index = conf['index']
        p_list = []
        for server in server_list:
            p = subprocess.Popen(["ping", server], stdout=subprocess.PIPE)
            p_list.append(p)

        for p in p_list:
            p.wait()
            out = p.stdout.read().decode("gbk").splitlines()
            drop = out[-3]
            avg = out[-1]
            avg_ms = re.findall(r"(\d+)(?=ms)", avg)
            drop_l = re.findall(r"(\d+)", drop)
            print(avg)
            print(avg_ms)
            print(drop)
            print(drop_l)
            pass
            pass


if __name__ == '__main__':
    main()
