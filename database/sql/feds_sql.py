import ast
import threading

from sqlalchemy import BigInteger, Boolean, Column, Integer, String, UnicodeText
from telegram.error import BadRequest, Forbidden

from Database.sql import BASE, SESSION
from Mikobot import dispatcher


class Federations(BASE):
    __tablename__ = "feds"
    owner_id = Column(String(14))
    fed_name = Column(UnicodeText)
    fed_id = Column(UnicodeText, primary_key=True)
    fed_rules = Column(UnicodeText)
    fed_log = Column(UnicodeText)
    fed_users = Column(UnicodeText)

    def __init__(self, owner_id, fed_name, fed_id, fed_rules, fed_log, fed_users):
        self.owner_id = owner_id
        self.fed_name = fed_name
        self.fed_id = fed_id
        self.fed_rules = fed_rules
        self.fed_log = fed_log
        self.fed_users = fed_users


class ChatF(BASE):
    __tablename__ = "chat_feds"
    chat_id = Column(String(14), primary_key=True)
    chat_name = Column(UnicodeText)
    fed_id = Column(UnicodeText)

    def __init__(self, chat_id, chat_name, fed_id):
        self.chat_id = chat_id
        self.chat_name = chat_name
        self.fed_id = fed_id


class BansF(BASE):
    __tablename__ = "bans_feds"
    fed_id = Column(UnicodeText, primary_key=True)
    user_id = Column(String(14), primary_key=True)
    first_name = Column(UnicodeText, nullable=False)
    last_name = Column(UnicodeText)
    user_name = Column(UnicodeText)
    reason = Column(UnicodeText, default="")
    time = Column(Integer, default=0)

    def __init__(self, fed_id, user_id, first_name, last_name, user_name, reason, time):
        self.fed_id = fed_id
        self.user_id = user_id
        self.first_name = first_name
        self.last_name = last_name
        self.user_name = user_name
        self.reason = reason
        self.time = time


class FedsUserSettings(BASE):
    __tablename__ = "feds_settings"
    user_id = Column(BigInteger, primary_key=True)
    should_report = Column(Boolean, default=True)

    def __init__(self, user_id):
        self.user_id = user_id

    def __repr__(self):
        return "<Feds report settings ({})>".format(self.user_id)


class FedSubs(BASE):
    __tablename__ = "feds_subs"
    fed_id = Column(UnicodeText, primary_key=True)
    fed_subs = Column(UnicodeText, primary_key=True, nullable=False)

    def __init__(self, fed_id, fed_subs):
        self.fed_id = fed_id
        self.fed_subs = fed_subs

    def __repr__(self):
        return "<Fed {} subscribes for {}>".format(self.fed_id, self.fed_subs)


# Dropping db
# Federations.__table__.drop()
# ChatF.__table__.drop()
# BansF.__table__.drop()
# FedSubs.__table__.drop()

Federations.__table__.create(checkfirst=True)
ChatF.__table__.create(checkfirst=True)
BansF.__table__.create(checkfirst=True)
FedsUserSettings.__table__.create(checkfirst=True)
FedSubs.__table__.create(checkfirst=True)

FEDS_LOCK = threading.RLock()
CHAT_FEDS_LOCK = threading.RLock()
FEDS_SETTINGS_LOCK = threading.RLock()
FEDS_SUBSCRIBER_LOCK = threading.RLock()

FEDERATION_BYNAME = {}
FEDERATION_BYOWNER = {}
FEDERATION_BYFEDID = {}

FEDERATION_CHATS = {}
FEDERATION_CHATS_BYID = {}

FEDERATION_BANNED_FULL = {}
FEDERATION_BANNED_USERID = {}

FEDERATION_NOTIFICATION = {}
FEDS_SUBSCRIBER = {}
MYFEDS_SUBSCRIBER = {}


def get_fed_info(fed_id):
    get = FEDERATION_BYFEDID.get(str(fed_id))
    if get is None:
        return False
    return get


def get_fed_id(chat_id):
    get = FEDERATION_CHATS.get(str(chat_id))
    if get is None:
        return False
    else:
        return get["fid"]


def get_fed_name(chat_id):
    get = FEDERATION_CHATS.get(str(chat_id))
    if get is None:
        return False
    else:
        return get["chat_name"]


def get_user_fban(fed_id, user_id):
    if not FEDERATION_BANNED_FULL.get(fed_id):
        return False, False, False
    user_info = FEDERATION_BANNED_FULL[fed_id].get(user_id)
    if not user_info:
        return None, None, None
    return user_info["first_name"], user_info["reason"], user_info["time"]


def get_user_admin_fed_name(user_id):
    user_feds = []
    for f in FEDERATION_BYFEDID:
        if int(user_id) in ast.literal_eval(
            ast.literal_eval(FEDERATION_BYFEDID[f]["fusers"])["members"]
        ):
            user_feds.append(FEDERATION_BYFEDID[f]["fname"])
    return user_feds


def get_user_owner_fed_name(user_id):
    user_feds = []
    for f in FEDERATION_BYFEDID:
        if int(user_id) == int(
            ast.literal_eval(FEDERATION_BYFEDID[f]["fusers"])["owner"]
        ):
            user_feds.append(FEDERATION_BYFEDID[f]["fname"])
    return user_feds


def get_user_admin_fed_full(user_id):
    user_feds = []
    for f in FEDERATION_BYFEDID:
        if int(user_id) in ast.literal_eval(
            ast.literal_eval(FEDERATION_BYFEDID[f]["fusers"])["members"]
        ):
            user_feds.append({"fed_id": f, "fed": FEDERATION_BYFEDID[f]})
    return user_feds


def get_user_owner_fed_full(user_id):
    user_feds = []
    for f in FEDERATION_BYFEDID:
        if int(user_id) == int(
            ast.literal_eval(FEDERATION_BYFEDID[f]["fusers"])["owner"]
        ):
            user_feds.append({"fed_id": f, "fed": FEDERATION_BYFEDID[f]})
    return user_feds


def get_user_fbanlist(user_id):
    banlist = FEDERATION_BANNED_FULL
    user_name = ""
    fedname = []
    for x in banlist:
        if banlist[x].get(user_id):
            if user_name == "":
                user_name = banlist[x][user_id].get("first_name")
            fedname.append([x, banlist[x][user_id].get("reason")])
    return user_name, fedname


def new_fed(owner_id, fed_name, fed_id):
    with FEDS_LOCK:
        global FEDERATION_BYOWNER, FEDERATION_BYFEDID, FEDERATION_BYNAME
        fed = Federations(
            str(owner_id),
            fed_name,
            str(fed_id),
            "Rules is not set in this federation.",
            None,
            str({"owner": str(owner_id), "members": "[]"}),
        )
        SESSION.add(fed)
        SESSION.commit()
        FEDERATION_BYOWNER[str(owner_id)] = {
            "fid": str(fed_id),
            "fname": fed_name,
            "frules": "Rules is not set in this federation.",
            "flog": None,
            "fusers": str({"owner": str(owner_id), "members": "[]"}),
        }
        FEDERATION_BYFEDID[str(fed_id)] = {
            "owner": str(owner_id),
            "fname": fed_name,
            "frules": "Rules is not set in this federation.",
            "flog": None,
            "fusers": str({"owner": str(owner_id), "members": "[]"}),
        }
        FEDERATION_BYNAME[fed_name] = {
            "fid": str(fed_id),
            "owner": str(owner_id),
            "frules": "Rules is not set in this federation.",
            "flog": None,
            "fusers": str({"owner": str(owner_id), "members": "[]"}),
        }
        return fed


def del_fed(fed_id):
    with FEDS_LOCK:
        global FEDERATION_BYOWNER, FEDERATION_BYFEDID, FEDERATION_BYNAME, FEDERATION_CHATS, FEDERATION_CHATS_BYID, FEDERATION_BANNED_USERID, FEDERATION_BANNED_FULL
        getcache = FEDERATION_BYFEDID.get(fed_id)
        if getcache is None:
            return False
        # Variables
        getfed = FEDERATION_BYFEDID.get(fed_id)
        owner_id = getfed["owner"]
        fed_name = getfed["fname"]
        # Delete from cache
        FEDERATION_BYOWNER.pop(owner_id)
        FEDERATION_BYFEDID.pop(fed_id)
        FEDERATION_BYNAME.pop(fed_name)
        if FEDERATION_CHATS_BYID.get(fed_id):
            for x in FEDERATION_CHATS_BYID[fed_id]:
                delchats = SESSION.query(ChatF).get(str(x))
                if delchats:
                    SESSION.delete(delchats)
                    SESSION.commit()
                FEDERATION_CHATS.pop(x)
            FEDERATION_CHATS_BYID.pop(fed_id)
        # Delete fedban users
        getall = FEDERATION_BANNED_USERID.get(fed_id)
        if getall:
            for x in getall:
                banlist = SESSION.query(BansF).get((fed_id, str(x)))
                if banlist:
                    SESSION.delete(banlist)
                    SESSION.commit()
        if FEDERATION_BANNED_USERID.get(fed_id):
            FEDERATION_BANNED_USERID.pop(fed_id)
        if FEDERATION_BANNED_FULL.get(fed_id):
            FEDERATION_BANNED_FULL.pop(fed_id)
        # Delete fedsubs
        getall = MYFEDS_SUBSCRIBER.get(fed_id)
        if getall:
            for x in getall:
                getsubs = SESSION.query(FedSubs).get((fed_id, str(x)))
                if getsubs:
                    SESSION.delete(getsubs)
                    SESSION.commit()
        if FEDS_SUBSCRIBER.get(fed_id):
            FEDS_SUBSCRIBER.pop(fed_id)
        if MYFEDS_SUBSCRIBER.get(fed_id):
            MYFEDS_SUBSCRIBER.pop(fed_id)
        # Delete from database
        curr = SESSION.query(Federations).get(fed_id)
        if curr:
            SESSION.delete(curr)
            SESSION.commit()
        return True


def rename_fed(fed_id, owner_id, newname):
    with FEDS_LOCK:
        global FEDERATION_BYFEDID, FEDERATION_BYOWNER, FEDERATION_BYNAME
        fed = SESSION.query(Federations).get(fed_id)
        if not fed:
            return False
        fed.fed_name = newname
        SESSION.commit()

        # Update the dicts
        oldname = FEDERATION_BYFEDID[str(fed_id)]["fname"]
        tempdata = FEDERATION_BYNAME[oldname]
        FEDERATION_BYNAME.pop(oldname)

        FEDERATION_BYOWNER[str(owner_id)]["fname"] = newname
        FEDERATION_BYFEDID[str(fed_id)]["fname"] = newname
        FEDERATION_BYNAME[newname] = tempdata
        return True


def chat_join_fed(fed_id, chat_name, chat_id):
    with FEDS_LOCK:
        global FEDERATION_CHATS, FEDERATION_CHATS_BYID
        r = ChatF(chat_id, chat_name, fed_id)
        SESSION.add(r)
        FEDERATION_CHATS[str(chat_id)] = {"chat_name": chat_name, "fid": fed_id}
        checkid = FEDERATION_CHATS_BYID.get(fed_id)
        if checkid is None:
            FEDERATION_CHATS_BYID[fed_id] = []
        FEDERATION_CHATS_BYID[fed_id].append(str(chat_id))
        SESSION.commit()
        return r


def search_fed_by_name(fed_name):
    allfed = FEDERATION_BYNAME.get(fed_name)
    if allfed is None:
        return False
    return allfed


def search_user_in_fed(fed_id, user_id):
    getfed = FEDERATION_BYFEDID.get(fed_id)
    if getfed is None:
        return False
    getfed = ast.literal_eval(getfed["fusers"])["members"]
    if user_id in ast.literal_eval(getfed):
        return True
    else:
        return False


def user_demote_fed(fed_id, user_id):
    with FEDS_LOCK:
        global FEDERATION_BYOWNER, FEDERATION_BYFEDID, FEDERATION_BYNAME
        # Variables
        getfed = FEDERATION_BYFEDID.get(str(fed_id))
        owner_id = getfed["owner"]
        fed_name = getfed["fname"]
        fed_rules = getfed["frules"]
        fed_log = getfed["flog"]
        # Temp set
        try:
            members = ast.literal_eval(ast.literal_eval(getfed["fusers"])["members"])
        except ValueError:
            return False
        members.remove(user_id)
        # Set user
        FEDERATION_BYOWNER[str(owner_id)]["fusers"] = str(
            {"owner": str(owner_id), "members": str(members)},
        )
        FEDERATION_BYFEDID[str(fed_id)]["fusers"] = str(
            {"owner": str(owner_id), "members": str(members)},
        )
        FEDERATION_BYNAME[fed_name]["fusers"] = str(
            {"owner": str(owner_id), "members": str(members)},
        )
        # Set on database
        fed = Federations(
            str(owner_id),
            fed_name,
            str(fed_id),
            fed_rules,
            fed_log,
            str({"owner": str(owner_id), "members": str(members)}),
        )
        SESSION.merge(fed)
        SESSION.commit()
        return True

        curr = SESSION.query(UserF).all()
        result = False
        for r in curr:
            if int(r.user_id) == int(user_id):
                if r.fed_id == fed_id:
                    SESSION.delete(r)
                    SESSION.commit()
                    result = True

        SESSION.close()
        return result


def user_join_fed(fed_id, user_id):
    with FEDS_LOCK:
        global FEDERATION_BYOWNER, FEDERATION_BYFEDID, FEDERATION_BYNAME
        # Variables
        getfed = FEDERATION_BYFEDID.get(str(fed_id))
        owner_id = getfed["owner"]
        fed_name = getfed["fname"]
        fed_rules = getfed["frules"]
        fed_log = getfed["flog"]
        # Temp set
        members = ast.literal_eval(ast.literal_eval(getfed["fusers"])["members"])
        members.append(user_id)
        # Set user
        FEDERATION_BYOWNER[str(owner_id)]["fusers"] = str(
            {"owner": str(owner_id), "members": str(members)},
        )
        FEDERATION_BYFEDID[str(fed_id)]["fusers"] = str(
            {"owner": str(owner_id), "members": str(members)},
        )
        FEDERATION_BYNAME[fed_name]["fusers"] = str(
            {"owner": str(owner_id), "members": str(members)},
        )
        # Set on database
        fed = Federations(
            str(owner_id),
            fed_name,
            str(fed_id),
            fed_rules,
            fed_log,
            str({"owner": str(owner_id), "members": str(members)}),
        )
        SESSION.merge(fed)
        SESSION.commit()
        __load_all_feds_chats()
        return True


def chat_leave_fed(chat_id):
    with FEDS_LOCK:
        global FEDERATION_CHATS, FEDERATION_CHATS_BYID
        # Set variables
        fed_info = FEDERATION_CHATS.get(str(chat_id))
        if fed_info is None:
            return False
        fed_id = fed_info["fid"]
        # Delete from cache
        FEDERATION_CHATS.pop(str(chat_id))
        FEDERATION_CHATS_BYID[str(fed_id)].remove(str(chat_id))
        # Delete from db
        curr = SESSION.query(ChatF).all()
        for U in curr:
            if int(U.chat_id) == int(chat_id):
                SESSION.delete(U)
                SESSION.commit()
        return True


def all_fed_chats(fed_id):
    with FEDS_LOCK:
        getfed = FEDERATION_CHATS_BYID.get(fed_id)
        if getfed is None:
            return []
        else:
            return getfed


def all_fed_users(fed_id):
    with FEDS_LOCK:
        getfed = FEDERATION_BYFEDID.get(str(fed_id))
        if getfed is None:
            return False
        fed_owner = ast.literal_eval(ast.literal_eval(getfed["fusers"])["owner"])
        fed_admins = ast.literal_eval(ast.literal_eval(getfed["fusers"])["members"])
        fed_admins.append(fed_owner)
        return fed_admins


def all_fed_members(fed_id):
    with FEDS_LOCK:
        getfed = FEDERATION_BYFEDID.get(str(fed_id))
        fed_admins = ast.literal_eval(ast.literal_eval(getfed["fusers"])["members"])
        return fed_admins


def set_frules(fed_id, rules):
    with FEDS_LOCK:
        global FEDERATION_BYOWNER, FEDERATION_BYFEDID, FEDERATION_BYNAME
        # Variables
        getfed = FEDERATION_BYFEDID.get(str(fed_id))
        owner_id = getfed["owner"]
        fed_name = getfed["fname"]
        fed_members = getfed["fusers"]
        fed_rules = str(rules)
        fed_log = getfed["flog"]
        # Set user
        FEDERATION_BYOWNER[str(owner_id)]["frules"] = fed_rules
        FEDERATION_BYFEDID[str(fed_id)]["frules"] = fed_rules
        FEDERATION_BYNAME[fed_name]["frules"] = fed_rules
        # Set on database
        fed = Federations(
            str(owner_id),
            fed_name,
            str(fed_id),
            fed_rules,
            fed_log,
            str(fed_members),
        )
        SESSION.merge(fed)
        SESSION.commit()
        return True


def get_frules(fed_id):
    with FEDS_LOCK:
        rules = FEDERATION_BYFEDID[str(fed_id)]["frules"]
        return rules


def fban_user(fed_id, user_id, first_name, last_name, user_name, reason, time):
    with FEDS_LOCK:
        r = SESSION.query(BansF).all()
        for I in r:
            if I.fed_id == fed_id:
                if int(I.user_id) == int(user_id):
                    SESSION.delete(I)

        r = BansF(
            str(fed_id),
            str(user_id),
            first_name,
            last_name,
            user_name,
            reason,
            time,
        )

        SESSION.add(r)
        try:
            SESSION.commit()
        except:
            SESSION.rollback()
            return False
        finally:
            SESSION.commit()
        __load_all_feds_banned()
        return r


def multi_fban_user(
    multi_fed_id,
    multi_user_id,
    multi_first_name,
    multi_last_name,
    multi_user_name,
    multi_reason,
):
    if True:  # with FEDS_LOCK:
        counter = 0
        time = 0
        for x in range(len(multi_fed_id)):
            fed_id = multi_fed_id[x]
            user_id = multi_user_id[x]
            first_name = multi_first_name[x]
            last_name = multi_last_name[x]
            user_name = multi_user_name[x]
            reason = multi_reason[x]
            r = SESSION.query(BansF).all()
            for I in r:
                if I.fed_id == fed_id:
                    if int(I.user_id) == int(user_id):
                        SESSION.delete(I)

            r = BansF(
                str(fed_id),
                str(user_id),
                first_name,
                last_name,
                user_name,
                reason,
                time,
            )

            SESSION.add(r)
            counter += 1
        try:
            SESSION.commit()
        except:
            SESSION.rollback()
            return False
        finally:
            SESSION.commit()
        __load_all_feds_banned()
        return counter


def un_fban_user(fed_id, user_id):
    with FEDS_LOCK:
        r = SESSION.query(BansF).all()
        for I in r:
            if I.fed_id == fed_id:
                if int(I.user_id) == int(user_id):
                    SESSION.delete(I)
        try:
            SESSION.commit()
        except:
            SESSION.rollback()
            return False
        finally:
            SESSION.commit()
        __load_all_feds_banned()
        return I


def get_fban_user(fed_id, user_id):
    list_fbanned = FEDERATION_BANNED_USERID.get(fed_id)
    if list_fbanned is None:
        FEDERATION_BANNED_USERID[fed_id] = []
    if user_id in FEDERATION_BANNED_USERID[fed_id]:
        r = SESSION.query(BansF).all()
        reason = None
        for I in r:
            if I.fed_id == fed_id:
                if int(I.user_id) == int(user_id):
                    reason = I.reason
                    time = I.time
        return True, reason, time
    else:
        return False, None, None


def get_all_fban_users(fed_id):
    list_fbanned = FEDERATION_BANNED_USERID.get(fed_id)
    if list_fbanned is None:
        FEDERATION_BANNED_USERID[fed_id] = []
    return FEDERATION_BANNED_USERID[fed_id]


def get_all_fban_users_target(fed_id, user_id):
    list_fbanned = FEDERATION_BANNED_FULL.get(fed_id)
    if list_fbanned is None:
        FEDERATION_BANNED_FULL[fed_id] = []
        return False
    getuser = list_fbanned[str(user_id)]
    return getuser


def get_all_fban_users_global():
    list_fbanned = FEDERATION_BANNED_USERID
    total = []
    for x in list(FEDERATION_BANNED_USERID):
        for y in FEDERATION_BANNED_USERID[x]:
            total.append(y)
    return total


def get_all_feds_users_global():
    list_fed = FEDERATION_BYFEDID
    total = []
    for x in list(FEDERATION_BYFEDID):
        total.append(FEDERATION_BYFEDID[x])
    return total


def search_fed_by_id(fed_id):
    get = FEDERATION_BYFEDID.get(fed_id)
    if get is None:
        return False
    else:
        return get
    result = False
    for Q in curr:
        if Q.fed_id == fed_id:
            result = Q.fed_id

    return result


def user_feds_report(user_id: int) -> bool:
    user_setting = FEDERATION_NOTIFICATION.get(str(user_id))
    if user_setting is None:
        user_setting = True
    return user_setting


def set_feds_sett
