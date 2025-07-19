import json
import os
import datetime

# Bot Files
def make_botfile(filename):
    if not os.path.exists("data"):
        os.makedirs("data")
    with open(f"data/{filename}.json", "w") as f:
        f.write("{}")
        return json.loads("{}")


def get_botfile(filename):
    if not os.path.exists(f"data/{filename}.json"):
        make_botfile(filename)
    with open(f"data/{filename}.json", "r") as f:
        return json.load(f)


def set_botfile(filename, contents):
    with open(f"data/{filename}.json", "w") as f:
        f.write(contents)


# Guild Files
def make_guildfile(serverid, filename):
    if not os.path.exists(f"data/servers/{serverid}"):
        os.makedirs(f"data/servers/{serverid}")
    with open(f"data/servers/{serverid}/{filename}.json", "w") as f:
        f.write("{}")
        return json.loads("{}")


def get_guildfile(serverid, filename):
    if not os.path.exists(f"data/servers/{serverid}/{filename}.json"):
        make_guildfile(serverid, filename)
    with open(f"data/servers/{serverid}/{filename}.json", "r") as f:
        return json.load(f)


def set_guildfile(serverid, filename, contents):
    with open(f"data/servers/{serverid}/{filename}.json", "w") as f:
        f.write(contents)


# Toss Files


def make_tossfile(serverid, filename):
    if not os.path.exists(f"data/servers/{serverid}/toss"):
        os.makedirs(f"data/servers/{serverid}/toss")
    with open(f"data/servers/{serverid}/toss/{filename}.json", "w") as f:
        f.write("{}")
        return json.loads("{}")


def get_tossfile(serverid, filename):
    if not os.path.exists(f"data/servers/{serverid}/toss/{filename}.json"):
        make_tossfile(serverid, filename)
    with open(f"data/servers/{serverid}/toss/{filename}.json", "r") as f:
        return json.load(f)


def set_tossfile(serverid, filename, contents):
    with open(f"data/servers/{serverid}/toss/{filename}.json", "w") as f:
        f.write(contents)


# Default Fills


def fill_userlog(serverid, userid):
    userlogs = get_guildfile(serverid, "userlog")
    uid = str(userid)
    if uid not in userlogs:
        userlogs[uid] = {
            "warns": [],
            "mutes": [],
            "kicks": [],
            "bans": [],
            "notes": [],
            "watch": {"state": False, "thread": None, "message": None},
        }

    return userlogs, uid

# Userlog Features


def add_userlog(sid, uid, issuer, reason, event_type):
    userlogs, uid = fill_userlog(sid, uid)

    log_data = {
        "issuer_id": issuer.id,
        "reason": reason,
        "timestamp": int(datetime.datetime.now().timestamp()),
    }
    if event_type not in userlogs[uid]:
        userlogs[uid][event_type] = []
    userlogs[uid][event_type].append(log_data)
    set_guildfile(sid, "userlog", json.dumps(userlogs))
    return len(userlogs[uid][event_type])


def toss_userlog(sid, uid, issuer, mlink, cid):
    userlogs, uid = fill_userlog(sid, uid)

    toss_data = {
        "issuer_id": issuer.id,
        "session_id": cid,
        "post_link": mlink,
        "timestamp": int(datetime.datetime.now().timestamp()),
    }
    if "tosses" not in userlogs[uid]:
        userlogs[uid]["tosses"] = []
    userlogs[uid]["tosses"].append(toss_data)
    set_guildfile(sid, "userlog", json.dumps(userlogs))
    return len(userlogs[uid]["tosses"])


# Dishtimer Features


def delete_job(timestamp, job_type, job_name):
    timestamp = str(timestamp)
    job_name = str(job_name)
    ctab = get_botfile("timers")

    del ctab[job_type][timestamp][job_name]

    # smh, not checking for empty timestamps. Smells like bloat!
    if not ctab[job_type][timestamp]:
        del ctab[job_type][timestamp]

    set_botfile("timers", json.dumps(ctab))
